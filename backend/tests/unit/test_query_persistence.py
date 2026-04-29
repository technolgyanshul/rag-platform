from db.supabase import SupabaseRepository


def test_save_query_and_trace_in_memory() -> None:
    repository = SupabaseRepository()
    query_row = repository.save_query(
        session_id="session-1",
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
