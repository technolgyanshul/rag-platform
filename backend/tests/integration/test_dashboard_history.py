import httpx
import pytest

from db.supabase import SupabaseRepository
from main import app


pytestmark = pytest.mark.anyio


async def test_query_history_returns_saved_rows() -> None:
    repository = SupabaseRepository()
    session_id = "33333333-3333-3333-3333-333333333333"
    repository.create_session(user_id="00000000-0000-0000-0000-000000000001", session_id=session_id)
    row = repository.save_query(
        user_id="00000000-0000-0000-0000-000000000001",
        session_id=session_id,
        query_text="What changed in policy A?",
        final_answer="Policy A changed in section 3.",
        scorecard={"overall": 8.2, "citation_accuracy": 8.8, "insight_depth": 7.9},
        response_time_ms=420,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/query/history", params={"session_id": session_id, "limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert any(item["id"] == row["id"] for item in payload)


async def test_recent_query_history_returns_rows_without_session_id_filter() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    session_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    repository.create_session(user_id=user_id, session_id=session_a)
    repository.create_session(user_id=user_id, session_id=session_b)

    row_a = repository.save_query(
        user_id=user_id,
        session_id=session_a,
        query_text="Question A",
        final_answer="Answer A",
        scorecard=None,
        response_time_ms=100,
    )
    row_b = repository.save_query(
        user_id=user_id,
        session_id=session_b,
        query_text="Question B",
        final_answer="Answer B",
        scorecard=None,
        response_time_ms=120,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/query/history/recent", params={"limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == row_a["id"] for item in payload)
    assert any(item["id"] == row_b["id"] for item in payload)
    assert all("session_id" in item for item in payload)


async def test_dashboard_metrics_returns_aggregates() -> None:
    repository = SupabaseRepository()
    session_id = "44444444-4444-4444-4444-444444444444"
    repository.create_session(user_id="00000000-0000-0000-0000-000000000001", session_id=session_id)
    repository.save_query(
        user_id="00000000-0000-0000-0000-000000000001",
        session_id=session_id,
        query_text="Q1",
        final_answer="A1",
        scorecard={"overall": 7.0, "citation_accuracy": 7.0, "insight_depth": 7.0},
        response_time_ms=300,
    )
    repository.save_query(
        user_id="00000000-0000-0000-0000-000000000001",
        session_id=session_id,
        query_text="Q2",
        final_answer="A2",
        scorecard={"overall": 9.0, "citation_accuracy": 9.0, "insight_depth": 9.0},
        response_time_ms=500,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/dashboard/metrics", params={"session_id": session_id, "days": 7})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_queries"] >= 2
    assert payload["average_response_time_ms"] >= 400
    assert payload["average_overall_score"] >= 8.0
    assert len(payload["queries_over_time"]) == 7
