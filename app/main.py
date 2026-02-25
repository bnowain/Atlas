"""Atlas — Civic Accountability Orchestration Hub."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db, validate_schema_columns
from app.services import spoke_client, spoke_registry, ollama_manager, service_manager
from app.middleware.error_handling import spoke_error_handler, spoke_timeout_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)-28s  %(levelname)-5s  %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await validate_schema_columns()
    spoke_client.init_clients()
    spoke_registry.start_polling()
    logger.info("Atlas started — checking spokes...")
    statuses = await spoke_registry.check_all()
    for s in statuses:
        icon = "+" if s.online else "-"
        lat = f" ({s.latency_ms}ms)" if s.latency_ms else ""
        logger.info("  [%s] %s %s%s", icon, s.name, s.base_url, lat)

    # Detect already-loaded Ollama models and start health polling
    await ollama_manager.detect_running_models()
    ollama_manager.start_health_polling()
    running = ollama_manager.get_running_profiles()
    if running:
        logger.info("Ollama models already loaded: %s", ", ".join(running))
    else:
        logger.info("No Ollama models detected — start them from the Settings page")

    # Detect running spoke services and start health polling
    await service_manager.detect_running_services()
    service_manager.start_health_polling()

    # Auto-start services from DB settings
    from sqlalchemy import select as sa_select
    from app.database import AsyncSessionLocal
    from app.models import ServiceSetting
    async with AsyncSessionLocal() as session:
        result = await session.execute(sa_select(ServiceSetting).where(ServiceSetting.auto_start == True))
        auto_keys = [r.service_key for r in result.scalars().all()]
    if auto_keys:
        logger.info("Auto-start services: %s", auto_keys)
        asyncio.create_task(service_manager.startup_auto_start_services(auto_keys))

    yield
    # Shutdown — stop services that Atlas spawned (prevents orphan processes).
    # Services detected as already-running on startup are left alone.
    service_manager.stop_health_polling()
    await service_manager.stop_spawned_services()
    ollama_manager.stop_health_polling()
    spoke_registry.stop_polling()
    await spoke_client.close_clients()


app = FastAPI(
    title="Atlas",
    description="Civic Accountability Orchestration Hub",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server, local origins, and Tailscale origins
from app.services.tailscale import detect_tailscale, get_tailscale_origins

ts_ip, ts_host = detect_tailscale()
if ts_ip:
    logger.info("Tailscale detected: %s (%s)", ts_ip, ts_host or "no DNS")

cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8888",
    "http://127.0.0.1:8888",
]
cors_origins.extend(get_tailscale_origins([8888, 5173]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers for spoke errors
app.add_exception_handler(httpx.ConnectError, spoke_error_handler)
app.add_exception_handler(httpx.TimeoutException, spoke_timeout_handler)

# --- Routers ---
from app.routers import health, spokes, chat, settings, people, search, pipeline, models, instructions, rag, services, summaries, system_prompt  # noqa: E402

app.include_router(health.router)
app.include_router(spokes.router)
app.include_router(chat.router)
app.include_router(settings.router)
app.include_router(people.router)
app.include_router(search.router)
app.include_router(pipeline.router)
app.include_router(models.router)
app.include_router(instructions.router)
app.include_router(rag.router)
app.include_router(services.router)
app.include_router(summaries.router)
app.include_router(system_prompt.router)

# --- Static file serving (production) ---
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback — serve index.html for any non-API route."""
        # Never intercept API routes — let them 404 naturally
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(404, "Not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
