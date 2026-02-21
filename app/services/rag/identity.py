"""Deterministic hashing and chunk identity for LazyChroma RAG."""

from __future__ import annotations

import hashlib


def compute_content_hash(text: str) -> str:
    """SHA-256 hash of the raw text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_chunk_id(source_type: str, source_id: str, content_hash: str) -> str:
    """Deterministic chunk ID: SHA-256 of 'source_type:source_id:content_hash'."""
    composite = f"{source_type}:{source_id}:{content_hash}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()
