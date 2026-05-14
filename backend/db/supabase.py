from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

SESSION_ACCESS_ERROR_MESSAGE = "Session is not accessible for this user"
DOCUMENT_ACCESS_ERROR_MESSAGE = "Document is not accessible for this user"
TEAM_ACCESS_ERROR_MESSAGE = "Team is not accessible for this user"
AGENT_ACCESS_ERROR_MESSAGE = "Agent is not accessible for this team"

DEFAULT_TEAM_AGENTS: tuple[dict[str, Any], ...] = (
    {
        "name": "Researcher",
        "role": "researcher",
        "system_prompt": "Find the strongest evidence in the retrieved sources.",
        "model_provider": "lmstudio",
        "model_name": "local-model",
        "response_style": "evidence-first",
        "execution_order": 0,
    },
    {
        "name": "Critic",
        "role": "critic",
        "system_prompt": "Challenge weak claims and identify unsupported statements.",
        "model_provider": "lmstudio",
        "model_name": "local-model",
        "response_style": "skeptical",
        "execution_order": 1,
    },
    {
        "name": "Synthesizer",
        "role": "synthesizer",
        "system_prompt": "Synthesize evidence and produce a concise final answer.",
        "model_provider": "lmstudio",
        "model_name": "local-model",
        "response_style": "balanced",
        "execution_order": 2,
    },
)


def default_team_agents() -> list[dict[str, Any]]:
    return list(DEFAULT_TEAM_AGENTS)


class DocumentStorageError(RuntimeError):
    pass


@dataclass
class _FallbackStore:
    teams: list[dict[str, Any]] = field(default_factory=list)
    agents: list[dict[str, Any]] = field(default_factory=list)
    sessions: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    queries: list[dict[str, Any]] = field(default_factory=list)
    agent_traces: list[dict[str, Any]] = field(default_factory=list)
    scorecards: list[dict[str, Any]] = field(default_factory=list)


_FALLBACK = _FallbackStore()


def reset_fallback_store() -> None:
    _FALLBACK.teams.clear()
    _FALLBACK.agents.clear()
    _FALLBACK.sessions.clear()
    _FALLBACK.messages.clear()
    _FALLBACK.documents.clear()
    _FALLBACK.chunks.clear()
    _FALLBACK.queries.clear()
    _FALLBACK.agent_traces.clear()
    _FALLBACK.scorecards.clear()


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
            # Prefer any existing team for this user so previously uploaded documents remain visible.
            existing_for_user = (
                self._client.table("teams")
                .select("id")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if existing_for_user.data:
                return str(existing_for_user.data[0].get("id", workspace_id))

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
                created_workspace_id = str(result.data[0].get("id", workspace_id))
                self._seed_default_agents(user_id=user_id, team_id=created_workspace_id)
                return created_workspace_id
            raise RuntimeError("Failed to create demo workspace")

        for team in _FALLBACK.teams:
            if str(team.get("user_id", "")) == user_id:
                return str(team.get("id", workspace_id))

        self.create_team(
            user_id=user_id,
            name="Demo Workspace",
            domain=None,
            team_id=workspace_id,
            seed_default_agents=True,
        )
        return workspace_id

    def _find_fallback_team(self, team_id: str) -> dict[str, Any] | None:
        for row in _FALLBACK.teams:
            if row.get("id") == team_id:
                return row
        return None

    def _ensure_team_owned(self, user_id: str, team_id: str) -> dict[str, Any]:
        team = self.get_team(user_id=user_id, team_id=team_id)
        if team is None:
            raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
        return team

    def _seed_default_agents(self, user_id: str, team_id: str) -> None:
        if self.team_has_agents(user_id=user_id, team_id=team_id):
            return

        for template in DEFAULT_TEAM_AGENTS:
            self.create_agent(
                user_id=user_id,
                team_id=team_id,
                name=str(template["name"]),
                role=str(template["role"]),
                system_prompt=str(template["system_prompt"]),
                model_provider=str(template["model_provider"]),
                model_name=str(template["model_name"]),
                response_style=str(template["response_style"]),
                execution_order=int(template["execution_order"]),
            )

    def _find_fallback_session(self, session_id: str) -> dict[str, Any] | None:
        for row in _FALLBACK.sessions:
            if row["id"] == session_id:
                return row
        return None

    def _ensure_session_owned(self, session_id: str, user_id: str) -> None:
        session = self.get_session(user_id=user_id, session_id=session_id)
        if session is None:
            raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)

    def _find_fallback_query(self, query_id: str) -> dict[str, Any] | None:
        for row in _FALLBACK.queries:
            if row.get("id") == query_id:
                return row
        return None

    def _ensure_query_owned(self, query_id: str, user_id: str) -> dict[str, Any]:
        if self._client:
            result = self._client.table("queries").select("*").eq("id", query_id).limit(1).execute()
            if not result.data:
                raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)
            row = result.data[0]
            self._ensure_session_owned(session_id=str(row["session_id"]), user_id=user_id)
            return row

        row = self._find_fallback_query(query_id)
        if row is None:
            raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)
        self._ensure_session_owned(session_id=str(row["session_id"]), user_id=user_id)
        return row

    def get_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        if self._client:
            result = self._client.table("sessions").select("*").eq("id", session_id).limit(1).execute()
            if not result.data:
                return None
            row = result.data[0]
            if str(row.get("user_id", "")) != user_id:
                raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)
            return row

        row = self._find_fallback_session(session_id)
        if row is None:
            return None
        if str(row.get("user_id", "")) != user_id:
            raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)
        return row

    def create_session(
        self,
        user_id: str,
        title: str | None = None,
        session_id: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        workspace_id = team_id or self._ensure_workspace(user_id)
        self._ensure_team_owned(user_id=user_id, team_id=workspace_id)
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
                raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)
            return existing

        _FALLBACK.sessions.append(payload)
        return payload

    def list_teams(self, user_id: str) -> list[dict[str, Any]]:
        if self._client:
            result = self._client.table("teams").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return result.data or []

        rows = [row for row in _FALLBACK.teams if str(row.get("user_id", "")) == user_id]
        rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return rows

    def get_team(self, user_id: str, team_id: str) -> dict[str, Any] | None:
        if self._client:
            result = self._client.table("teams").select("*").eq("id", team_id).limit(1).execute()
            if not result.data:
                return None
            row = result.data[0]
            if str(row.get("user_id", "")) != user_id:
                raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
            return row

        team = self._find_fallback_team(team_id)
        if team is None:
            return None
        if str(team.get("user_id", "")) != user_id:
            raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
        return team

    def create_team(
        self,
        user_id: str,
        name: str,
        domain: str | None = None,
        collaboration_rule: str = "sequential",
        team_id: str | None = None,
        seed_default_agents: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "id": team_id or str(uuid4()),
            "user_id": user_id,
            "name": name,
            "domain": domain,
            "collaboration_rule": collaboration_rule,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("teams").insert(payload).execute()
            if not result.data:
                raise RuntimeError("Failed to create team")
            row = result.data[0]
            created_team_id = str(row.get("id", payload["id"]))
            if seed_default_agents:
                self._seed_default_agents(user_id=user_id, team_id=created_team_id)
            return row

        existing = self._find_fallback_team(payload["id"])
        if existing:
            if str(existing.get("user_id", "")) != user_id:
                raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
            return existing

        _FALLBACK.teams.append(payload)
        if seed_default_agents:
            self._seed_default_agents(user_id=user_id, team_id=payload["id"])
        return payload

    def update_team(self, user_id: str, team_id: str, **updates: Any) -> dict[str, Any]:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        payload = {key: value for key, value in updates.items() if key in {"name", "domain", "collaboration_rule"}}
        if not payload:
            existing = self.get_team(user_id=user_id, team_id=team_id)
            if existing is None:
                raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
            return existing

        if self._client:
            result = self._client.table("teams").update(payload).eq("id", team_id).execute()
            if not result.data:
                raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
            row = result.data[0]
            if str(row.get("user_id", "")) != user_id:
                raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
            return row

        existing = self._find_fallback_team(team_id)
        if existing is None:
            raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
        if str(existing.get("user_id", "")) != user_id:
            raise PermissionError(TEAM_ACCESS_ERROR_MESSAGE)
        existing.update(payload)
        return existing

    def delete_team(self, user_id: str, team_id: str) -> None:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        if self._client:
            self._client.table("teams").delete().eq("id", team_id).execute()
            return

        _FALLBACK.teams = [row for row in _FALLBACK.teams if row.get("id") != team_id]
        _FALLBACK.agents = [row for row in _FALLBACK.agents if row.get("team_id") != team_id]

        session_ids = {row.get("id") for row in _FALLBACK.sessions if row.get("team_id") == team_id}
        _FALLBACK.sessions = [row for row in _FALLBACK.sessions if row.get("team_id") != team_id]
        _FALLBACK.messages = [row for row in _FALLBACK.messages if row.get("session_id") not in session_ids]
        _FALLBACK.queries = [row for row in _FALLBACK.queries if row.get("session_id") not in session_ids]
        _FALLBACK.agent_traces = [row for row in _FALLBACK.agent_traces if row.get("session_id") not in session_ids]
        _FALLBACK.scorecards = [row for row in _FALLBACK.scorecards if row.get("session_id") not in session_ids]

        document_ids = {row.get("id") for row in _FALLBACK.documents if row.get("team_id") == team_id}
        _FALLBACK.documents = [row for row in _FALLBACK.documents if row.get("team_id") != team_id]
        _FALLBACK.chunks = [row for row in _FALLBACK.chunks if row.get("document_id") not in document_ids]

    def list_agents(self, user_id: str, team_id: str) -> list[dict[str, Any]]:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        if self._client:
            result = self._client.table("agents").select("*").eq("team_id", team_id).order("execution_order").execute()
            return result.data or []

        rows = [row for row in _FALLBACK.agents if row.get("team_id") == team_id]
        rows.sort(key=lambda item: (int(item.get("execution_order", 0)), str(item.get("created_at", ""))))
        return rows

    def get_agent(self, user_id: str, team_id: str, agent_id: str) -> dict[str, Any] | None:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        if self._client:
            result = self._client.table("agents").select("*").eq("id", agent_id).limit(1).execute()
            if not result.data:
                return None
            row = result.data[0]
            if str(row.get("team_id", "")) != team_id:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            return row

        for agent in _FALLBACK.agents:
            if agent.get("id") != agent_id:
                continue
            if agent.get("team_id") != team_id:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            return agent
        return None

    def create_agent(
        self,
        user_id: str,
        team_id: str,
        name: str,
        role: str,
        system_prompt: str,
        model_provider: str,
        model_name: str,
        response_style: str,
        execution_order: int,
        provider_base_url: str | None = None,
        provider_passcode: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        payload = {
            "id": agent_id or str(uuid4()),
            "team_id": team_id,
            "name": name,
            "role": role,
            "system_prompt": system_prompt,
            "model_provider": model_provider,
            "model_name": model_name,
            "response_style": response_style,
            "execution_order": execution_order,
            "provider_base_url": provider_base_url,
            "provider_passcode": provider_passcode,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("agents").insert(payload).execute()
            if result.data:
                return result.data[0]
            raise RuntimeError("Failed to create agent")

        for agent in _FALLBACK.agents:
            if agent.get("id") != payload["id"]:
                continue
            if agent.get("team_id") != team_id:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            return agent

        _FALLBACK.agents.append(payload)
        return payload

    def update_agent(
        self,
        user_id: str,
        team_id: str,
        agent_id: str,
        **updates: Any,
    ) -> dict[str, Any]:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        allowed_keys = {
            "name",
            "role",
            "system_prompt",
            "model_provider",
            "model_name",
            "response_style",
            "execution_order",
            "provider_base_url",
            "provider_passcode",
        }
        payload = {key: value for key, value in updates.items() if key in allowed_keys}
        if not payload:
            existing = self.get_agent(user_id=user_id, team_id=team_id, agent_id=agent_id)
            if existing is None:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            return existing

        if self._client:
            result = self._client.table("agents").update(payload).eq("id", agent_id).eq("team_id", team_id).execute()
            if not result.data:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            return result.data[0]

        for agent in _FALLBACK.agents:
            if agent.get("id") != agent_id:
                continue
            if agent.get("team_id") != team_id:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            agent.update(payload)
            return agent
        raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)

    def delete_agent(self, user_id: str, team_id: str, agent_id: str) -> None:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        if self._client:
            result = self._client.table("agents").delete().eq("id", agent_id).eq("team_id", team_id).execute()
            if not result.data:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            return

        for index, agent in enumerate(_FALLBACK.agents):
            if agent.get("id") != agent_id:
                continue
            if agent.get("team_id") != team_id:
                raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)
            del _FALLBACK.agents[index]
            return
        raise PermissionError(AGENT_ACCESS_ERROR_MESSAGE)

    def team_has_agents(self, user_id: str, team_id: str) -> bool:
        self._ensure_team_owned(user_id=user_id, team_id=team_id)
        if self._client:
            result = self._client.table("agents").select("id").eq("team_id", team_id).limit(1).execute()
            return bool(result.data)

        return any(row.get("team_id") == team_id for row in _FALLBACK.agents)

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
            raise PermissionError(DOCUMENT_ACCESS_ERROR_MESSAGE)

        for document in _FALLBACK.documents:
            if document.get("id") != document_id:
                continue
            if document.get("team_id") != workspace_id:
                raise PermissionError(DOCUMENT_ACCESS_ERROR_MESSAGE)
            document.update(payload)
            return document

        raise PermissionError(DOCUMENT_ACCESS_ERROR_MESSAGE)

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

        try:
            self._client.storage.from_("knowledge-files").upload(
                path=storage_path,
                file=payload,
                file_options={"content-type": content_type, "upsert": "false"},
            )
        except Exception as exc:
            raise DocumentStorageError("Failed to upload source file to storage") from exc

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
                raise PermissionError(DOCUMENT_ACCESS_ERROR_MESSAGE)

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
                raise PermissionError(DOCUMENT_ACCESS_ERROR_MESSAGE)
            storage_path = document.get("storage_path")
            if not storage_path:
                raise ValueError("Document does not have a stored file")
            return f"http://localhost/storage/v1/object/sign/knowledge-files/{storage_path}"

        raise PermissionError(DOCUMENT_ACCESS_ERROR_MESSAGE)

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

    def create_query(
        self,
        user_id: str,
        session_id: str,
        query_text: str,
        response_time_ms: int | None = None,
    ) -> dict[str, Any]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        payload = {
            "id": str(uuid4()),
            "session_id": session_id,
            "query_text": query_text,
            "final_answer": None,
            "overall_score": None,
            "citation_accuracy": None,
            "insight_depth": None,
            "response_time_ms": response_time_ms,
            "sources": [],
            "citations": [],
            "retrieval_metadata": {},
            "model_version": None,
            "insufficient_context": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("queries").insert(payload).execute()
            if result.data:
                return result.data[0]
            raise RuntimeError("Failed to create query")

        _FALLBACK.queries.append(payload)
        return payload

    def update_query_result(
        self,
        user_id: str,
        query_id: str,
        final_answer: str,
        scorecard: dict[str, Any] | None,
        response_time_ms: int,
        sources: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
        retrieval_metadata: dict[str, Any] | None = None,
        model_version: str | None = None,
        insufficient_context: bool | None = None,
    ) -> dict[str, Any]:
        scorecard = scorecard or {}
        payload = {
            "final_answer": final_answer,
            "overall_score": scorecard.get("overall") or scorecard.get("overall_quality"),
            "citation_accuracy": scorecard.get("citation_accuracy"),
            "insight_depth": scorecard.get("insight_depth"),
            "response_time_ms": response_time_ms,
        }
        if sources is not None:
            payload["sources"] = sources
        if citations is not None:
            payload["citations"] = citations
        if retrieval_metadata is not None:
            payload["retrieval_metadata"] = retrieval_metadata
        if model_version is not None:
            payload["model_version"] = model_version
        if insufficient_context is not None:
            payload["insufficient_context"] = insufficient_context

        if self._client:
            existing = self._ensure_query_owned(query_id=query_id, user_id=user_id)
            result = self._client.table("queries").update(payload).eq("id", query_id).execute()
            if result.data:
                return result.data[0]
            return {**existing, **payload}

        row = self._ensure_query_owned(query_id=query_id, user_id=user_id)
        row.update(payload)
        return row

    def create_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        payload = {
            "id": str(uuid4()),
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("messages").insert(payload).execute()
            if result.data:
                return result.data[0]
            raise RuntimeError("Failed to create message")

        _FALLBACK.messages.append(payload)
        return payload

    def list_messages(self, user_id: str, session_id: str) -> list[dict[str, Any]]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        if self._client:
            result = (
                self._client.table("messages")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .execute()
            )
            return result.data or []

        rows = [row for row in _FALLBACK.messages if row.get("session_id") == session_id]
        rows.sort(key=lambda item: str(item.get("created_at", "")))
        return rows

    def create_agent_trace(
        self,
        user_id: str,
        session_id: str,
        query_id: str | None,
        agent_id: str | None,
        agent_name: str,
        agent_role: str,
        model_provider: str,
        model_name: str,
        input_payload: dict[str, Any],
        output: str,
        citations: list[dict[str, Any]],
        latency_ms: int | None,
        status: str,
        error: str | None,
    ) -> dict[str, Any]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        if query_id is not None:
            query = self._ensure_query_owned(query_id=query_id, user_id=user_id)
            if str(query.get("session_id")) != session_id:
                raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)

        payload = {
            "id": str(uuid4()),
            "session_id": session_id,
            "query_id": query_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_role": agent_role,
            "model_provider": model_provider,
            "model_name": model_name,
            "input": input_payload,
            "output": output,
            "citations": citations,
            "latency_ms": latency_ms,
            "status": status,
            "error": error,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("agent_traces").insert(payload).execute()
            if result.data:
                return result.data[0]
            raise RuntimeError("Failed to create agent trace")

        _FALLBACK.agent_traces.append(payload)
        return payload

    def list_agent_traces(
        self,
        user_id: str,
        session_id: str,
        query_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        if query_id is not None:
            query = self._ensure_query_owned(query_id=query_id, user_id=user_id)
            if str(query.get("session_id")) != session_id:
                raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)

        if self._client:
            query_builder = self._client.table("agent_traces").select("*").eq("session_id", session_id)
            if query_id is not None:
                query_builder = query_builder.eq("query_id", query_id)
            result = query_builder.order("created_at", desc=False).execute()
            return result.data or []

        rows = [row for row in _FALLBACK.agent_traces if row.get("session_id") == session_id]
        if query_id is not None:
            rows = [row for row in rows if row.get("query_id") == query_id]
        rows.sort(key=lambda item: str(item.get("created_at", "")))
        return rows

    def save_scorecard(
        self,
        user_id: str,
        session_id: str,
        query_id: str | None,
        overall_quality: int | None,
        citation_accuracy: int | None,
        insight_depth: int | None,
        model_contribution_breakdown: dict[str, Any],
        notes: str | None,
    ) -> dict[str, Any]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        if query_id is not None:
            query = self._ensure_query_owned(query_id=query_id, user_id=user_id)
            if str(query.get("session_id")) != session_id:
                raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)

        payload = {
            "id": str(uuid4()),
            "session_id": session_id,
            "query_id": query_id,
            "overall_quality": overall_quality,
            "citation_accuracy": citation_accuracy,
            "insight_depth": insight_depth,
            "model_contribution_breakdown": model_contribution_breakdown,
            "notes": notes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._client:
            result = self._client.table("scorecards").insert(payload).execute()
            if result.data:
                return result.data[0]
            raise RuntimeError("Failed to save scorecard")

        _FALLBACK.scorecards.append(payload)
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

    def list_sessions(self, user_id: str, limit: int = 500) -> list[dict[str, Any]]:
        if self._client:
            sessions_result = (
                self._client.table("sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            sessions = sessions_result.data or []
            if not sessions:
                return []

            team_ids = sorted({str(row.get("team_id")) for row in sessions if row.get("team_id")})
            team_name_by_id: dict[str, str | None] = {}
            if team_ids:
                teams_result = self._client.table("teams").select("id,name").in_("id", team_ids).execute()
                team_name_by_id = {
                    str(row.get("id")): row.get("name") for row in (teams_result.data or []) if row.get("id")
                }

            session_ids = [str(row.get("id")) for row in sessions if row.get("id")]
            query_counts: dict[str, int] = {}
            query_last: dict[str, str] = {}
            if session_ids:
                queries_result = (
                    self._client.table("queries")
                    .select("session_id,created_at")
                    .in_("session_id", session_ids)
                    .order("created_at", desc=True)
                    .limit(limit * 50)
                    .execute()
                )
                for row in queries_result.data or []:
                    session_id = str(row.get("session_id", ""))
                    if not session_id:
                        continue
                    query_counts[session_id] = query_counts.get(session_id, 0) + 1
                    created_at = str(row.get("created_at", ""))
                    if created_at and session_id not in query_last:
                        query_last[session_id] = created_at

            return [
                {
                    "id": str(row.get("id", "")),
                    "team_id": str(row.get("team_id", "")),
                    "team_name": team_name_by_id.get(str(row.get("team_id", ""))),
                    "title": row.get("title"),
                    "created_at": str(row.get("created_at", "")),
                    "query_count": int(query_counts.get(str(row.get("id", "")), 0)),
                    "last_query_at": query_last.get(str(row.get("id", ""))),
                }
                for row in sessions
            ]

        sessions = [row for row in _FALLBACK.sessions if str(row.get("user_id", "")) == user_id]
        sessions.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        sessions = sessions[:limit]
        owned_session_ids = {str(item.get("id", "")) for item in sessions}
        team_name_by_id = {
            str(row.get("id")): row.get("name") for row in _FALLBACK.teams if str(row.get("user_id", "")) == user_id
        }

        query_counts: dict[str, int] = {}
        query_last: dict[str, str] = {}
        for row in _FALLBACK.queries:
            session_id = str(row.get("session_id", ""))
            if session_id not in owned_session_ids:
                continue
            query_counts[session_id] = query_counts.get(session_id, 0) + 1
            created_at = str(row.get("created_at", ""))
            if created_at and (session_id not in query_last or created_at > query_last[session_id]):
                query_last[session_id] = created_at

        return [
            {
                "id": str(row.get("id", "")),
                "team_id": str(row.get("team_id", "")),
                "team_name": team_name_by_id.get(str(row.get("team_id", ""))),
                "title": row.get("title"),
                "created_at": str(row.get("created_at", "")),
                "query_count": int(query_counts.get(str(row.get("id", "")), 0)),
                "last_query_at": query_last.get(str(row.get("id", ""))),
            }
            for row in sessions
        ]

    def list_scorecards(
        self,
        user_id: str,
        session_id: str,
        query_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self._ensure_session_owned(session_id=session_id, user_id=user_id)
        if query_id is not None:
            query = self._ensure_query_owned(query_id=query_id, user_id=user_id)
            if str(query.get("session_id")) != session_id:
                raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)

        if self._client:
            query_builder = self._client.table("scorecards").select("*").eq("session_id", session_id)
            if query_id is not None:
                query_builder = query_builder.eq("query_id", query_id)
            result = query_builder.order("created_at", desc=False).execute()
            return result.data or []

        rows = [row for row in _FALLBACK.scorecards if row.get("session_id") == session_id]
        if query_id is not None:
            rows = [row for row in rows if row.get("query_id") == query_id]
        rows.sort(key=lambda item: str(item.get("created_at", "")))
        return rows

    def get_session_detail(self, user_id: str, session_id: str) -> dict[str, Any]:
        session = self.get_session(user_id=user_id, session_id=session_id)
        if session is None:
            raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)

        team_id = str(session.get("team_id", ""))
        team_name: str | None = None
        if team_id:
            team = self.get_team(user_id=user_id, team_id=team_id)
            team_name = team.get("name") if team else None

        messages = self.list_messages(user_id=user_id, session_id=session_id)
        scorecards = self.list_scorecards(user_id=user_id, session_id=session_id)
        traces = self.list_agent_traces(user_id=user_id, session_id=session_id)
        scorecard_by_query_id = {
            str(row.get("query_id")): row for row in scorecards if row.get("query_id") is not None
        }
        traces_by_query_id: dict[str, list[dict[str, Any]]] = {}
        for row in traces:
            query_id = row.get("query_id")
            if query_id is None:
                continue
            key = str(query_id)
            traces_by_query_id.setdefault(key, []).append(row)

        queries = self.list_queries(user_id=user_id, session_id=session_id, limit=500)
        queries.sort(key=lambda item: str(item.get("created_at", "")))
        normalized_queries: list[dict[str, Any]] = []
        for query in queries:
            query_id = str(query.get("id", ""))
            normalized_query = dict(query)
            normalized_query.setdefault("sources", [])
            normalized_query.setdefault("citations", [])
            normalized_query.setdefault("retrieval_metadata", {})
            normalized_query.setdefault("model_version", None)
            normalized_query.setdefault("insufficient_context", False)
            normalized_query["scorecard"] = scorecard_by_query_id.get(query_id)
            normalized_query["agent_traces"] = traces_by_query_id.get(query_id, [])
            normalized_queries.append(normalized_query)

        return {
            "session": {
                "id": str(session.get("id", "")),
                "team_id": team_id,
                "team_name": team_name,
                "title": session.get("title"),
                "created_at": str(session.get("created_at", "")),
            },
            "messages": messages,
            "queries": normalized_queries,
        }

    def list_recent_queries(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if self._client:
            sessions = (
                self._client.table("sessions")
                .select("id")
                .eq("user_id", user_id)
                .limit(500)
                .execute()
            )
            session_ids = [str(row.get("id")) for row in (sessions.data or []) if row.get("id")]
            if not session_ids:
                return []

            result = (
                self._client.table("queries")
                .select("*")
                .in_("session_id", session_ids)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []

        owned_session_ids = {row.get("id") for row in _FALLBACK.sessions if row.get("user_id") == user_id}
        rows = [row for row in _FALLBACK.queries if row.get("session_id") in owned_session_ids]
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
    if math.isclose(norm_a, 0.0) or math.isclose(norm_b, 0.0):
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
