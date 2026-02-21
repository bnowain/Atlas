"""Lazy validation retrieval — the core LazyChroma logic.

On every retrieval:
1. Fetch candidates from spokes via spoke_client
2. Chunk deterministically
3. Validate each chunk against Chroma (insert/re-embed/reuse)
4. Embed query
5. Similarity search
6. Return top results
"""

from __future__ import annotations

import logging

from app.config import EMBEDDING_VERSION
from app.services import spoke_client
from app.services.rag import deterministic_chunking, embedding_service
from app.services.rag.deterministic_chunking import Chunk

logger = logging.getLogger(__name__)

# Max records to fetch per spoke for candidate gathering
_MAX_CANDIDATES_PER_SPOKE = 50


async def retrieve(
    query: str,
    source_types: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Semantic search with lazy validation.

    Returns a list of result dicts with text, metadata, and distance.
    """
    active_sources = source_types or ["civic_media", "article_tracker", "shasta_db", "facebook_offline"]

    # 1. Fetch candidates from spokes
    candidates = await _fetch_candidates(query, active_sources)
    if not candidates:
        logger.info("No candidates fetched from spokes for query: %s", query[:80])
        return []

    # 2. Chunk candidates deterministically
    chunks = deterministic_chunking.chunk_records(candidates)
    if not chunks:
        return []

    # 3. Validate and embed chunks against Chroma
    await _validate_and_embed(chunks)

    # 4. Embed query
    query_embedding = await embedding_service.embed_text(query)

    # 5. Similarity search in Chroma
    results = embedding_service.query_similar(
        query_embedding=query_embedding,
        source_types=active_sources,
        n_results=limit,
    )

    return results


async def _fetch_candidates(query: str, source_types: list[str]) -> list[dict]:
    """Fetch candidate records from spoke APIs for semantic ranking."""
    candidates = []

    for source_type in source_types:
        try:
            records = await _fetch_from_spoke(source_type, query)
            candidates.extend(records)
        except Exception as exc:
            logger.warning("Failed to fetch from %s: %s", source_type, exc)

    return candidates


async def _fetch_from_spoke(source_type: str, query: str) -> list[dict]:
    """Fetch records from a single spoke, returning normalized records."""
    records = []

    if source_type == "civic_media":
        # Search meetings and get transcripts for matches
        try:
            resp = await spoke_client.get("civic_media", "/api/meetings/")
            if resp.status_code == 200:
                meetings = resp.json()
                query_lower = query.lower()
                # Filter to relevant meetings
                matched = [m for m in meetings if query_lower in (m.get("title", "") or "").lower()]
                if not matched:
                    matched = meetings[:10]  # fallback: recent meetings
                for m in matched[:_MAX_CANDIDATES_PER_SPOKE]:
                    mid = m.get("meeting_id") or m.get("id")
                    if not mid:
                        continue
                    seg_resp = await spoke_client.get("civic_media", f"/api/segments/{mid}")
                    if seg_resp.status_code == 200:
                        segments = seg_resp.json()
                        # Combine all segment text for this meeting
                        text_parts = []
                        for seg in (segments if isinstance(segments, list) else [segments]):
                            seg_text = seg.get("text", "") or seg.get("content", "")
                            if seg_text:
                                text_parts.append(seg_text)
                        if text_parts:
                            records.append({
                                "source_type": "civic_media",
                                "source_id": str(mid),
                                "text": "\n".join(text_parts),
                                "metadata": {
                                    "title": m.get("title", ""),
                                    "date": m.get("meeting_date", "") or m.get("date", ""),
                                    "speaker_ids": ",".join(str(s) for s in m.get("speaker_ids", [])),
                                },
                            })
        except Exception as exc:
            logger.warning("civic_media fetch error: %s", exc)

    elif source_type == "article_tracker":
        try:
            params = {"limit": _MAX_CANDIDATES_PER_SPOKE}
            if query:
                params["q"] = query
            resp = await spoke_client.get("article_tracker", "/api/articles", params=params)
            if resp.status_code == 200:
                articles = resp.json()
                if isinstance(articles, list):
                    for a in articles[:_MAX_CANDIDATES_PER_SPOKE]:
                        text = a.get("content", "") or a.get("snippet", "") or a.get("title", "")
                        if text:
                            records.append({
                                "source_type": "article_tracker",
                                "source_id": str(a.get("id", "")),
                                "text": text,
                                "metadata": {
                                    "title": a.get("title", ""),
                                    "source": a.get("source", ""),
                                    "date": a.get("published_date", "") or a.get("date", ""),
                                },
                            })
        except Exception as exc:
            logger.warning("article_tracker fetch error: %s", exc)

    elif source_type == "shasta_db":
        try:
            params = {"limit": _MAX_CANDIDATES_PER_SPOKE}
            if query:
                params["q"] = query
            resp = await spoke_client.get("shasta_db", "/search", params=params)
            if resp.status_code == 200:
                files = resp.json()
                if isinstance(files, list):
                    for f in files[:_MAX_CANDIDATES_PER_SPOKE]:
                        # Shasta-DB files are metadata-only
                        parts = []
                        if f.get("title"):
                            parts.append(f"Title: {f['title']}")
                        if f.get("kind"):
                            parts.append(f"Kind: {f['kind']}")
                        if f.get("people"):
                            parts.append(f"People: {f['people']}")
                        if f.get("dates"):
                            parts.append(f"Dates: {f['dates']}")
                        if f.get("notes"):
                            parts.append(f"Notes: {f['notes']}")
                        text = "\n".join(parts) if parts else f.get("title", "")
                        if text:
                            records.append({
                                "source_type": "shasta_db",
                                "source_id": str(f.get("id", "") or f.get("instance_id", "")),
                                "text": text,
                                "metadata": {
                                    "title": f.get("title", ""),
                                    "kind": f.get("kind", ""),
                                    "date": f.get("dates", ""),
                                },
                            })
        except Exception as exc:
            logger.warning("shasta_db fetch error: %s", exc)

    elif source_type == "facebook_offline":
        try:
            params = {"q": query, "limit": _MAX_CANDIDATES_PER_SPOKE}
            resp = await spoke_client.get("facebook_offline", "/api/messages/search/", params=params)
            if resp.status_code == 200:
                data = resp.json()
                messages = data if isinstance(data, list) else data.get("messages", [])
                for msg in messages[:_MAX_CANDIDATES_PER_SPOKE]:
                    text = msg.get("content", "") or msg.get("text", "")
                    if text:
                        records.append({
                            "source_type": "facebook_offline",
                            "source_id": str(msg.get("id", "")),
                            "text": text,
                            "metadata": {
                                "thread_title": msg.get("thread_title", ""),
                                "participants": msg.get("participants", ""),
                                "date": msg.get("timestamp", "") or msg.get("date", ""),
                            },
                        })
        except Exception as exc:
            logger.warning("facebook_offline fetch error: %s", exc)

    return records


async def _validate_and_embed(chunks: list[Chunk]) -> None:
    """Validate chunks against Chroma and embed/re-embed as needed."""
    if not chunks:
        return

    # Look up which chunks already exist in Chroma
    chunk_ids = [c.chunk_id for c in chunks]
    existing = embedding_service.get_by_ids(chunk_ids)

    # Determine which chunks need embedding
    to_embed: list[Chunk] = []

    for chunk in chunks:
        existing_meta = existing.get(chunk.chunk_id)

        if existing_meta is None:
            # Not found → needs embedding
            to_embed.append(chunk)
        elif existing_meta.get("content_hash") != chunk.content_hash:
            # Content changed → re-embed
            to_embed.append(chunk)
        elif existing_meta.get("embedding_version") != EMBEDDING_VERSION:
            # Embedding version mismatch → re-embed
            to_embed.append(chunk)
        # else: valid, reuse

    if not to_embed:
        logger.debug("All %d chunks validated, no re-embedding needed", len(chunks))
        return

    logger.info("Embedding %d/%d chunks (new/stale)", len(to_embed), len(chunks))

    # Batch embed
    texts = [c.text for c in to_embed]
    embeddings = await embedding_service.embed_texts(texts)

    # Upsert into Chroma
    embedding_service.upsert_chunks(to_embed, embeddings)
