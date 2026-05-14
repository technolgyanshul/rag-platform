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
    assert scorecard["citation_accuracy"] == 7
    assert scorecard["insight_depth"] == 7
    assert scorecard["model_contribution_breakdown"] == {"Researcher": "completed"}
    assert scorecard["notes"] == "MVP deterministic scorecard."


def test_create_query_initializes_history_artifacts() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session = repository.create_session(user_id=user_id, session_id="23232323-2323-2323-2323-232323232323")

    query = repository.create_query(
        user_id=user_id,
        session_id=str(session["id"]),
        query_text="What should be persisted?",
    )

    assert query["sources"] == []
    assert query["citations"] == []
    assert query["retrieval_metadata"] == {}
    assert query["model_version"] is None
    assert query["insufficient_context"] is False


def test_update_query_result_persists_history_artifacts() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session = repository.create_session(user_id=user_id, session_id="24242424-2424-2424-2424-242424242424")
    query = repository.create_query(user_id=user_id, session_id=str(session["id"]), query_text="Persist all artifacts")

    updated = repository.update_query_result(
        user_id=user_id,
        query_id=str(query["id"]),
        final_answer="Persisted answer.",
        scorecard={"overall_quality": 8, "citation_accuracy": 9, "insight_depth": 7},
        response_time_ms=187,
        sources=[{"document_id": "doc-1", "filename": "policy.txt", "chunk_index": 0, "content_preview": "..."},],
        citations=[{"document_id": "doc-1", "filename": "policy.txt", "chunk_index": 0, "source_index": 1},],
        retrieval_metadata={"embedding_model_version": "embed-v1", "index_version": "idx-v1", "top_k": 3},
        model_version="llm-v1",
        insufficient_context=False,
    )

    assert updated["sources"][0]["document_id"] == "doc-1"
    assert updated["citations"][0]["source_index"] == 1
    assert updated["retrieval_metadata"]["top_k"] == 3
    assert updated["model_version"] == "llm-v1"
    assert updated["insufficient_context"] is False


def test_create_and_list_messages_for_session() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session = repository.create_session(user_id=user_id, session_id="25252525-2525-2525-2525-252525252525")

    user_message = repository.create_message(
        user_id=user_id,
        session_id=str(session["id"]),
        role="user",
        content="What changed?",
        metadata={"query_id": "query-1"},
    )
    assistant_message = repository.create_message(
        user_id=user_id,
        session_id=str(session["id"]),
        role="assistant",
        content="Policy A changed in section 2.",
        metadata={"query_id": "query-1"},
    )
    messages = repository.list_messages(user_id=user_id, session_id=str(session["id"]))

    assert [message["id"] for message in messages] == [user_message["id"], assistant_message["id"]]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["metadata"]["query_id"] == "query-1"


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
