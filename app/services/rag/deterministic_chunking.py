"""Deterministic per-source chunking strategies for LazyChroma RAG.

Chunking is token-window based to avoid dependence on diarization boundaries
or speaker order. Chunk identity depends only on source_type, source_id, and
content_hash — never on chunk index or diarization labels.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.services.rag.identity import compute_content_hash, compute_chunk_id

logger = logging.getLogger(__name__)

# Approximate tokens per chunk (1 token ~ 4 chars for English text)
CHUNK_SIZE_CHARS = 2000   # ~500 tokens
OVERLAP_CHARS = 400       # ~100 tokens overlap


@dataclass
class Chunk:
    chunk_id: str
    text: str
    content_hash: str
    source_type: str
    source_id: str
    metadata: dict = field(default_factory=dict)


def chunk_records(records: list[dict]) -> list[Chunk]:
    """Chunk a list of spoke records into embeddable chunks.

    Each record must have at minimum: {source_type, source_id, text}
    plus optional metadata fields.
    """
    chunks = []
    for record in records:
        source_type = record["source_type"]
        source_id = str(record["source_id"])
        text = record.get("text", "")
        metadata = record.get("metadata", {})

        if not text or not text.strip():
            continue

        strategy = _STRATEGIES.get(source_type, _chunk_generic)
        chunks.extend(strategy(source_type, source_id, text, metadata))

    return chunks


def _chunk_civic_media(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Token-window chunks on raw transcript text. No diarization reliance."""
    return _sliding_window_chunks(source_type, source_id, text, metadata)


def _chunk_article_tracker(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Paragraph-aware chunking. Title + metadata prepended to first chunk."""
    prefix = ""
    if metadata.get("title"):
        prefix = f"Title: {metadata['title']}\n"
    if metadata.get("source"):
        prefix += f"Source: {metadata['source']}\n"
    if metadata.get("date"):
        prefix += f"Date: {metadata['date']}\n"
    if prefix:
        prefix += "\n"

    # Prepend metadata to text for first chunk context
    full_text = prefix + text
    return _sliding_window_chunks(source_type, source_id, full_text, metadata)


def _chunk_shasta_db(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Single chunk per file — these are metadata-only records."""
    content_hash = compute_content_hash(text)
    chunk_id = compute_chunk_id(source_type, source_id, content_hash)
    return [Chunk(
        chunk_id=chunk_id,
        text=text,
        content_hash=content_hash,
        source_type=source_type,
        source_id=source_id,
        metadata=metadata,
    )]


def _chunk_facebook_offline(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Message-group chunks by thread. Thread context prepended."""
    prefix = ""
    if metadata.get("thread_title"):
        prefix = f"Thread: {metadata['thread_title']}\n"
    if metadata.get("participants"):
        prefix += f"Participants: {metadata['participants']}\n"
    if prefix:
        prefix += "\n"

    full_text = prefix + text
    return _sliding_window_chunks(source_type, source_id, full_text, metadata)


def _chunk_shasta_pra(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Metadata prefix + sliding window for PRA request texts."""
    prefix = ""
    if metadata.get("pretty_id"):
        prefix = f"PRA Request: {metadata['pretty_id']}\n"
    if metadata.get("department"):
        prefix += f"Department: {metadata['department']}\n"
    if metadata.get("status"):
        prefix += f"Status: {metadata['status']}\n"
    if metadata.get("date"):
        prefix += f"Date: {metadata['date']}\n"
    if prefix:
        prefix += "\n"

    full_text = prefix + text
    return _sliding_window_chunks(source_type, source_id, full_text, metadata)


def _chunk_facebook_monitor(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Page/author metadata prefix + sliding window for Facebook Monitor posts."""
    prefix = ""
    if metadata.get("page_name"):
        prefix = f"Page: {metadata['page_name']}\n"
    if metadata.get("author"):
        prefix += f"Author: {metadata['author']}\n"
    if metadata.get("date"):
        prefix += f"Date: {metadata['date']}\n"
    if prefix:
        prefix += "\n"

    full_text = prefix + text
    return _sliding_window_chunks(source_type, source_id, full_text, metadata)


def _chunk_campaign_finance(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Transaction/filer metadata prefix + sliding window for campaign finance records."""
    prefix = ""
    if metadata.get("entity_name"):
        prefix = f"Entity: {metadata['entity_name']}\n"
    if metadata.get("schedule"):
        prefix += f"Schedule: {metadata['schedule']}\n"
    if metadata.get("date"):
        prefix += f"Date: {metadata['date']}\n"
    if prefix:
        prefix += "\n"

    full_text = prefix + text
    return _sliding_window_chunks(source_type, source_id, full_text, metadata)


def _chunk_reference_sections(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Single chunk per Brown Act section — short legal text, prefix with section number + title."""
    prefix = ""
    if metadata.get("section_num"):
        prefix = f"Section {metadata['section_num']}"
        if metadata.get("title"):
            prefix += f": {metadata['title']}"
        prefix += "\n\n"
    elif metadata.get("title"):
        prefix = f"{metadata['title']}\n\n"

    full_text = prefix + text
    content_hash = compute_content_hash(full_text)
    chunk_id = compute_chunk_id(source_type, source_id, content_hash)
    return [Chunk(
        chunk_id=chunk_id,
        text=full_text,
        content_hash=content_hash,
        source_type=source_type,
        source_id=source_id,
        metadata=metadata,
    )]


def _chunk_generic(source_type: str, source_id: str, text: str, metadata: dict) -> list[Chunk]:
    """Fallback: sliding window chunks."""
    return _sliding_window_chunks(source_type, source_id, text, metadata)


def _sliding_window_chunks(
    source_type: str,
    source_id: str,
    text: str,
    metadata: dict,
) -> list[Chunk]:
    """Split text into overlapping chunks using a sliding character window."""
    if len(text) <= CHUNK_SIZE_CHARS:
        content_hash = compute_content_hash(text)
        chunk_id = compute_chunk_id(source_type, source_id, content_hash)
        return [Chunk(
            chunk_id=chunk_id,
            text=text,
            content_hash=content_hash,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
        )]

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE_CHARS
        chunk_text = text[start:end]

        content_hash = compute_content_hash(chunk_text)
        chunk_id = compute_chunk_id(source_type, source_id, content_hash)

        chunks.append(Chunk(
            chunk_id=chunk_id,
            text=chunk_text,
            content_hash=content_hash,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
        ))

        start += CHUNK_SIZE_CHARS - OVERLAP_CHARS
        if start >= len(text):
            break

    return chunks


_STRATEGIES = {
    "civic_media": _chunk_civic_media,
    "article_tracker": _chunk_article_tracker,
    "shasta_db": _chunk_shasta_db,
    "facebook_offline": _chunk_facebook_offline,
    "shasta_pra": _chunk_shasta_pra,
    "facebook_monitor": _chunk_facebook_monitor,
    "campaign_finance": _chunk_campaign_finance,
    "reference_sections": _chunk_reference_sections,
}
