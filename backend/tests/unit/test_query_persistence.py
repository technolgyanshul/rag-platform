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
