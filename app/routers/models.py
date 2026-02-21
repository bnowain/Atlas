"""Model management endpoints — start/stop Ollama backends, VRAM monitoring."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.config import OLLAMA_MODELS
from app.services import ollama_manager

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
async def list_models():
    """Get all model definitions with their current status."""
    statuses = await ollama_manager.get_all_status()
    return {"models": [asdict(s) for s in statuses]}


@router.get("/gpu")
async def get_gpu():
    """Get GPU info including actual VRAM usage."""
    info = await ollama_manager.get_gpu_info()
    return asdict(info)


@router.post("/{key}/start")
async def start_model(key: str):
    """Load an Ollama model into VRAM."""
    if key not in OLLAMA_MODELS:
        raise HTTPException(404, f"Unknown model key: {key}")
    return await ollama_manager.start_model(key)


@router.post("/{key}/stop")
async def stop_model(key: str):
    """Unload an Ollama model from VRAM."""
    if key not in OLLAMA_MODELS:
        raise HTTPException(404, f"Unknown model key: {key}")
    return await ollama_manager.stop_model(key)


@router.get("/{key}/logs")
async def get_model_logs(key: str, lines: int = 50):
    """Get runtime info for an Ollama model."""
    if key not in OLLAMA_MODELS:
        raise HTTPException(404, f"Unknown model key: {key}")
    logs = await ollama_manager.get_logs(key, lines)
    return {"key": key, "logs": logs}
