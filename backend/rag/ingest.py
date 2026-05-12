from __future__ import annotations

from typing import Any

from rag.embedanything_pipeline import EmbeddedChunk, embed_file_semantic


def ingest_document(file_path: str, file_type: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> dict[str, Any]:
    del chunk_size, chunk_overlap
    chunks = embed_file_semantic(file_path=file_path, file_type=file_type)
    return {"chunks": [_chunk_payload(chunk) for chunk in chunks]}


def _chunk_payload(chunk: EmbeddedChunk) -> dict[str, Any]:
    return {
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "embedding": chunk.embedding,
        "metadata": chunk.metadata,
    }
