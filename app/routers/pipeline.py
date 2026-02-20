"""Media pipeline — Shasta-DB to civic_media transcription."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import media_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class TranscribeRequest(BaseModel):
    instance_id: int
    title: str | None = None


@router.post("/transcribe")
async def transcribe(req: TranscribeRequest):
    """Stream a file from Shasta-DB to civic_media for transcription."""
    result = await media_pipeline.transcribe_from_shasta(
        instance_id=req.instance_id,
        meeting_title=req.title,
    )
    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(502, result["error"])
    return result


@router.get("/transcribe/{meeting_id}/status")
async def transcribe_status(meeting_id: int):
    """Check processing status of a transcription pipeline run."""
    return await media_pipeline.get_pipeline_status(meeting_id)
