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
