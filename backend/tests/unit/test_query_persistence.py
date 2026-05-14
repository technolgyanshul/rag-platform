import ast
import inspect

from db.supabase import SupabaseRepository, _cosine_similarity


def test_save_query_in_memory() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session_id = "11111111-2222-3333-4444-555555555555"
    repository.create_session(user_id=user_id, session_id=session_id)
    query_row = repository.save_query(
        user_id=user_id,
        session_id=session_id,
        query_text="What is the summary?",
        final_answer="Answer text",
        scorecard=None,
        response_time_ms=1200,
    )

    assert query_row["id"]
    assert query_row["overall_score"] is None


def test_create_and_update_query_in_memory() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session = repository.create_session(user_id=user_id, session_id="12121212-1212-1212-1212-121212121212")

    query = repository.create_query(
        user_id=user_id,
        session_id=str(session["id"]),
        query_text="What changed?",
        response_time_ms=None,
    )

    assert query["final_answer"] is None

    updated = repository.update_query_result(
        user_id=user_id,
        query_id=str(query["id"]),
        final_answer="Final answer",
        scorecard={"overall": 7, "citation_accuracy": 7, "insight_depth": 7},
        response_time_ms=123,
    )

    assert updated["final_answer"] == "Final answer"
    assert updated["overall_score"] == 7


def test_agent_traces_and_scorecard_in_memory() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session = repository.create_session(user_id=user_id, session_id="12121212-1212-1212-1212-121212121212")
    query = repository.create_query(user_id=user_id, session_id=str(session["id"]), query_text="Question")

    trace = repository.create_agent_trace(
        user_id=user_id,
        session_id=str(session["id"]),
        query_id=str(query["id"]),
        agent_id=None,
        agent_name="Researcher",
        agent_role="researcher",
        model_provider="groq",
        model_name="llama-3.1-8b-instant",
        input_payload={"query": "Question"},
        output="Answer",
        citations=[],
        latency_ms=10,
        status="completed",
        error=None,
    )
    scorecard = repository.save_scorecard(
        user_id=user_id,
        session_id=str(session["id"]),
        query_id=str(query["id"]),
        overall_quality=7,
        citation_accuracy=7,
        insight_depth=7,
        model_contribution_breakdown={"Researcher": "completed"},
        notes="MVP deterministic scorecard.",
    )

    assert trace["status"] == "completed"
    assert repository.list_agent_traces(user_id=user_id, session_id=str(session["id"]), query_id=str(query["id"])) == [trace]
    assert scorecard["overall_quality"] == 7


def test_cosine_similarity_avoids_float_equality_checks() -> None:
    tree = ast.parse(inspect.getsource(_cosine_similarity))

    float_equality_checks = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and any(isinstance(operator, ast.Eq | ast.NotEq) for operator in node.ops)
        and any(
            isinstance(value, ast.Constant) and isinstance(value.value, float)
            for value in [node.left, *node.comparators]
        )
    ]

    assert float_equality_checks == []
