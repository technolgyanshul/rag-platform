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
    sessions: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    queries: list[dict[str, Any]] = field(default_factory=list)


_FALLBACK = _FallbackStore()


def reset_fallback_store() -> None:
    _FALLBACK.sessions.clear()
    _FALLBACK.documents.clear()
    _FALLBACK.chunks.clear()
    _FALLBACK.queries.clear()


class SupabaseRepository:
    def __init__(self) -> None:
        self._client = None
        self._allow_inmemory = bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv("ALLOW_INMEMORY_REPOSITORY", "false").lower() == "true"

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if url and key and not self._allow_inmemory:
            try:
                from supabase import create_client

                self._client = create_client(url, key)
            except ImportError as exc:
                logger.warning("Supabase SDK unavailable", extra={"error": str(exc)})
            except Exception as exc:
                logger.exception("Supabase client initialization failed", extra={"error": str(exc)})

        if self._client is None and not self._allow_inmemory:
            raise RuntimeError("Supabase is unavailable and in-memory repository fallback is disabled")

    def _workspace_id_for_user(self, user_id: str) -> str:
        return user_id

    def _ensure_workspace(self, user_id: str) -> str:
        workspace_id = self._workspace_id_for_user(user_id)
        if self._client:
            result = self._client.table("teams").select("id").eq("id", workspace_id).eq("user_id", user_id).limit(1).execute()
            if result.data:
                return workspace_id

            payload = {
                "id": workspace_id,
                "user_id": user_id,
                "name": "Demo Workspace",
                "domain": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            result = self._client.table("teams").insert(payload).execute()
            if result.data:
                return str(result.data[0].get("id", workspace_id))
            raise RuntimeError("Failed to create demo workspace")

        return workspace_id

    def _find_fallback_session(self, session_id: str) -> dict[str, Any] | None:
        for row in _FALLBACK.sessions:
            if row["id"] == session_id:
                return row
        return None

    def _ensure_session_owned(self, session_id: str, user_id: str) -> None:
        session = self.get_session(user_id=user_id, session_id=session_id)
        if session is None:
            raise PermissionError("Session is not accessible for this user")

    def get_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        if self._client:
            result = self._client.table("sessions").select("*").eq("id", session_id).limit(1).execute()
            if not result.data:
                return None
            row = result.data[0]
            if str(row.get("user_id", "")) != user_id:
                raise PermissionError("Session is not accessible for this user")
            return row

        row = self._find_fallback_session(session_id)
        if row is None:
            return None
        if str(row.get("user_id", "")) != user_id:
            raise PermissionError("Session is not accessible for this user")
        return row

    def create_session(
        self,
        user_id: str,
        title: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        workspace_id = self._ensure_workspace(user_id)
        payload = {
            "id": session_id or str(uuid4()),
            "user_id": user_id,
            "team_id": workspace_id,
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("sessions").insert(payload).execute()
            if result.data:
                return result.data[0]
            raise RuntimeError("Failed to create session")

        existing = self._find_fallback_session(payload["id"])
        if existing:
            if str(existing.get("user_id", "")) != user_id:
                raise PermissionError("Session is not accessible for this user")
            return existing

        _FALLBACK.sessions.append(payload)
        return payload

    def insert_document(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        chunk_count: int,
        storage_path: str | None = None,
        content_type: str | None = None,
        file_size_bytes: int | None = None,
        file_sha256: str | None = None,
        extracted_text_sha256: str | None = None,
        chunking_config: dict[str, Any] | None = None,
        embedding_model_version: str | None = None,
        embedding_bge_model_version: str | None = None,
        index_version: str | None = None,
        index_backend: str = "legacy_supabase_pgvector",
        index_status: str = "legacy_unindexed",
        indexed_at: str | None = None,
        index_error: str | None = None,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        workspace_id = self._ensure_workspace(user_id)
        payload = {
            "id": document_id or str(uuid4()),
            "team_id": workspace_id,
            "filename": filename,
            "file_type": file_type,
            "chunk_count": chunk_count,
            "storage_bucket": "knowledge-files",
            "storage_path": storage_path,
            "content_type": content_type,
            "file_size_bytes": file_size_bytes if file_size_bytes is not None else 0,
            "file_sha256": file_sha256,
            "extracted_text_sha256": extracted_text_sha256,
            "chunking_config": chunking_config or {"chunk_size": 1000, "chunk_overlap": 150},
            "embedding_model_version": embedding_model_version,
            "embedding_bge_model_version": embedding_bge_model_version,
            "index_version": index_version,
            "index_backend": index_backend,
            "index_status": index_status,
            "indexed_at": indexed_at,
            "index_error": index_error,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("documents").insert(payload).execute()
            if result.data:
                return result.data[0]

        _FALLBACK.documents.append(payload)
        return payload

    def update_document_index_status(
        self,
        user_id: str,
        document_id: str,
        status: str,
        backend: str,
        error: str | None = None,
        chunk_count: int | None = None,
    ) -> dict[str, Any]:
        workspace_id = self._ensure_workspace(user_id)
        indexed_at = datetime.now(timezone.utc).isoformat() if status == "indexed" else None
        payload = {
            "index_backend": backend,
            "index_status": status,
            "indexed_at": indexed_at,
            "index_error": error,
        }
        if chunk_count is not None:
            payload["chunk_count"] = chunk_count

        if self._client:
            result = (
                self._client.table("documents")
                .update(payload)
                .eq("id", document_id)
                .eq("team_id", workspace_id)
                .execute()
            )
            if result.data:
                return result.data[0]
            raise PermissionError("Document is not accessible for this user")

        for document in _FALLBACK.documents:
            if document.get("id") != document_id:
                continue
            if document.get("team_id") != workspace_id:
                raise PermissionError("Document is not accessible for this user")
            document.update(payload)
            return document

        raise PermissionError("Document is not accessible for this user")

    def find_document_by_fingerprint(
        self,
        user_id: str,
        file_sha256: str,
        chunking_config: dict[str, Any],
        embedding_model_version: str | None,
        embedding_bge_model_version: str | None,
        index_version: str | None,
    ) -> dict[str, Any] | None:
        workspace_id = self._ensure_workspace(user_id)
        if self._client:
            query = (
                self._client.table("documents")
                .select("*")
                .eq("team_id", workspace_id)
                .eq("file_sha256", file_sha256)
                .eq("chunking_config", chunking_config)
            )
            for column, value in (
                ("embedding_model_version", embedding_model_version),
                ("embedding_bge_model_version", embedding_bge_model_version),
                ("index_version", index_version),
            ):
                query = query.is_(column, "null") if value is None else query.eq(column, value)

            result = query.limit(1).execute()
            if result.data:
                return result.data[0]
            return None

        for document in _FALLBACK.documents:
            if document.get("team_id") != workspace_id:
                continue
            if document.get("file_sha256") != file_sha256:
                continue
            if document.get("chunking_config") != chunking_config:
                continue
            if document.get("embedding_model_version") != embedding_model_version:
                continue
            if document.get("embedding_bge_model_version") != embedding_bge_model_version:
                continue
            if document.get("index_version") != index_version:
                continue
            return document
        return None

    def upload_document_file(self, storage_path: str, payload: bytes, content_type: str) -> None:
        if not self._client:
            return

        self._client.storage.from_("knowledge-files").upload(
            path=storage_path,
            file=payload,
            file_options={"content-type": content_type, "upsert": "false"},
        )

    def create_document_download_url(self, user_id: str, document_id: str, expires_in_seconds: int = 300) -> str:
        workspace_id = self._ensure_workspace(user_id)
        if self._client:
            result = (
                self._client.table("documents")
                .select("id, team_id, storage_path")
                .eq("id", document_id)
                .eq("team_id", workspace_id)
                .limit(1)
                .execute()
            )
            if not result.data:
                raise PermissionError("Document is not accessible for this user")

            storage_path = result.data[0].get("storage_path")
            if not storage_path:
                raise ValueError("Document does not have a stored file")

            response = self._client.storage.from_("knowledge-files").create_signed_url(
                storage_path,
                expires_in_seconds,
            )
            signed_url = _extract_signed_url(response)
            if not signed_url:
                raise RuntimeError("Failed to create signed document URL")
            return signed_url

        for document in _FALLBACK.documents:
            if document.get("id") != document_id:
                continue
            if document.get("team_id") != workspace_id:
                raise PermissionError("Document is not accessible for this user")
            storage_path = document.get("storage_path")
            if not storage_path:
                raise ValueError("Document does not have a stored file")
            return f"http://localhost/storage/v1/object/sign/knowledge-files/{storage_path}"

        raise PermissionError("Document is not accessible for this user")

    def insert_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> None:
        rows = []
        for chunk in chunks:
            row: dict[str, Any] = {
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": chunk["embedding"],
                "metadata": chunk.get("metadata", {}),
            }
            if "embedding_bge" in chunk:
                row["embedding_bge"] = chunk["embedding_bge"]
            rows.append(row)

        if self._client:
            self._client.table("chunks").insert(rows).execute()
            return

        for row in rows:
            _FALLBACK.chunks.append({"id": str(uuid4()), **row, "created_at": datetime.now(timezone.utc).isoformat()})

    def list_documents(self, user_id: str) -> list[dict[str, Any]]:
        workspace_id = self._ensure_workspace(user_id)
        if self._client:
            result = self._client.table("documents").select("*").eq("team_id", workspace_id).order("uploaded_at", desc=True).execute()
            return result.data or []

        docs = [doc for doc in _FALLBACK.documents if doc["team_id"] == workspace_id]
        return sorted(docs, key=lambda item: item["uploaded_at"], reverse=True)

    def search_chunks(self, user_id: str, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        workspace_id = self._ensure_workspace(user_id)
        if self._client:
            result = self._client.rpc(
                "match_chunks",
                {
                    "query_embedding": query_embedding,
                    "filter_team_id": workspace_id,
                    "match_count": top_k,
                },
            ).execute()
            return result.data or []

        document_map = {document["id"]: document for document in _FALLBACK.documents if document["team_id"] == workspace_id}
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

    def hybrid_search_chunks(
        self,
        user_id: str,
        query_embedding: list[float],
        query_embedding_bge: list[float],
        query_text: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        workspace_id = self._ensure_workspace(user_id)
        if self._client:
            result = self._client.rpc(
                "hybrid_match_chunks",
                {
                    "query_embedding": query_embedding,
                    "query_embedding_bge": query_embedding_bge,
                    "query_text": query_text,
                    "filter_team_id": workspace_id,
                    "match_count": top_k,
                },
            ).execute()
            return result.data or []

        # In-memory fallback (tests/dev): delegate to cosine-only search
        return self.search_chunks(user_id=user_id, query_embedding=query_embedding, top_k=top_k)

    def save_query(
        self,
        user_id: str,
        session_id: str,
        query_text: str,
        final_answer: str,
        scorecard: dict[str, Any] | None,
        response_time_ms: int,
    ) -> dict[str, Any]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        scorecard = scorecard or {}

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
        all_rows = self.list_queries(user_id=user_id, session_id=session_id, limit=500)

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        per_day: dict[str, int] = {}
        for day_offset in range(days - 1, -1, -1):
            day = now.date() - timedelta(days=day_offset)
            per_day[day.isoformat()] = 0

        rows = []
        for row in all_rows:
            created_at = row.get("created_at")
            if not created_at:
                continue
            try:
                ts = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts < cutoff:
                continue
            rows.append(row)
            day_key = ts.date().isoformat()
            if day_key in per_day:
                per_day[day_key] += 1

        total_queries = len(rows)
        avg_response_ms = int(sum(int(row.get("response_time_ms", 0)) for row in rows) / total_queries) if total_queries else 0
        avg_overall_score = (
            round(sum(float(row.get("overall_score", 0.0) or 0.0) for row in rows) / total_queries, 2) if total_queries else 0.0
        )

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


def _extract_signed_url(response: Any) -> str | None:
    if isinstance(response, dict):
        for key in ("signedURL", "signedUrl", "signed_url"):
            value = response.get(key)
            if value:
                return str(value)
        data = response.get("data")
        if isinstance(data, dict):
            return _extract_signed_url(data)

    for key in ("signedURL", "signedUrl", "signed_url"):
        value = getattr(response, key, None)
        if value:
            return str(value)

    data = getattr(response, "data", None)
    if data is not None:
        return _extract_signed_url(data)
    return None
