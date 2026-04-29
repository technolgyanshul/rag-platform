from fastapi.testclient import TestClient

from db.supabase import SupabaseRepository
from main import app


client = TestClient(app)


def test_query_returns_top_k_sources() -> None:
    repository = SupabaseRepository()
    team_id = "phase4-team"
    document = repository.insert_document(team_id=team_id, filename="report.txt", file_type="txt", chunk_count=2)
    repository.insert_chunks(
        document_id=document["id"],
        chunks=[
            {"chunk_index": 0, "content": "alpha finding", "embedding": [1.0, 0.0, 0.0], "metadata": {}},
            {"chunk_index": 1, "content": "beta finding", "embedding": [0.0, 1.0, 0.0], "metadata": {}},
        ],
    )

    response = client.post(
        "/query",
        json={"query": "alpha", "team_id": team_id, "session_id": "session-a", "top_k": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_id"]
    assert payload["insufficient_context"] is False
    assert payload["retrieval_count"] == 1
    assert payload["sources"][0]["filename"] == "report.txt"
    assert "chunk_index" in payload["sources"][0]
    assert payload["scorecard"] is not None
    assert {row["agent_name"] for row in payload["agent_trace"]} == {"Researcher", "Critic", "Synthesizer", "Judge"}
    assert payload["agent_trace"][0]["agent_name"] == "Researcher"
    assert payload["agent_trace"][1]["agent_name"] == "Critic"
    assert payload["agent_trace"][2]["agent_name"] == "Synthesizer"
    assert payload["agent_trace"][3]["agent_name"] == "Judge"


def test_query_returns_insufficient_context_when_no_hits() -> None:
    response = client.post(
        "/query",
        json={"query": "unknown", "team_id": "empty-team", "session_id": "session-b", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_id"] is None
    assert payload["insufficient_context"] is True
    assert payload["retrieval_count"] == 0
    assert payload["sources"] == []
    assert payload["agent_trace"] == []
