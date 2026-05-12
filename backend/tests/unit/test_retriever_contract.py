import pytest

from rag.retriever import format_sources, retrieve_chunks
from rag.vector_backend import RetrievedChunk


class FakeQdrantVectorBackend:
    calls = []

    def search(self, *, query_vector: list[float], user_id: str, top_k: int) -> list[RetrievedChunk]:
        self.calls.append({"query_vector": query_vector, "user_id": user_id, "top_k": top_k})
        return [
            RetrievedChunk(
                user_id=user_id,
                document_id="doc-1",
                filename="doc.txt",
                file_type="txt",
                chunk_index=0,
                content="retrieval source",
                metadata={},
                score=0.88,
            )
        ]


def test_retrieve_chunks_embeds_query_and_searches_qdrant(monkeypatch) -> None:
    FakeQdrantVectorBackend.calls = []
    monkeypatch.setattr("rag.retriever.embed_query", lambda query: [0.2, 0.3])
    monkeypatch.setattr("rag.retriever.QdrantVectorBackend", FakeQdrantVectorBackend)

    user_id = "00000000-0000-0000-0000-000000000001"
    rows = retrieve_chunks(query="retrieval", user_id=user_id, top_k=1)

    assert FakeQdrantVectorBackend.calls == [{"query_vector": [0.2, 0.3], "user_id": user_id, "top_k": 1}]
    assert len(rows) == 1
    assert rows[0]["document_id"] == "doc-1"
    assert rows[0]["similarity"] == pytest.approx(0.88)


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
