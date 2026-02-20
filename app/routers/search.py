"""Unified search across all spokes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import SearchResponse
from app.services import unified_search

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    sources: str | None = Query(None, description="Comma-separated spoke keys"),
    limit: int = Query(20, ge=1, le=100),
):
    source_list = sources.split(",") if sources else None
    results = await unified_search.search(q, source_list, limit)
    return SearchResponse(results=results, total=len(results))
