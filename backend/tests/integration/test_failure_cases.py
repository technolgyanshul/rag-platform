from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_ingest_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/ingest",
        data={"team_id": "phase8-team"},
        files={"file": ("notes.md", b"hello", "text/markdown")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_ingest_rejects_empty_payload() -> None:
    response = client.post(
        "/ingest",
        data={"team_id": "phase8-team"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


def test_query_history_requires_non_empty_session_id() -> None:
    response = client.get("/query/history", params={"session_id": "", "limit": 10})

    assert response.status_code == 422
