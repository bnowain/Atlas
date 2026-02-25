"""Health check endpoint — Atlas status + all spoke statuses."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import HealthResponse, TailscaleInfo
from app.services import spoke_registry
from app.services.tailscale import detect_tailscale

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Return Atlas health + live status of all spokes with latency."""
    spokes = await spoke_registry.check_all()

    ts_ip, ts_host = detect_tailscale()
    tailscale = None
    if ts_ip:
        tailscale = TailscaleInfo(
            ip=ts_ip,
            hostname=ts_host,
            url=f"http://{ts_ip}:8888",
        )

    return HealthResponse(status="ok", spokes=spokes, tailscale=tailscale)
