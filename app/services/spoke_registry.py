"""Spoke health monitoring — background polling + on-demand checks."""

from __future__ import annotations

import asyncio
import time
import logging

import httpx

from app.config import SPOKES, HEALTH_POLL_INTERVAL, SpokeConfig
from app.schemas import SpokeStatus
from app.services import spoke_client

logger = logging.getLogger(__name__)

# Cached status per spoke
_status_cache: dict[str, SpokeStatus] = {}
_poll_task: asyncio.Task | None = None


async def check_health(spoke_key: str) -> SpokeStatus:
    """Ping a single spoke's health endpoint and return status."""
    spoke = SPOKES.get(spoke_key)
    if not spoke:
        return SpokeStatus(key=spoke_key, name=spoke_key, base_url="", online=False, error="Unknown spoke")

    t0 = time.monotonic()
    try:
        resp = await spoke_client.get(spoke_key, spoke.health_path, timeout=5.0)
        latency = round((time.monotonic() - t0) * 1000, 1)
        online = resp.status_code < 500
        return SpokeStatus(
            key=spoke_key,
            name=spoke.name,
            base_url=spoke.base_url,
            online=online,
            latency_ms=latency,
        )
    except (httpx.ConnectError, httpx.TimeoutException, httpx.ConnectTimeout, OSError) as exc:
        return SpokeStatus(
            key=spoke_key,
            name=spoke.name,
            base_url=spoke.base_url,
            online=False,
            error=str(exc),
        )


async def check_all() -> list[SpokeStatus]:
    """Check all spokes in parallel, update cache."""
    results = await asyncio.gather(*(check_health(key) for key in SPOKES))
    for status in results:
        _status_cache[status.key] = status
    return list(results)


def get_cached_status() -> list[SpokeStatus]:
    """Return last known status without making network calls."""
    return list(_status_cache.values())


async def _poll_loop():
    """Background loop that checks all spokes every HEALTH_POLL_INTERVAL seconds."""
    while True:
        try:
            await check_all()
        except Exception:
            logger.exception("Error during spoke health poll")
        await asyncio.sleep(HEALTH_POLL_INTERVAL)


def start_polling():
    """Start the background health polling task."""
    global _poll_task
    if _poll_task is None or _poll_task.done():
        _poll_task = asyncio.create_task(_poll_loop())


def stop_polling():
    """Cancel the background polling task."""
    global _poll_task
    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
        _poll_task = None
