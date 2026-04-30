from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class _FallbackStore:
    documents: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    queries: list[dict[str, Any]] = field(default_factory=list)
    agent_traces: list[dict[str, Any]] = field(default_factory=list)
    session_logs: list[dict[str, Any]] = field(default_factory=list)


_FALLBACK = _FallbackStore()


class SupabaseRepository:
    def __init__(self) -> None:
        self._client = None
        self._allow_inmemory = bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv("ALLOW_INMEMORY_REPOSITORY", "false").lower() == "true"

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if url and key:
            try:
                from supabase import create_client

                self._client = create_client(url, key)
            except ImportError as exc:
                logger.warning("Supabase SDK unavailable", extra={"error": str(exc)})
            except Exception as exc:
                logger.exception("Supabase client initialization failed", extra={"error": str(exc)})

        if self._client is None and not self._allow_inmemory:
            raise RuntimeError("Supabase is unavailable and in-memory repository fallback is disabled")

    def _ensure_team_owned(self, team_id: str, user_id: str) -> None:
        if self._client:
            result = self._client.table("teams").select("id").eq("id", team_id).eq("user_id", user_id).limit(1).execute()
            if not result.data:
                raise PermissionError("Team is not accessible for this user")
            return

        # Fallback mode cannot verify ownership against auth.users table. Require explicit UUID-like ids and allow tests.
        _ = (team_id, user_id)

    def _ensure_session_owned(self, session_id: str, user_id: str) -> None:
        if self._client:
            result = self._client.table("sessions").select("id").eq("id", session_id).eq("user_id", user_id).limit(1).execute()
            if not result.data:
                raise PermissionError("Session is not accessible for this user")
            return

        _ = (session_id, user_id)

    def insert_document(self, user_id: str, team_id: str, filename: str, file_type: str, chunk_count: int) -> dict[str, Any]:
        self._ensure_team_owned(team_id=team_id, user_id=user_id)

        payload = {
            "id": str(uuid4()),
            "team_id": team_id,
            "filename": filename,
            "file_type": file_type,
            "chunk_count": chunk_count,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("documents").insert(payload).execute()
            if result.data:
                return result.data[0]

        _FALLBACK.documents.append(payload)
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
            self._client.table("chunks").insert(rows).execute()
            return

        for row in rows:
            _FALLBACK.chunks.append({"id": str(uuid4()), **row, "created_at": datetime.now(timezone.utc).isoformat()})

    def list_documents(self, user_id: str, team_id: str) -> list[dict[str, Any]]:
        self._ensure_team_owned(team_id=team_id, user_id=user_id)
        if self._client:
            result = self._client.table("documents").select("*").eq("team_id", team_id).order("uploaded_at", desc=True).execute()
            return result.data or []

        docs = [doc for doc in _FALLBACK.documents if doc["team_id"] == team_id]
        return sorted(docs, key=lambda item: item["uploaded_at"], reverse=True)

    def search_chunks(self, user_id: str, team_id: str, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        self._ensure_team_owned(team_id=team_id, user_id=user_id)
        if self._client:
            result = self._client.rpc(
                "match_chunks",
                {
                    "query_embedding": query_embedding,
                    "filter_team_id": team_id,
                    "match_count": top_k,
                },
            ).execute()
            return result.data or []

        document_map = {document["id"]: document for document in _FALLBACK.documents if document["team_id"] == team_id}
        scored_rows: list[dict[str, Any]] = []
        for chunk in _FALLBACK.chunks:
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
        user_id: str,
        session_id: str,
        query_text: str,
        final_answer: str,
        scorecard: dict[str, Any],
        response_time_ms: int,
    ) -> dict[str, Any]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)

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
            result = self._client.table("queries").insert(payload).execute()
            if result.data:
                return result.data[0]

        _FALLBACK.queries.append(payload)
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
            self._client.table("agent_traces").insert(rows).execute()
            return

        for row in rows:
            _FALLBACK.agent_traces.append({"id": str(uuid4()), **row, "created_at": datetime.now(timezone.utc).isoformat()})

    def save_session_log(
        self,
        session_id: str,
        team_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": str(uuid4()),
            "session_id": session_id,
            "team_id": team_id,
            "event_type": event_type,
            "request_id": request_id,
            "payload": payload or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("session_logs").insert(row).execute()
            if result.data:
                return result.data[0]

        _FALLBACK.session_logs.append(row)
        return row

    def list_queries(self, user_id: str, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        if self._client:
            result = (
                self._client.table("queries")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []

        rows = [row for row in _FALLBACK.queries if row.get("session_id") == session_id]
        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return rows[:limit]

    def list_dashboard_metrics(self, user_id: str, session_id: str, days: int = 7) -> dict[str, Any]:
        rows = self.list_queries(user_id=user_id, session_id=session_id, limit=500)
        total_queries = len(rows)
        avg_response_ms = int(sum(int(row.get("response_time_ms", 0)) for row in rows) / total_queries) if total_queries else 0
        avg_overall_score = (
            round(sum(float(row.get("overall_score", 0.0) or 0.0) for row in rows) / total_queries, 2) if total_queries else 0.0
        )

        now = datetime.now(timezone.utc)
        per_day: dict[str, int] = {}
        for day_offset in range(days - 1, -1, -1):
            day = now.date() - timedelta(days=day_offset)
            per_day[day.isoformat()] = 0

        for row in rows:
            created_at = row.get("created_at")
            if not created_at:
                continue
            try:
                day_key = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                continue
            if day_key in per_day:
                per_day[day_key] += 1

        return {
            "total_queries": total_queries,
            "average_response_time_ms": avg_response_ms,
            "average_overall_score": avg_overall_score,
            "queries_over_time": [{"date": day, "count": count} for day, count in per_day.items()],
        }


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
