from __future__ import annotations

import os
from typing import Any

from db.supabase import SupabaseRepository
from rag.embeddings import embed_text


def retrieve_chunks(query: str, team_id: str, top_k: int | None = None) -> list[dict[str, Any]]:
    if top_k is None:
        top_k = int(os.getenv("TOP_K", "5"))

    query_embedding = embed_text(query)
    repository = SupabaseRepository()
    rows = repository.search_chunks(team_id=team_id, query_embedding=query_embedding, top_k=top_k)
    return rows


def format_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
