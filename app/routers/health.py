"""Health check endpoint — Atlas status + all spoke statuses."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import HealthResponse
from app.services import spoke_registry

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Return Atlas health + live status of all spokes with latency."""
    spokes = await spoke_registry.check_all()
    return HealthResponse(status="ok", spokes=spokes)
