from __future__ import annotations

from typing import Any

import httpx
import pytest

import routers.query as query_router
from db.supabase import SupabaseRepository
from main import app
from tests.integration.test_query_orchestration_modes import USER_ID, _fake_retrieval, _team_with_agents


pytestmark = pytest.mark.anyio


class FailingLLMRouter:
    def chat(
        self,
        provider: str,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        raise RuntimeError("provider outage")


@pytest.mark.parametrize("rule", ["sequential", "debate", "hierarchical"])
async def test_query_model_failure_persists_failed_trace(rule: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_retrieval(monkeypatch)
    monkeypatch.setattr(query_router, "LLMRouter", lambda: FailingLLMRouter(), raising=False)
    repository, team_id = _team_with_agents(rule)
    session_id = {
        "sequential": "45454545-4545-4545-4545-454545454545",
        "debate": "56565656-5656-5656-5656-565656565656",
        "hierarchical": "67676767-6767-6767-6767-676767676767",
    }[rule]
    repository.create_session(user_id=USER_ID, session_id=session_id, team_id=team_id, title=f"{rule} failure session")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/query",
            json={"query": "What fails?", "session_id": session_id, "top_k": 1},
        )

    assert response.status_code == 503
    assert "provider" in response.json()["detail"].lower()
    queries = repository.list_queries(user_id=USER_ID, session_id=session_id, limit=1)
    assert queries
    traces = repository.list_agent_traces(user_id=USER_ID, session_id=session_id, query_id=queries[0]["id"])
    assert any(trace["status"] == "failed" for trace in traces)
