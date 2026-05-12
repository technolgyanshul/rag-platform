from db.supabase import SupabaseRepository


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
