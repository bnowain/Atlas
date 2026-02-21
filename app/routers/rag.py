"""RAG management endpoints — pre-index and reconcile."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.rag import pre_index as pre_index_service
from app.services.rag import reconcile_embeddings

router = APIRouter(prefix="/api/rag", tags=["rag"])


class PreIndexRequest(BaseModel):
    source_type: str | None = None


class ReconcileRequest(BaseModel):
    mode: str = "check_only"
    source_type: str | None = None


@router.post("/pre-index")
async def pre_index(req: PreIndexRequest):
    """Bulk pre-index spoke data into Chroma (performance optimization)."""
    report = await pre_index_service.pre_index(source_type=req.source_type)
    return report


@router.post("/reconcile")
async def reconcile(req: ReconcileRequest):
    """Manual reconciliation of Chroma cache against canonical spoke data."""
    report = await reconcile_embeddings.reconcile(
        mode=req.mode,
        source_type=req.source_type,
    )
    return asdict(report)
