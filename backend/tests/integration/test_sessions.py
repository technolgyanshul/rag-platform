import httpx
import pytest

from core.auth import AuthUser, get_current_user
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


async def test_list_sessions_returns_owned_sessions() -> None:
    repository = SupabaseRepository()
    owner_id = "00000000-0000-0000-0000-000000000001"
    other_user_id = "99999999-9999-9999-9999-999999999999"

    owner_team = repository.create_team(user_id=owner_id, name="Owner Team", domain="Policy")
    owner_session = repository.create_session(
        user_id=owner_id,
        session_id="51515151-5151-5151-5151-515151515151",
        team_id=str(owner_team["id"]),
        title="Owner Session",
    )
    repository.save_query(
        user_id=owner_id,
        session_id=str(owner_session["id"]),
        query_text="What changed?",
        final_answer="Policy update.",
        scorecard={"overall": 8, "citation_accuracy": 7, "insight_depth": 8},
        response_time_ms=120,
    )

    other_team = repository.create_team(user_id=other_user_id, name="Other Team", domain=None)
    repository.create_session(
        user_id=other_user_id,
        session_id="61616161-6161-6161-6161-616161616161",
        team_id=str(other_team["id"]),
        title="Other Session",
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/sessions")

    assert response.status_code == 200
    payload = response.json()
    target = next(item for item in payload if item["id"] == str(owner_session["id"]))
    assert target["team_id"] == str(owner_team["id"])
    assert target["team_name"] == owner_team["name"]
    assert target["query_count"] == 1
    assert target["last_query_at"]
    assert all(item["id"] != "61616161-6161-6161-6161-616161616161" for item in payload)


async def test_session_detail_includes_queries_trace_scorecard_and_citations() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"

    team = repository.create_team(user_id=user_id, name="Detail Team", domain="Research")
    session_id = "71717171-7171-7171-7171-717171717171"
    repository.create_session(user_id=user_id, session_id=session_id, team_id=str(team["id"]), title="Detail Session")

    query = repository.create_query(
        user_id=user_id,
        session_id=session_id,
        query_text="Summarize the policy update.",
    )
    repository.update_query_result(
        user_id=user_id,
        query_id=str(query["id"]),
        final_answer="The policy update narrows eligibility.",
        scorecard={"overall_quality": 7, "citation_accuracy": 8, "insight_depth": 7},
        response_time_ms=210,
    )
    repository.create_agent_trace(
        user_id=user_id,
        session_id=session_id,
        query_id=str(query["id"]),
        agent_id=None,
        agent_name="Researcher",
        agent_role="researcher",
        model_provider="groq",
        model_name="llama-3.1-8b-instant",
        input_payload={"query": "Summarize the policy update."},
        output="Evidence collected.",
        citations=[{"document_id": "doc-1", "filename": "policy.txt", "chunk_index": 0, "source_index": 1}],
        latency_ms=44,
        status="completed",
        error=None,
    )
    repository.save_scorecard(
        user_id=user_id,
        session_id=session_id,
        query_id=str(query["id"]),
        overall_quality=7,
        citation_accuracy=8,
        insight_depth=7,
        model_contribution_breakdown={"Researcher": "completed"},
        notes="Looks good.",
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["id"] == session_id
    assert payload["session"]["team_id"] == str(team["id"])
    assert payload["session"]["team_name"] == "Detail Team"

    stored_query = next(item for item in payload["queries"] if item["id"] == str(query["id"]))
    assert stored_query["query_text"] == "Summarize the policy update."
    assert stored_query["final_answer"] == "The policy update narrows eligibility."
    assert stored_query["scorecard"]["overall_quality"] == 7
    assert stored_query["agent_traces"][0]["output"] == "Evidence collected."
    assert isinstance(stored_query["citations"], list)


async def test_session_export_returns_structured_json() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"

    team = repository.create_team(user_id=user_id, name="Export Team", domain=None)
    session_id = "81818181-8181-8181-8181-818181818181"
    session = repository.create_session(user_id=user_id, session_id=session_id, team_id=str(team["id"]), title="Export Session")

    query = repository.create_query(user_id=user_id, session_id=session_id, query_text="Export this session")
    repository.update_query_result(
        user_id=user_id,
        query_id=str(query["id"]),
        final_answer="Export-ready answer.",
        scorecard={"overall_quality": 8, "citation_accuracy": 8, "insight_depth": 8},
        response_time_ms=180,
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get(f"/sessions/{session_id}/export.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "session-export-v1"
    assert payload["session"]["id"] == str(session["id"])
    assert isinstance(payload["messages"], list)
    assert isinstance(payload["queries"], list)
    assert payload["queries"][0]["id"] == str(query["id"])
    assert response.headers["content-disposition"] == f'attachment; filename="session-{session_id}.json"'


async def test_session_export_rejects_other_users_session() -> None:
    repository = SupabaseRepository()
    owner_id = "00000000-0000-0000-0000-000000000001"
    other_id = "99999999-9999-9999-9999-999999999999"

    team = repository.create_team(user_id=owner_id, name="Owner Export Team", domain=None)
    session_id = "91919191-9191-9191-9191-919191919191"
    repository.create_session(user_id=owner_id, session_id=session_id, team_id=str(team["id"]), title="Private Session")

    def _other_user() -> AuthUser:
        return AuthUser(user_id=other_id, email="other@example.com")

    app.dependency_overrides[get_current_user] = _other_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            response = await client.get(f"/sessions/{session_id}/export.json")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
