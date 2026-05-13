from __future__ import annotations

from typing import Any

import pytest

from rag.qdrant_backend import QdrantVectorBackend
from rag.vector_backend import VectorPoint


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collections: set[str] = set()
        self.create_collection_calls: list[dict[str, Any]] = []
        self.upsert_calls: list[dict[str, Any]] = []
        self.search_calls: list[dict[str, Any]] = []
        self.search_results: list[Any] = []

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        self.collections.add(collection_name)
        self.create_collection_calls.append(
            {
                "collection_name": collection_name,
                "vectors_config": vectors_config,
            }
        )

    def upsert(self, collection_name: str, points: list[Any]) -> None:
        self.upsert_calls.append({"collection_name": collection_name, "points": points})

    def search(self, **kwargs: Any) -> list[Any]:
        self.search_calls.append(kwargs)
        return self.search_results


class FakeResult:
    def __init__(self, payload: dict[str, Any], score: float) -> None:
        self.payload = payload
        self.score = score


def test_collection_created_once_with_cosine_distance() -> None:
    client = FakeQdrantClient()
    backend = QdrantVectorBackend(client=client, collection_name="rag_chunks")
    point = _point(document_id="doc-1", chunk_index=0, embedding=[0.1, 0.2, 0.3])

    backend.upsert_points([point])
    backend.upsert_points([point])

    assert len(client.create_collection_calls) == 1
    created = next(iter(client.create_collection_calls), None)
    assert created is not None
    assert created["collection_name"] == "rag_chunks"
    assert created["vectors_config"].size == 3
    assert created["vectors_config"].distance.value == "Cosine"


def test_upsert_payload_includes_isolation_fields_and_deterministic_ids() -> None:
    client = FakeQdrantClient()
    backend = QdrantVectorBackend(client=client, collection_name="rag_chunks")
    first = _point(document_id="doc-1", chunk_index=7, user_id="user-a", filename="a.txt")
    second = _point(document_id="doc-1", chunk_index=7, user_id="user-a", filename="a.txt")

    backend.upsert_points([first, second])

    upsert_call = next(iter(client.upsert_calls), None)
    assert upsert_call is not None
    points = upsert_call["points"]
    assert len(points) == 2
    first_point, second_point = points
    assert first_point.id == second_point.id
    assert first_point.payload == {
        "user_id": "user-a",
        "document_id": "doc-1",
        "filename": "a.txt",
        "file_type": "txt",
        "chunk_index": 7,
        "content": "chunk body",
        "metadata": {"page": 2},
    }


def test_search_applies_user_id_filter_and_sorts_by_score() -> None:
    client = FakeQdrantClient()
    client.collections.add("rag_chunks")
    client.search_results = [
        FakeResult(
            payload={
                "user_id": "user-a",
                "document_id": "doc-low",
                "filename": "low.txt",
                "file_type": "txt",
                "chunk_index": 1,
                "content": "low",
                "metadata": {},
            },
            score=0.2,
        ),
        FakeResult(
            payload={
                "user_id": "user-a",
                "document_id": "doc-high",
                "filename": "high.txt",
                "file_type": "txt",
                "chunk_index": 0,
                "content": "high",
                "metadata": {"section": "intro"},
            },
            score=0.9,
        ),
    ]
    backend = QdrantVectorBackend(client=client, collection_name="rag_chunks")

    rows = backend.search(query_vector=[0.3, 0.4], user_id="user-a", top_k=2)

    search_call = next(iter(client.search_calls), None)
    assert search_call is not None
    filter_conditions = search_call["query_filter"].must
    assert len(filter_conditions) == 1
    user_filter = next(iter(filter_conditions), None)
    assert user_filter is not None
    assert user_filter.key == "user_id"
    assert user_filter.match.value == "user-a"
    assert len(rows) == 2
    assert [row.document_id for row in rows] == ["doc-high", "doc-low"]
    first_row = next(iter(rows), None)
    assert first_row is not None
    assert first_row.score == pytest.approx(0.9)
    assert first_row.metadata == {"section": "intro"}


def _point(
    *,
    document_id: str,
    chunk_index: int,
    user_id: str = "user-a",
    filename: str = "notes.txt",
    embedding: list[float] | None = None,
) -> VectorPoint:
    return VectorPoint(
        user_id=user_id,
        document_id=document_id,
        filename=filename,
        file_type="txt",
        chunk_index=chunk_index,
        content="chunk body",
        embedding=embedding or [0.1, 0.2],
        metadata={"page": 2},
    )
