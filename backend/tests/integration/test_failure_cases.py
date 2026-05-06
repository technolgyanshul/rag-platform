from fastapi.testclient import TestClient

from db.supabase import SupabaseRepository
from main import app


client = TestClient(app)


def test_ingest_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/ingest",
        data={"team_id": "99999999-9999-9999-9999-999999999999"},
        files={"file": ("notes.md", b"hello", "text/markdown")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_ingest_rejects_empty_payload() -> None:
    repository = SupabaseRepository()
    repository.create_team(
        user_id="00000000-0000-0000-0000-000000000001",
        team_id="99999999-9999-9999-9999-999999999999",
        name="Team Ingest",
    )
    response = client.post(
        "/ingest",
        data={"team_id": "99999999-9999-9999-9999-999999999999"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


def test_query_history_requires_non_empty_session_id() -> None:
    response = client.get("/query/history", params={"session_id": "", "limit": 10})

    assert response.status_code == 422


def test_query_rejects_session_team_mismatch() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    team_a = "10000000-0000-0000-0000-000000000001"
    team_b = "20000000-0000-0000-0000-000000000002"
    session_id = "30000000-0000-0000-0000-000000000003"

    repository.create_team(user_id=user_id, team_id=team_a, name="Team A")
    repository.create_team(user_id=user_id, team_id=team_b, name="Team B")
    repository.create_session(user_id=user_id, team_id=team_a, session_id=session_id)

    response = client.post(
        "/query",
        json={"query": "mismatch", "team_id": team_b, "session_id": session_id, "top_k": 1},
    )

    assert response.status_code == 403
    assert "Session does not belong" in response.json()["detail"]
