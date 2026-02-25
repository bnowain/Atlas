"""Manual reconciliation tool for LazyChroma cache integrity.

On-demand only — never runs automatically. Scans canonical spoke data
against Chroma and repairs inconsistencies.

Modes:
  check_only     — Report mismatches without fixing
  fix_missing    — Embed chunks not yet in Chroma
  fix_stale      — Re-embed chunks with content_hash or embedding_version mismatch
  delete_orphans — Remove Chroma entries whose source records no longer exist
  full_rebuild   — Wipe Chroma for scope and re-embed everything
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from app.config import EMBEDDING_VERSION
from app.services.rag import deterministic_chunking, embedding_service
from app.services.rag.retrieval_validator import _fetch_from_spoke

logger = logging.getLogger(__name__)

ALL_SOURCE_TYPES = [
    "civic_media", "article_tracker", "shasta_db", "facebook_offline",
    "shasta_pra", "facebook_monitor", "campaign_finance",
]
VALID_MODES = {"check_only", "fix_missing", "fix_stale", "delete_orphans", "full_rebuild"}


@dataclass
class ReconcileReport:
    chunks_scanned: int = 0
    missing: int = 0
    stale_content: int = 0
    stale_version: int = 0
    orphaned: int = 0
    fixed: int = 0
    deleted: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


async def reconcile(
    mode: str = "check_only",
    source_type: str | None = None,
) -> ReconcileReport:
    """Run reconciliation in the specified mode.

    Args:
        mode: One of check_only, fix_missing, fix_stale, delete_orphans, full_rebuild
        source_type: Optional scope to a single spoke type (None = all)
    """
    if mode not in VALID_MODES:
        report = ReconcileReport()
        report.errors.append(f"Invalid mode: {mode}. Must be one of: {VALID_MODES}")
        return report

    start = time.time()
    report = ReconcileReport()
    sources = [source_type] if source_type else ALL_SOURCE_TYPES

    # Full rebuild: wipe first, then re-embed everything
    if mode == "full_rebuild":
        for src in sources:
            try:
                deleted = embedding_service.wipe_collection(src)
                report.deleted += deleted
                logger.info("Wiped %d entries for %s", deleted, src)
            except Exception as exc:
                report.errors.append(f"Wipe {src}: {exc}")

        # Now re-embed everything
        for src in sources:
            try:
                records = await _fetch_from_spoke(src, "")
                chunks = deterministic_chunking.chunk_records(records)
                report.chunks_scanned += len(chunks)

                if chunks:
                    texts = [c.text for c in chunks]
                    embeddings = await embedding_service.embed_texts(texts)
                    embedding_service.upsert_chunks(chunks, embeddings)
                    report.fixed += len(chunks)

                logger.info("Rebuilt %s: %d chunks", src, len(chunks))
            except Exception as exc:
                report.errors.append(f"Rebuild {src}: {exc}")

        report.duration_seconds = round(time.time() - start, 2)
        return report

    # For all other modes: scan and compare
    for src in sources:
        try:
            # Fetch canonical records
            records = await _fetch_from_spoke(src, "")
            chunks = deterministic_chunking.chunk_records(records)
            report.chunks_scanned += len(chunks)

            # Build canonical chunk ID set
            canonical_ids = {c.chunk_id for c in chunks}
            chunk_map = {c.chunk_id: c for c in chunks}

            # Get existing Chroma entries for this source
            existing = embedding_service.get_by_ids(list(canonical_ids))

            # Classify each chunk
            missing_chunks = []
            stale_chunks = []

            for chunk in chunks:
                meta = existing.get(chunk.chunk_id)
                if meta is None:
                    report.missing += 1
                    missing_chunks.append(chunk)
                elif meta.get("content_hash") != chunk.content_hash:
                    report.stale_content += 1
                    stale_chunks.append(chunk)
                elif meta.get("embedding_version") != EMBEDDING_VERSION:
                    report.stale_version += 1
                    stale_chunks.append(chunk)

            # Check for orphans (Chroma entries not in canonical set)
            chroma_entries = embedding_service.get_all_ids_for_source(src)
            orphan_ids = [e["chunk_id"] for e in chroma_entries if e["chunk_id"] not in canonical_ids]
            report.orphaned += len(orphan_ids)

            # Apply fixes based on mode
            if mode == "fix_missing" and missing_chunks:
                texts = [c.text for c in missing_chunks]
                embeddings = await embedding_service.embed_texts(texts)
                embedding_service.upsert_chunks(missing_chunks, embeddings)
                report.fixed += len(missing_chunks)

            elif mode == "fix_stale" and stale_chunks:
                texts = [c.text for c in stale_chunks]
                embeddings = await embedding_service.embed_texts(texts)
                embedding_service.upsert_chunks(stale_chunks, embeddings)
                report.fixed += len(stale_chunks)

            elif mode == "delete_orphans" and orphan_ids:
                embedding_service.delete_by_ids(orphan_ids)
                report.deleted += len(orphan_ids)

        except Exception as exc:
            msg = f"{src}: {exc}"
            logger.warning("Reconcile error for %s: %s", src, exc)
            report.errors.append(msg)

    report.duration_seconds = round(time.time() - start, 2)
    logger.info("Reconcile %s complete: scanned=%d missing=%d stale_content=%d stale_version=%d orphaned=%d fixed=%d deleted=%d (%.1fs)",
                mode, report.chunks_scanned, report.missing, report.stale_content,
                report.stale_version, report.orphaned, report.fixed, report.deleted,
                report.duration_seconds)
    return report
