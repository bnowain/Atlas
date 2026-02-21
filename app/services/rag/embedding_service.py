"""Embedding service — all Chroma interactions go through this module.

Uses Ollama's embedding endpoint with nomic-embed-text (768-dim).
Chroma is a persistent cache only; canonical spoke DBs remain authoritative.
"""

from __future__ import annotations

import logging
from typing import Sequence

import httpx
import chromadb

from app.config import OLLAMA_BASE_URL, EMBEDDING_MODEL, EMBEDDING_VERSION, CHROMA_PERSIST_DIR
from app.services.rag.deterministic_chunking import Chunk

logger = logging.getLogger(__name__)

# Singleton Chroma client + collection
_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "atlas_rag"
EMBED_BATCH_SIZE = 32


def get_collection() -> chromadb.Collection:
    """Get or create the singleton Chroma collection."""
    global _chroma_client, _collection
    if _collection is None:
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def embed_text(text: str) -> list[float]:
    """Embed a single text string via Ollama /api/embed."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        # Ollama returns {"embeddings": [[...]]} for /api/embed
        return data["embeddings"][0]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts via Ollama /api/embed (batch)."""
    if not texts:
        return []

    all_embeddings = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i:i + EMBED_BATCH_SIZE]
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": EMBEDDING_MODEL, "input": batch},
            )
            resp.raise_for_status()
            data = resp.json()
            all_embeddings.extend(data["embeddings"])

    return all_embeddings


def upsert_chunks(chunks: Sequence[Chunk], embeddings: list[list[float]]) -> None:
    """Store chunks with embeddings and full metadata in Chroma."""
    if not chunks:
        return

    collection = get_collection()
    ids = [c.chunk_id for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [
        {
            "content_hash": c.content_hash,
            "embedding_version": EMBEDDING_VERSION,
            "source_type": c.source_type,
            "source_id": c.source_id,
            "date": c.metadata.get("date", ""),
            "speaker_ids": c.metadata.get("speaker_ids", ""),
        }
        for c in chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query_similar(
    query_embedding: list[float],
    source_types: list[str] | None = None,
    n_results: int = 5,
) -> list[dict]:
    """Similarity search in Chroma, optionally filtered by source_type."""
    collection = get_collection()

    where_filter = None
    if source_types and len(source_types) == 1:
        where_filter = {"source_type": source_types[0]}
    elif source_types and len(source_types) > 1:
        where_filter = {"source_type": {"$in": source_types}}

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    # Flatten Chroma's nested list format
    items = []
    if results and results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            items.append({
                "chunk_id": chunk_id,
                "text": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })

    return items


def get_by_ids(chunk_ids: list[str]) -> dict[str, dict]:
    """Fetch existing Chroma entries by chunk_id. Returns {chunk_id: metadata}."""
    if not chunk_ids:
        return {}

    collection = get_collection()
    results = collection.get(
        ids=chunk_ids,
        include=["metadatas"],
    )

    found = {}
    if results and results["ids"]:
        for i, cid in enumerate(results["ids"]):
            found[cid] = results["metadatas"][i] if results["metadatas"] else {}

    return found


def delete_by_ids(chunk_ids: list[str]) -> None:
    """Delete specific chunk IDs from Chroma."""
    if not chunk_ids:
        return
    collection = get_collection()
    collection.delete(ids=chunk_ids)


def delete_by_source(source_type: str, source_id: str | None = None) -> None:
    """Delete all embeddings for a source type, optionally scoped to a source ID."""
    collection = get_collection()
    if source_id:
        collection.delete(where={"$and": [{"source_type": source_type}, {"source_id": source_id}]})
    else:
        collection.delete(where={"source_type": source_type})


def get_all_ids_for_source(source_type: str | None = None) -> list[dict]:
    """Get all chunk IDs and metadata in Chroma, optionally filtered by source_type."""
    collection = get_collection()
    kwargs: dict = {"include": ["metadatas"]}
    if source_type:
        kwargs["where"] = {"source_type": source_type}

    # Chroma .get() with no ids returns all
    results = collection.get(**kwargs)

    items = []
    if results and results["ids"]:
        for i, cid in enumerate(results["ids"]):
            items.append({
                "chunk_id": cid,
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
            })

    return items


def wipe_collection(source_type: str | None = None) -> int:
    """Wipe all entries, optionally scoped to a source_type. Returns count deleted."""
    collection = get_collection()
    if source_type:
        existing = get_all_ids_for_source(source_type)
        ids = [e["chunk_id"] for e in existing]
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    else:
        count = collection.count()
        # Wipe by recreating
        global _collection
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        _chroma_client.delete_collection(COLLECTION_NAME)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return count
