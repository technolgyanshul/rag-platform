import httpx
import pytest

from db.supabase import SupabaseRepository
from main import app


pytestmark = pytest.mark.anyio


async def test_create_session_returns_row() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post("/sessions", json={"title": "Integration Session"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["title"] == "Integration Session"


async def test_create_session_accepts_and_returns_team_id() -> None:
    repository = SupabaseRepository()
    team = repository.create_team(
        user_id="00000000-0000-0000-0000-000000000001",
        name="Selected Team",
        domain=None,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.post(
            "/sessions",
            json={"title": "Team Session", "team_id": str(team["id"])},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["title"] == "Team Session"
    assert payload["team_id"] == str(team["id"])
