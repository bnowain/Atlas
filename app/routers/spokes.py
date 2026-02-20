"""Transparent spoke proxy — forwards requests to spoke APIs."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from app.config import SPOKES
from app.services import spoke_client

router = APIRouter(prefix="/api/spokes", tags=["spokes"])

# Headers we should NOT forward from the spoke back to the browser
_DROP_HEADERS = {
    "connection", "keep-alive", "transfer-encoding",
    "te", "trailer", "upgrade",
    # Never leak spoke redirect locations to the browser
    "location",
}

# Headers to forward from the original request to the spoke
_FORWARD_HEADERS = {"range", "accept", "content-type", "accept-encoding"}


@router.api_route("/{spoke_key}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_to_spoke(spoke_key: str, path: str, request: Request):
    """
    Proxy any request to a spoke.

    GET /api/spokes/civic_media/api/meetings
      -> GET http://localhost:8000/api/meetings
    """
    if spoke_key not in SPOKES:
        return Response(content=f"Unknown spoke: {spoke_key}", status_code=404)

    # Build forwarded path (ensure trailing slash matches spoke expectations)
    target_path = f"/{path}"
    if request.url.query:
        target_path += f"?{request.url.query}"

    # Forward selected headers
    fwd_headers = {}
    for key in _FORWARD_HEADERS:
        val = request.headers.get(key)
        if val:
            fwd_headers[key] = val

    # Read body for non-GET requests
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    # Check if this looks like a media/streaming request (Range header or media paths)
    is_streaming = "range" in fwd_headers or any(
        seg in path for seg in ("/media/", "/video", "/audio", "/file/")
    )

    try:
        if is_streaming and request.method == "GET":
            return await _stream_response(spoke_key, target_path, fwd_headers)
        else:
            resp = await spoke_client.request(
                spoke_key,
                request.method,
                target_path,
                headers=fwd_headers,
                content=body,
                follow_redirects=True,
            )
            # Filter headers we don't want to forward
            resp_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in _DROP_HEADERS
            }
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers,
            )
    except httpx.ConnectError:
        return Response(
            content=f'{{"detail":"Spoke \'{spoke_key}\' is not reachable"}}',
            status_code=502,
            media_type="application/json",
        )
    except httpx.TimeoutException:
        return Response(
            content=f'{{"detail":"Spoke \'{spoke_key}\' timed out"}}',
            status_code=504,
            media_type="application/json",
        )


async def _stream_response(spoke_key: str, path: str, headers: dict) -> StreamingResponse:
    """Stream a response from a spoke (used for media files with Range support)."""
    client = spoke_client._get_client(spoke_key)

    # Follow redirects manually for streaming requests
    req = client.build_request("GET", path, headers=headers)
    resp = await client.send(req, stream=False, follow_redirects=True)

    # If the final response is small enough, we already have it
    # Re-request with streaming for actual media content
    if resp.status_code in (301, 302, 307, 308):
        # Shouldn't happen with follow_redirects=True, but safety net
        await resp.aclose()
        resp = await client.send(req, stream=True, follow_redirects=True)

    # For non-redirect final responses, re-request with streaming
    await resp.aclose()
    req2 = client.build_request("GET", path, headers=headers)
    resp2 = await client.send(req2, stream=True, follow_redirects=True)

    resp_headers = {}
    for key in ("content-type", "content-range", "content-length", "accept-ranges"):
        val = resp2.headers.get(key)
        if val:
            resp_headers[key] = val

    async def generate():
        try:
            async for chunk in resp2.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await resp2.aclose()

    return StreamingResponse(
        generate(),
        status_code=resp2.status_code,
        headers=resp_headers,
    )
