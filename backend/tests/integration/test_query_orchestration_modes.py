from __future__ import annotations

from typing import Any

import httpx
import pytest

import routers.query as query_router
from db.supabase import SupabaseRepository
from main import app


pytestmark = pytest.mark.anyio

USER_ID = "00000000-0000-0000-0000-000000000001"


class FakeLLMRouter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        provider: str,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        metadata = metadata or {}
        self.calls.append(
            {
                "provider": provider,
                "model_name": model_name,
                "agent_name": metadata.get("agent_name"),
            }
        )
        return f"{metadata.get('agent_name', 'Agent')} output"


def _fake_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        query_router,
        "retrieve_chunks",
        lambda query, user_id, top_k: [
            {
                "document_id": "doc-1",
                "filename": "policy.txt",
                "chunk_index": 0,
                "content": "Policy source text for orchestration.",
                "similarity": 0.91,
            }
        ],
    )


def _team_with_agents(rule: str) -> tuple[SupabaseRepository, str]:
    repository = SupabaseRepository()
    team = repository.create_team(
        user_id=USER_ID,
        name=f"{rule.title()} Team",
        domain="Policy",
        collaboration_rule=rule,
        seed_default_agents=False,
    )
    team_id = str(team["id"])
    for order, (name, role) in enumerate(
        [
            ("Researcher", "researcher"),
            ("Critic", "critic"),
            ("Synthesizer", "synthesizer"),
        ]
    ):
        repository.create_agent(
            user_id=USER_ID,
            team_id=team_id,
            name=name,
            role=role,
            system_prompt=f"Act as {role}",
            model_provider="groq",
            model_name="llama-3.1-8b-instant",
            response_style="concise",
            execution_order=order,
        )
    return repository, team_id


@pytest.mark.parametrize("rule", ["sequential", "debate", "hierarchical"])
async def test_query_runs_rule_aware_orchestration_and_returns_traces(rule: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_retrieval(monkeypatch)
    fake_llm = FakeLLMRouter()
    monkeypatch.setattr(query_router, "LLMRouter", lambda: fake_llm, raising=False)

    repository, team_id = _team_with_agents(rule)
    session_id = {
        "sequential": "12121212-1212-1212-1212-121212121212",
        "debate": "23232323-2323-2323-2323-232323232323",
        "hierarchical": "34343434-3434-3434-3434-343434343434",
    }[rule]
    repository.create_session(user_id=USER_ID, session_id=session_id, team_id=team_id, title=f"{rule} session")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/query",
            json={"query": "What does the policy say?", "session_id": session_id, "top_k": 1},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_id"]
    assert payload["final_answer"].endswith("output")
    assert payload["sources"][0]["document_id"] == "doc-1"
    assert payload["citations"] == [{"document_id": "doc-1", "filename": "policy.txt", "chunk_index": 0, "source_index": 1}]
    assert payload["scorecard"]["overall_quality"] == 7
    assert payload["traces"]
    assert all(trace["model_provider"] == "groq" for trace in payload["traces"])
    assert all(trace["model_name"] == "llama-3.1-8b-instant" for trace in payload["traces"])

    persisted = repository.list_agent_traces(user_id=USER_ID, session_id=session_id, query_id=payload["query_id"])
    assert len(persisted) == len(payload["traces"])
    assert [call["model_name"] for call in fake_llm.calls] == ["llama-3.1-8b-instant"] * len(fake_llm.calls)
