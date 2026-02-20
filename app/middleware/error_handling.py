"""Global exception handlers for spoke communication errors."""

from __future__ import annotations

import logging

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def spoke_error_handler(request: Request, exc: httpx.ConnectError):
    logger.warning("Spoke connection refused: %s", exc)
    return JSONResponse(
        status_code=502,
        content={"detail": "Spoke service is not reachable", "error": str(exc)},
    )


async def spoke_timeout_handler(request: Request, exc: httpx.TimeoutException):
    logger.warning("Spoke request timed out: %s", exc)
    return JSONResponse(
        status_code=504,
        content={"detail": "Spoke service timed out", "error": str(exc)},
    )
