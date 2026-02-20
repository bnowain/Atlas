"""Async httpx client pool for spoke communication."""

from __future__ import annotations

import httpx
from typing import AsyncIterator

from app.config import SPOKES, SPOKE_REQUEST_TIMEOUT


# One httpx.AsyncClient per spoke, managed by lifespan
_clients: dict[str, httpx.AsyncClient] = {}


def init_clients():
    """Create an AsyncClient for each spoke. Called during FastAPI lifespan startup."""
    for key, spoke in SPOKES.items():
        _clients[key] = httpx.AsyncClient(
            base_url=spoke.base_url,
            timeout=httpx.Timeout(SPOKE_REQUEST_TIMEOUT, connect=5.0),
            follow_redirects=True,
        )


async def close_clients():
    """Close all clients. Called during FastAPI lifespan shutdown."""
    for client in _clients.values():
        await client.aclose()
    _clients.clear()


def _get_client(spoke_key: str) -> httpx.AsyncClient:
    if spoke_key not in _clients:
        raise ValueError(f"Unknown spoke: {spoke_key}")
    return _clients[spoke_key]


async def get(spoke_key: str, path: str, **kwargs) -> httpx.Response:
    client = _get_client(spoke_key)
    return await client.get(path, **kwargs)


async def post(spoke_key: str, path: str, **kwargs) -> httpx.Response:
    client = _get_client(spoke_key)
    return await client.post(path, **kwargs)


async def patch(spoke_key: str, path: str, **kwargs) -> httpx.Response:
    client = _get_client(spoke_key)
    return await client.patch(path, **kwargs)


async def put(spoke_key: str, path: str, **kwargs) -> httpx.Response:
    client = _get_client(spoke_key)
    return await client.put(path, **kwargs)


async def delete(spoke_key: str, path: str, **kwargs) -> httpx.Response:
    client = _get_client(spoke_key)
    return await client.delete(path, **kwargs)


async def stream_file(spoke_key: str, path: str, headers: dict | None = None) -> AsyncIterator[bytes]:
    """Stream a file response from a spoke, yielding chunks."""
    client = _get_client(spoke_key)
    async with client.stream("GET", path, headers=headers or {}) as resp:
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes(chunk_size=65536):
            yield chunk


async def request(spoke_key: str, method: str, path: str, **kwargs) -> httpx.Response:
    """Generic request — used by the spoke proxy."""
    client = _get_client(spoke_key)
    return await client.request(method, path, **kwargs)
