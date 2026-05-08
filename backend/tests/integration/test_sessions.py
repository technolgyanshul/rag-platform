from fastapi.testclient import TestClient

from db.supabase import SupabaseRepository
from main import app


client = TestClient(app)


def test_create_session_returns_row() -> None:
    response = client.post("/sessions", json={"title": "Integration Session"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["title"] == "Integration Session"
