from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


class SupabaseRepository:
    _memory_documents: list[dict[str, Any]] = []
    _memory_chunks: list[dict[str, Any]] = []
    _memory_queries: list[dict[str, Any]] = []
    _memory_agent_traces: list[dict[str, Any]] = []

    def __init__(self) -> None:
        self._client = None
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if url and key:
            try:
                from supabase import create_client

                self._client = create_client(url, key)
            except ImportError as exc:
                logger.warning("Supabase SDK unavailable, using in-memory repository", extra={"error": str(exc)})
                self._client = None
            except Exception as exc:
                logger.exception("Supabase client initialization failed, using in-memory repository", extra={"error": str(exc)})
                self._client = None

    def insert_document(self, team_id: str, filename: str, file_type: str, chunk_count: int) -> dict[str, Any]:
        payload = {
            "id": str(uuid4()),
            "team_id": team_id,
            "filename": filename,
            "file_type": file_type,
            "chunk_count": chunk_count,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            try:
                result = self._client.table("documents").insert(
                    {
                        "team_id": team_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_count": chunk_count,
                    }
                ).execute()
                if result.data:
                    return result.data[0]
            except Exception as exc:
                logger.exception("Failed to insert document in Supabase, falling back to in-memory", extra={"error": str(exc)})

        self._memory_documents.append(payload)
        return payload

    def insert_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> None:
        rows = [
            {
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": chunk["embedding"],
                "metadata": chunk.get("metadata", {}),
            }
            for chunk in chunks
        ]

        if self._client:
            try:
                self._client.table("chunks").insert(rows).execute()
                return
            except Exception as exc:
                logger.exception("Failed to insert chunks in Supabase, falling back to in-memory", extra={"error": str(exc)})

        for row in rows:
            memory_row = {"id": str(uuid4()), **row, "created_at": datetime.now(timezone.utc).isoformat()}
            self._memory_chunks.append(memory_row)

    def list_documents(self, team_id: str) -> list[dict[str, Any]]:
        if self._client:
            try:
                result = self._client.table("documents").select("*").eq("team_id", team_id).order("uploaded_at", desc=True).execute()
                return result.data or []
            except Exception as exc:
                logger.exception("Failed to list documents from Supabase, falling back to in-memory", extra={"error": str(exc)})

        docs = [doc for doc in self._memory_documents if doc["team_id"] == team_id]
        return sorted(docs, key=lambda item: item["uploaded_at"], reverse=True)

    def search_chunks(self, team_id: str, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if self._client:
            try:
                result = self._client.rpc(
                    "match_chunks",
                    {
                        "query_embedding": query_embedding,
                        "filter_team_id": team_id,
                        "match_count": top_k,
                    },
                ).execute()
                return result.data or []
            except Exception as exc:
                logger.exception("Failed to search chunks in Supabase, falling back to in-memory", extra={"error": str(exc)})

        document_map = {document["id"]: document for document in self._memory_documents if document["team_id"] == team_id}
        scored_rows: list[dict[str, Any]] = []
        for chunk in self._memory_chunks:
            document = document_map.get(chunk["document_id"])
            if not document:
                continue
            similarity = _cosine_similarity(query_embedding, chunk["embedding"])
            scored_rows.append(
                {
                    "id": chunk["id"],
                    "document_id": chunk["document_id"],
                    "filename": document["filename"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "metadata": chunk.get("metadata", {}),
                    "similarity": similarity,
                }
            )

        scored_rows.sort(key=lambda row: row["similarity"], reverse=True)
        return scored_rows[:top_k]

    def save_query(
        self,
        session_id: str,
        query_text: str,
        final_answer: str,
        scorecard: dict[str, Any],
        response_time_ms: int,
    ) -> dict[str, Any]:
        payload = {
            "id": str(uuid4()),
            "session_id": session_id,
            "query_text": query_text,
            "final_answer": final_answer,
            "overall_score": scorecard.get("overall"),
            "citation_accuracy": scorecard.get("citation_accuracy"),
            "insight_depth": scorecard.get("insight_depth"),
            "response_time_ms": response_time_ms,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            try:
                result = self._client.table("queries").insert(
                    {
                        "session_id": session_id,
                        "query_text": query_text,
                        "final_answer": final_answer,
                        "overall_score": scorecard.get("overall"),
                        "citation_accuracy": scorecard.get("citation_accuracy"),
                        "insight_depth": scorecard.get("insight_depth"),
                        "response_time_ms": response_time_ms,
                    }
                ).execute()
                if result.data:
                    return result.data[0]
            except Exception as exc:
                logger.exception("Failed to save query in Supabase, falling back to in-memory", extra={"error": str(exc)})

        self._memory_queries.append(payload)
        return payload

    def save_agent_traces(self, query_id: str, traces: list[dict[str, Any]]) -> None:
        rows = [
            {
                "query_id": query_id,
                "agent_name": trace.get("agent_name", ""),
                "model_name": trace.get("model_name", ""),
                "input_summary": trace.get("input_summary", ""),
                "output": trace.get("output", ""),
                "response_time_ms": trace.get("response_time_ms", 0),
                "metadata": trace.get("metadata", {}),
            }
            for trace in traces
        ]

        if self._client:
            try:
                self._client.table("agent_traces").insert(rows).execute()
                return
            except Exception as exc:
                logger.exception("Failed to save agent traces in Supabase, falling back to in-memory", extra={"error": str(exc)})

        for row in rows:
            memory_row = {"id": str(uuid4()), **row, "created_at": datetime.now(timezone.utc).isoformat()}
            self._memory_agent_traces.append(memory_row)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    a_vec = a[:length]
    b_vec = b[:length]
    dot = sum(x * y for x, y in zip(a_vec, b_vec))
    norm_a = math.sqrt(sum(x * x for x in a_vec))
    norm_b = math.sqrt(sum(y * y for y in b_vec))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
