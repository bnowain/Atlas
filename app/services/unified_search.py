"""Unified search — parallel queries across all spokes, normalized results."""

from __future__ import annotations

import asyncio
import logging

from app.schemas import SearchResult
from app.services import spoke_client

logger = logging.getLogger(__name__)


async def search(
    query: str,
    sources: list[str] | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Search across all (or selected) spokes in parallel."""
    targets = sources or ["civic_media", "article_tracker", "shasta_db", "facebook_offline"]

    tasks = []
    for spoke in targets:
        searcher = _SEARCHERS.get(spoke)
        if searcher:
            tasks.append(searcher(query, limit))

    results_groups = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for group in results_groups:
        if isinstance(group, Exception):
            logger.warning("Search error: %s", group)
            continue
        all_results.extend(group)

    # Sort by date (newest first), with undated items last
    all_results.sort(key=lambda r: r.date or "", reverse=True)
    return all_results[:limit]


async def _search_civic_media(query: str, limit: int) -> list[SearchResult]:
    """Search civic_media meetings."""
    try:
        resp = await spoke_client.get("civic_media", "/api/meetings")
        if resp.status_code != 200:
            return []
        meetings = resp.json()
        q = query.lower()
        results = []
        for m in meetings:
            title = m.get("title", "") or ""
            if q in title.lower():
                results.append(SearchResult(
                    source="civic_media",
                    type="meeting",
                    title=title or f"Meeting #{m['id']}",
                    date=m.get("date") or m.get("created_at"),
                    url=f"/meetings",
                    metadata={"meeting_id": m["id"]},
                ))
        return results[:limit]
    except Exception:
        return []


async def _search_articles(query: str, limit: int) -> list[SearchResult]:
    """Search article-tracker."""
    try:
        resp = await spoke_client.get(
            "article_tracker",
            "/api/articles",
            params={"limit": limit},
        )
        if resp.status_code != 200:
            return []
        articles = resp.json()
        if not isinstance(articles, list):
            return []
        q = query.lower()
        results = []
        for a in articles:
            title = a.get("title", "") or ""
            if q in title.lower():
                results.append(SearchResult(
                    source="article_tracker",
                    type="article",
                    title=title,
                    snippet=a.get("description"),
                    url=a.get("url"),
                    date=a.get("published"),
                    metadata={"source": a.get("source")},
                ))
        return results[:limit]
    except Exception:
        return []


async def _search_shasta_db(query: str, limit: int) -> list[SearchResult]:
    """Search Shasta-DB archive."""
    try:
        resp = await spoke_client.get(
            "shasta_db",
            "/search",
            params={"q": query, "limit": limit},
        )
        if resp.status_code != 200:
            return []
        files = resp.json()
        if not isinstance(files, list):
            return []
        return [
            SearchResult(
                source="shasta_db",
                type="file",
                title=f.get("title") or f.get("path") or f"File #{f.get('id')}",
                metadata={"kind": f.get("kind"), "ext": f.get("ext")},
            )
            for f in files[:limit]
        ]
    except Exception:
        return []


async def _search_facebook(query: str, limit: int) -> list[SearchResult]:
    """Search Facebook messages and posts."""
    try:
        resp = await spoke_client.get(
            "facebook_offline",
            "/api/search/",
            params={"q": query, "limit": limit},
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", data.get("results", []))
        results = []
        for item in items[:limit]:
            results.append(SearchResult(
                source="facebook_offline",
                type=item.get("type", "message"),
                title=item.get("title") or item.get("text", "")[:80] or "Facebook result",
                snippet=item.get("text", "")[:200] if item.get("text") else None,
                date=item.get("timestamp") or item.get("date"),
            ))
        return results
    except Exception:
        return []


_SEARCHERS = {
    "civic_media": _search_civic_media,
    "article_tracker": _search_articles,
    "shasta_db": _search_shasta_db,
    "facebook_offline": _search_facebook,
}
