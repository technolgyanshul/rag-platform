from __future__ import annotations
"""Query retrieval over embedded vectors with formatted source projection."""

from typing import Any

from core.config import get_settings
from rag.embedanything_pipeline import embed_query
from rag.qdrant_backend import QdrantVectorBackend
from rag.vector_backend import RetrievedChunk


def retrieve_chunks(query: str, user_id: str, top_k: int | None = None) -> list[dict[str, Any]]:
    """Retrieve top-K chunks for a query from the vector backend."""
    settings = get_settings()
    if top_k is None:
        top_k = settings.top_k
    if top_k < 1 or top_k > 20:
        raise ValueError("top_k must be between 1 and 20")
    if not query.strip():
        raise ValueError("query must not be empty")
    query_embedding = embed_query(query)
    rows = QdrantVectorBackend().search(query_vector=query_embedding, user_id=user_id, top_k=top_k)
    return [_retrieved_chunk_to_row(row) for row in rows]


def format_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert retrieved rows into compact source cards for API responses."""
    return [
        {
            "document_id": row.get("document_id", ""),
            "filename": row.get("filename", "unknown"),
            "chunk_index": row.get("chunk_index", -1),
            "content_preview": str(row.get("content", ""))[:240],
            "score": float(row.get("similarity", 0.0)),
        }
        for row in rows
    ]


def _retrieved_chunk_to_row(chunk: RetrievedChunk) -> dict[str, Any]:
    """Project a `RetrievedChunk` into the repository row-like structure."""
    return {
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "metadata": chunk.metadata,
        "similarity": chunk.score,
    }
