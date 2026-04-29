from fastapi.testclient import TestClient

from db.supabase import SupabaseRepository
from main import app


client = TestClient(app)


def test_query_history_returns_saved_rows() -> None:
    repository = SupabaseRepository()
    row = repository.save_query(
        session_id="history-session",
        query_text="What changed in policy A?",
        final_answer="Policy A changed in section 3.",
        scorecard={"overall": 8.2, "citation_accuracy": 8.8, "insight_depth": 7.9},
        response_time_ms=420,
    )

    response = client.get("/query/history", params={"session_id": "history-session", "limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert any(item["id"] == row["id"] for item in payload)


def test_dashboard_metrics_returns_aggregates() -> None:
    repository = SupabaseRepository()
    repository.save_query(
        session_id="dashboard-session",
        query_text="Q1",
        final_answer="A1",
        scorecard={"overall": 7.0, "citation_accuracy": 7.0, "insight_depth": 7.0},
        response_time_ms=300,
    )
    repository.save_query(
        session_id="dashboard-session",
        query_text="Q2",
        final_answer="A2",
        scorecard={"overall": 9.0, "citation_accuracy": 9.0, "insight_depth": 9.0},
        response_time_ms=500,
    )

    response = client.get("/dashboard/metrics", params={"session_id": "dashboard-session", "days": 7})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_queries"] >= 2
    assert payload["average_response_time_ms"] >= 400
    assert payload["average_overall_score"] >= 8.0
    assert len(payload["queries_over_time"]) == 7
