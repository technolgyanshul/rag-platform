from db.supabase import SupabaseRepository


def test_save_query_and_trace_in_memory() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session_id = "11111111-2222-3333-4444-555555555555"
    repository.create_session(user_id=user_id, session_id=session_id)
    query_row = repository.save_query(
        user_id=user_id,
        session_id=session_id,
        query_text="What is the summary?",
        final_answer="Answer text",
        scorecard={"overall": 8, "citation_accuracy": 7, "insight_depth": 8},
        response_time_ms=1200,
    )

    repository.save_agent_traces(
        query_id=query_row["id"],
        traces=[
            {
                "agent_name": "Researcher",
                "model_name": "model-x",
                "output": "draft",
                "response_time_ms": 400,
            }
        ],
    )

    assert query_row["id"]
    assert query_row["overall_score"] == 8
