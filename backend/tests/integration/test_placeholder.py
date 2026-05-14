import httpx
import pytest

import routers.query as query_router
from db.supabase import SupabaseRepository
from main import app


pytestmark = pytest.mark.anyio


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test")


class FakeLLMRouter:
    def chat(self, provider, model_name, messages, metadata=None):
        return "Answer from source."


def _team_id() -> str:
    repository = SupabaseRepository()
    team = repository.create_team(
        user_id="00000000-0000-0000-0000-000000000001",
        name="Query Test Team",
        domain=None,
    )
    return str(team["id"])


async def test_query_returns_top_k_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        query_router,
        "retrieve_chunks",
        lambda query, user_id, top_k: [
            {
                "document_id": "doc-1",
                "filename": "report.txt",
                "chunk_index": 0,
                "content": "alpha finding",
                "metadata": {},
                "similarity": 0.9,
            }
        ],
    )
    monkeypatch.setattr(query_router, "LLMRouter", lambda: FakeLLMRouter())

    async with _client() as client:
        response = await client.post(
            "/query",
            json={
                "query": "alpha",
                "session_id": "66666666-6666-6666-6666-666666666666",
                "team_id": _team_id(),
                "top_k": 1,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_id"]
    assert payload["final_answer"] == "Answer from source."
    assert payload["insufficient_context"] is False
    assert payload["retrieval_count"] == 1
    assert payload["sources"][0]["filename"] == "report.txt"
    assert "chunk_index" in payload["sources"][0]
    assert payload["traces"]


async def test_query_returns_insufficient_context_when_no_hits(monkeypatch) -> None:
    monkeypatch.setattr(query_router, "retrieve_chunks", lambda query, user_id, top_k: [])

    async with _client() as client:
        response = await client.post(
            "/query",
            json={
                "query": "unknown",
                "session_id": "88888888-8888-8888-8888-888888888888",
                "team_id": _team_id(),
                "top_k": 3,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_id"]
    assert payload["insufficient_context"] is True
    assert payload["retrieval_count"] == 0
    assert payload["sources"] == []
