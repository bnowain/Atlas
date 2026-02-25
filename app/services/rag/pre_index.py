"""Optional bulk pre-indexing for LazyChroma RAG.

Pre-indexing is a performance optimization only — correctness never depends on it.
Iterates spoke records, chunks deterministically, and embeds into Chroma.
"""

from __future__ import annotations

import logging
import time

from app.config import EMBEDDING_VERSION
from app.services.rag import deterministic_chunking, embedding_service
from app.services.rag.retrieval_validator import _fetch_from_spoke

logger = logging.getLogger(__name__)

ALL_SOURCE_TYPES = ["civic_media", "article_tracker", "shasta_db", "facebook_offline", "shasta_pra", "facebook_monitor", "campaign_finance", "reference_sections"]


async def pre_index(source_type: str | None = None) -> dict:
    """Bulk pre-index spoke data into Chroma.

    Returns a summary report.
    """
    start = time.time()
    sources = [source_type] if source_type else ALL_SOURCE_TYPES

    total_records = 0
    total_chunks = 0
    total_embedded = 0
    errors: list[str] = []

    for src in sources:
        try:
            # Fetch all records (empty query = all)
            records = await _fetch_from_spoke(src, "")
            total_records += len(records)

            # Chunk
            chunks = deterministic_chunking.chunk_records(records)
            total_chunks += len(chunks)

            if not chunks:
                continue

            # Check existing
            chunk_ids = [c.chunk_id for c in chunks]
            existing = embedding_service.get_by_ids(chunk_ids)

            # Filter to chunks needing embedding
            to_embed = []
            for chunk in chunks:
                meta = existing.get(chunk.chunk_id)
                if meta is None:
                    to_embed.append(chunk)
                elif meta.get("content_hash") != chunk.content_hash:
                    to_embed.append(chunk)
                elif meta.get("embedding_version") != EMBEDDING_VERSION:
                    to_embed.append(chunk)

            if to_embed:
                texts = [c.text for c in to_embed]
                embeddings = await embedding_service.embed_texts(texts)
                embedding_service.upsert_chunks(to_embed, embeddings)
                total_embedded += len(to_embed)

            logger.info("Pre-indexed %s: %d records → %d chunks, %d embedded",
                        src, len(records), len(chunks), len(to_embed))

        except Exception as exc:
            msg = f"{src}: {exc}"
            logger.warning("Pre-index error for %s: %s", src, exc)
            errors.append(msg)

    duration = time.time() - start
    report = {
        "records_fetched": total_records,
        "chunks_created": total_chunks,
        "chunks_embedded": total_embedded,
        "errors": errors,
        "duration_seconds": round(duration, 2),
    }
    logger.info("Pre-index complete: %s", report)
    return report
