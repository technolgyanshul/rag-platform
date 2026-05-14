import httpx
import pytest

from db.supabase import SupabaseRepository
from main import app
import routers.query as query_router


pytestmark = pytest.mark.anyio


async def test_query_requires_team_id() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/query",
            json={
                "query": "Any question",
                "session_id": "56565656-5656-5656-5656-565656565656",
                "top_k": 1,
            },
        )

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "team_id"] for error in response.json()["detail"])


async def test_query_rejects_session_team_mismatch() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session_team = repository.create_team(user_id=user_id, name="Session Team", domain=None)
    requested_team = repository.create_team(user_id=user_id, name="Requested Team", domain=None)
    session_id = "67676767-6767-6767-6767-676767676767"
    repository.create_session(
        user_id=user_id,
        session_id=session_id,
        team_id=str(session_team["id"]),
        title="Mismatch session",
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/query",
            json={
                "query": "Any question",
                "session_id": session_id,
                "team_id": str(requested_team["id"]),
                "top_k": 1,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Session belongs to a different team than the requested team"


@pytest.mark.parametrize("rule", ["sequential", "debate", "hierarchical"])
async def test_query_requires_at_least_one_agent_for_team(rule: str) -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    team = repository.create_team(
        user_id=user_id,
        name="No Agent Team",
        domain=None,
        collaboration_rule=rule,
        seed_default_agents=False,
    )
    session_id = "12121212-1212-1212-1212-121212121212"
    repository.create_session(
        user_id=user_id,
        session_id=session_id,
        team_id=str(team["id"]),
        title="Guarded session",
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Any question", "session_id": session_id, "team_id": str(team["id"]), "top_k": 1},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Team must have at least one agent before chat"


@pytest.mark.parametrize("rule", ["debate", "hierarchical"])
async def test_query_rule_guardrails_require_two_agents(rule: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        query_router,
        "retrieve_chunks",
        lambda query, user_id, top_k: [
            {
                "document_id": "doc-1",
                "filename": "policy.txt",
                "chunk_index": 0,
                "content": "Policy source text.",
                "similarity": 0.91,
            }
        ],
    )
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    team = repository.create_team(
        user_id=user_id,
        name=f"{rule} one-agent team",
        domain=None,
        collaboration_rule=rule,
        seed_default_agents=False,
    )
    team_id = str(team["id"])
    repository.create_agent(
        user_id=user_id,
        team_id=team_id,
        name="Solo",
        role="researcher",
        system_prompt="Act as researcher",
        model_provider="groq",
        model_name="llama-3.1-8b-instant",
        response_style="concise",
        execution_order=0,
    )
    session_id = {
        "debate": "78787878-7878-7878-7878-787878787878",
        "hierarchical": "89898989-8989-8989-8989-898989898989",
    }[rule]
    repository.create_session(user_id=user_id, session_id=session_id, team_id=team_id, title="Guarded session")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Any question", "session_id": session_id, "team_id": team_id, "top_k": 1},
        )

    assert response.status_code == 400
    assert f"{rule} requires at least two agents" in response.json()["detail"]
