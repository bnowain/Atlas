"""Media pipeline — stream files from Shasta-DB to civic_media for transcription."""

from __future__ import annotations

import logging

import httpx

from app.services import spoke_client

logger = logging.getLogger(__name__)


async def transcribe_from_shasta(instance_id: int, meeting_title: str | None = None) -> dict:
    """
    Stream a file from Shasta-DB → create meeting in civic_media → upload for processing.

    Returns: {"meeting_id": int, "status": str}
    """
    # 1. Create meeting in civic_media
    title = meeting_title or f"Shasta-DB file #{instance_id}"
    create_resp = await spoke_client.post(
        "civic_media",
        "/api/meetings",
        json={"title": title},
    )
    if create_resp.status_code not in (200, 201):
        return {"error": f"Failed to create meeting: {create_resp.status_code} {create_resp.text}"}

    meeting = create_resp.json()
    meeting_id = meeting["id"]

    # 2. Stream file from Shasta-DB
    try:
        shasta_client = spoke_client._get_client("shasta_db")
        async with shasta_client.stream("GET", f"/file/{instance_id}") as file_resp:
            if file_resp.status_code != 200:
                return {"error": f"Failed to fetch file from Shasta-DB: {file_resp.status_code}"}

            content_type = file_resp.headers.get("content-type", "application/octet-stream")

            # Collect the file content (chunked transfer to civic_media isn't supported by multipart)
            chunks = []
            async for chunk in file_resp.aiter_bytes(chunk_size=65536):
                chunks.append(chunk)
            file_bytes = b"".join(chunks)

    except Exception as exc:
        return {"error": f"Error streaming from Shasta-DB: {exc}"}

    # 3. Upload to civic_media
    # Determine a reasonable filename
    filename = f"shasta_{instance_id}.mp4"
    if "audio" in content_type:
        filename = f"shasta_{instance_id}.wav"

    upload_resp = await spoke_client.post(
        "civic_media",
        f"/api/media/{meeting_id}/upload",
        files={"file": (filename, file_bytes, content_type)},
    )

    if upload_resp.status_code not in (200, 201, 202):
        return {"error": f"Failed to upload to civic_media: {upload_resp.status_code} {upload_resp.text}"}

    return {
        "meeting_id": meeting_id,
        "status": "processing",
        "source": f"shasta_db:file:{instance_id}",
    }


async def get_pipeline_status(meeting_id: int) -> dict:
    """Check the processing status of a meeting."""
    resp = await spoke_client.get("civic_media", f"/api/media/{meeting_id}/status")
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}"}
    return resp.json()
