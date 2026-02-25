"""Service lifecycle management API — start, stop, restart spoke services."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ServiceSetting
from app.services import service_manager

router = APIRouter(prefix="/api/services", tags=["services"])


async def _get_auto_start_map(db: AsyncSession) -> dict[str, bool]:
    """Load auto-start settings from DB."""
    result = await db.execute(select(ServiceSetting))
    rows = result.scalars().all()
    return {r.service_key: r.auto_start for r in rows}


@router.get("")
async def list_services(db: AsyncSession = Depends(get_db)):
    """List all services with current status."""
    auto_start_map = await _get_auto_start_map(db)
    statuses = await service_manager.get_all_status(auto_start_map)
    return {"services": [
        {
            "key": s.key,
            "name": s.name,
            "port": s.port,
            "state": s.state,
            "error": s.error,
            "started_at": s.started_at,
            "restart_count": s.restart_count,
            "auto_start": s.auto_start,
            "process_group": s.process_group,
            "depends_on": s.depends_on or [],
            "is_docker": s.is_docker,
        }
        for s in statuses
    ]}


@router.post("/{key}/start")
async def start_service(key: str):
    """Start a service."""
    return await service_manager.start_service(key)


@router.post("/{key}/stop")
async def stop_service(key: str):
    """Stop a service."""
    return await service_manager.stop_service(key)


@router.post("/{key}/restart")
async def restart_service(key: str):
    """Restart a service."""
    return await service_manager.restart_service(key)


@router.get("/{key}/logs")
async def get_service_logs(key: str, lines: int = 100):
    """Get recent log output for a service."""
    logs = service_manager.get_logs(key, lines)
    return {"key": key, "logs": logs}


@router.get("/auto-start")
async def get_auto_start_settings(db: AsyncSession = Depends(get_db)):
    """Get all auto-start settings."""
    return await _get_auto_start_map(db)


@router.patch("/{key}/auto-start")
async def update_auto_start(key: str, enabled: bool = True, db: AsyncSession = Depends(get_db)):
    """Toggle auto-start for a service."""
    result = await db.execute(
        select(ServiceSetting).where(ServiceSetting.service_key == key)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.auto_start = enabled
    else:
        setting = ServiceSetting(service_key=key, auto_start=enabled)
        db.add(setting)

    await db.commit()
    return {"key": key, "auto_start": enabled}


@router.post("/start-all")
async def start_all_services():
    """Start all services in dependency order."""
    results = await service_manager.start_all_services()
    return {"results": results}


@router.post("/stop-all")
async def stop_all_services():
    """Gracefully stop all running services."""
    results = await service_manager.stop_all_services()
    return {"results": results}
