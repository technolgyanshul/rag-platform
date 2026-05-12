from fastapi.testclient import TestClient

from db.supabase import SupabaseRepository
from main import app


client = TestClient(app)


def test_ingest_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/ingest",
        files={"file": ("notes.md", b"hello", "text/markdown")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_ingest_rejects_empty_payload() -> None:
    response = client.post(
        "/ingest",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


def test_ingest_openapi_documents_error_responses() -> None:
    schema = client.get("/openapi.json").json()

    assert {"400", "403", "500", "503"}.issubset(schema["paths"]["/ingest"]["post"]["responses"])
    assert {"403", "503"}.issubset(schema["paths"]["/ingest/documents"]["get"]["responses"])


def test_query_history_requires_non_empty_session_id() -> None:
    response = client.get("/query/history", params={"session_id": "", "limit": 10})

    assert response.status_code == 422


def test_query_rejects_session_from_other_user() -> None:
    repository = SupabaseRepository()
    session_id = "30000000-0000-0000-0000-000000000003"
    repository.create_session(user_id="99999999-0000-0000-0000-000000000999", session_id=session_id)

    response = client.post(
        "/query",
        json={"query": "mismatch", "session_id": session_id, "top_k": 1},
    )

    assert response.status_code == 403
    assert "Session is not accessible" in response.json()["detail"]
