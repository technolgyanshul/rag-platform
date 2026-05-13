import httpx
import pytest

from db.supabase import SupabaseRepository
from main import app


pytestmark = pytest.mark.anyio


async def test_query_requires_at_least_one_agent_for_team() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    team = repository.create_team(
        user_id=user_id,
        name="No Agent Team",
        domain=None,
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
            json={"query": "Any question", "session_id": session_id, "top_k": 1},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Team must have at least one agent before chat"
