from fastapi.testclient import TestClient

from db.supabase import SupabaseRepository
from main import app


client = TestClient(app)


def test_create_session_returns_row() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    team_id = "91000000-0000-0000-0000-000000000001"
    repository.create_team(user_id=user_id, team_id=team_id, name="Team Sessions")

    response = client.post("/sessions", json={"team_id": team_id, "title": "Integration Session"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["team_id"] == team_id
    assert payload["title"] == "Integration Session"
