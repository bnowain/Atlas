"""Batch summary management — upload summaries to spoke projects via Atlas."""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from app.config import SPOKES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


class SummaryCoverage(BaseModel):
    """Summary coverage stats for a project."""
    project: str
    meetings_total: int = 0
    meetings_short: int = 0
    meetings_long: int = 0
    documents_total: int = 0
    documents_short: int = 0
    documents_long: int = 0


class BatchUploadResult(BaseModel):
    filename: str
    meeting_id: str
    summary_type: str
    success: bool
    error: Optional[str] = None


def _spoke_url(project: str) -> str:
    """Get base URL for a spoke project."""
    spoke = SPOKES.get(project)
    if not spoke:
        raise HTTPException(400, f"Unknown project: {project}")
    return spoke.base_url


@router.get("/coverage/{project}")
async def get_summary_coverage(project: str):
    """Get summary coverage stats for a project."""
    base_url = _spoke_url(project)

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(f"{base_url}/api/meetings/", params={"limit": 10000})
            r.raise_for_status()
            meetings = r.json()
        except Exception as e:
            raise HTTPException(502, f"Failed to reach {project}: {e}")

    meetings_short = sum(1 for m in meetings if m.get("summary_short"))
    meetings_long = sum(1 for m in meetings if m.get("summary_long"))

    # Aggregate document stats across all meetings
    docs_total = 0
    docs_short = 0
    docs_long = 0

    async with httpx.AsyncClient(timeout=15) as client:
        for m in meetings:
            mid = m.get("meeting_id")
            if not mid:
                continue
            try:
                r = await client.get(f"{base_url}/api/documents/{mid}")
                if r.status_code == 200:
                    docs = r.json()
                    docs_total += len(docs)
                    docs_short += sum(1 for d in docs if d.get("summary_short"))
                    docs_long += sum(1 for d in docs if d.get("summary_long"))
            except Exception:
                pass

    return SummaryCoverage(
        project=project,
        meetings_total=len(meetings),
        meetings_short=meetings_short,
        meetings_long=meetings_long,
        documents_total=docs_total,
        documents_short=docs_short,
        documents_long=docs_long,
    )


@router.post("/batch-upload/{project}")
async def batch_upload_summaries(
    project: str,
    files: list[UploadFile] = File(...),
):
    """
    Batch upload summary files to a spoke project.

    File naming convention:
      {meeting_id}_short.md  — short summary for that meeting
      {meeting_id}_long.md   — long summary for that meeting

    Forwards each file to the spoke's summary upload API.
    """
    base_url = _spoke_url(project)
    results: list[BatchUploadResult] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for upload_file in files:
            filename = upload_file.filename or ""

            # Parse filename: {meeting_id}_{short|long}.md
            stem = filename.rsplit(".", 1)[0] if "." in filename else filename
            parts = stem.rsplit("_", 1)

            if len(parts) != 2 or parts[1] not in ("short", "long"):
                results.append(BatchUploadResult(
                    filename=filename,
                    meeting_id="",
                    summary_type="",
                    success=False,
                    error=f"Invalid filename format. Expected {{meeting_id}}_short.md or {{meeting_id}}_long.md",
                ))
                continue

            meeting_id = parts[0]
            summary_type = parts[1]

            try:
                content = await upload_file.read()
                text = content.decode("utf-8", errors="replace")

                # Use the PATCH JSON endpoint (simpler than file upload)
                body = {}
                if summary_type == "short":
                    body["summary_short"] = text
                else:
                    body["summary_long"] = text

                r = await client.patch(
                    f"{base_url}/api/meetings/{meeting_id}/summary",
                    json=body,
                )

                if r.status_code == 200:
                    results.append(BatchUploadResult(
                        filename=filename,
                        meeting_id=meeting_id,
                        summary_type=summary_type,
                        success=True,
                    ))
                else:
                    results.append(BatchUploadResult(
                        filename=filename,
                        meeting_id=meeting_id,
                        summary_type=summary_type,
                        success=False,
                        error=f"HTTP {r.status_code}: {r.text[:200]}",
                    ))
            except Exception as e:
                results.append(BatchUploadResult(
                    filename=filename,
                    meeting_id=meeting_id,
                    summary_type=summary_type,
                    success=False,
                    error=str(e),
                ))

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    return {
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "results": [r.model_dump() for r in results],
    }
