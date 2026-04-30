from db.supabase import SupabaseRepository
from rag.retriever import format_sources, retrieve_chunks


def test_search_chunks_returns_ranked_rows() -> None:
    repository = SupabaseRepository()
    team_id = "11111111-1111-1111-1111-111111111111"
    user_id = "00000000-0000-0000-0000-000000000001"
    document = repository.insert_document(user_id=user_id, team_id=team_id, filename="notes.txt", file_type="txt", chunk_count=2)
    repository.insert_chunks(
        document_id=document["id"],
        chunks=[
            {
                "chunk_index": 0,
                "content": "alpha",
                "embedding": [1.0, 0.0, 0.0],
                "metadata": {},
            },
            {
                "chunk_index": 1,
                "content": "beta",
                "embedding": [0.0, 1.0, 0.0],
                "metadata": {},
            },
        ],
    )

    rows = repository.search_chunks(user_id=user_id, team_id=team_id, query_embedding=[1.0, 0.0, 0.0], top_k=1)

    assert len(rows) == 1
    assert rows[0]["content"] == "alpha"
    assert rows[0]["filename"] == "notes.txt"


def test_retrieve_chunks_returns_rows() -> None:
    repository = SupabaseRepository()
    team_id = "22222222-2222-2222-2222-222222222222"
    user_id = "00000000-0000-0000-0000-000000000001"
    document = repository.insert_document(user_id=user_id, team_id=team_id, filename="doc.txt", file_type="txt", chunk_count=1)
    repository.insert_chunks(
        document_id=document["id"],
        chunks=[
            {
                "chunk_index": 0,
                "content": "retrieval source",
                "embedding": [0.2] * 384,
                "metadata": {},
            }
        ],
    )

    rows = retrieve_chunks(query="retrieval", team_id=team_id, user_id=user_id, top_k=1)

    assert len(rows) == 1
    assert rows[0]["document_id"] == document["id"]


def test_format_sources_includes_filename_and_chunk_index() -> None:
    formatted = format_sources(
        [
            {
                "document_id": "doc-1",
                "filename": "paper.pdf",
                "chunk_index": 3,
                "content": "This is a long context snippet",
                "similarity": 0.91,
            }
        ]
    )

    assert formatted[0]["filename"] == "paper.pdf"
    assert formatted[0]["chunk_index"] == 3
    assert "content_preview" in formatted[0]
