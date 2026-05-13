from tempfile import NamedTemporaryFile

import httpx
import pytest

import routers.ingest as ingest_router
from db.supabase import SupabaseRepository
from main import app


pytestmark = pytest.mark.anyio


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test")


class FakeQdrantVectorBackend:
    points = []
    fail = False

    def upsert_points(self, points):
        if self.fail:
            raise RuntimeError("qdrant unavailable")
        self.points.extend(points)


async def test_ingest_rejects_unsupported_file_type() -> None:
    async with _client() as client:
        response = await client.post(
            "/ingest",
            files={"file": ("notes.md", b"hello", "text/markdown")},
        )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


async def test_ingest_rejects_empty_payload() -> None:
    async with _client() as client:
        response = await client.post(
            "/ingest",
            files={"file": ("empty.txt", b"", "text/plain")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


async def test_ingest_writes_temp_file_and_indexes_qdrant_points(monkeypatch) -> None:
    FakeQdrantVectorBackend.points = []
    FakeQdrantVectorBackend.fail = False

    def fake_named_temporary_file(*args, **kwargs):
        return NamedTemporaryFile(*args, **kwargs)

    monkeypatch.setattr(ingest_router, "NamedTemporaryFile", fake_named_temporary_file)
    monkeypatch.setattr(ingest_router, "QdrantVectorBackend", FakeQdrantVectorBackend)
    monkeypatch.setattr(
        ingest_router,
        "ingest_document",
        lambda file_path, file_type: {
            "chunks": [
                {
                    "chunk_index": 0,
                    "content": "hello",
                    "embedding": [0.1],
                    "embedding_bge": [0.1],
                    "metadata": {"source_type": file_type},
                }
            ]
        },
    )

    async with _client() as client:
        response = await client.post(
            "/ingest",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

    assert response.status_code == 200
    assert len(FakeQdrantVectorBackend.points) == 1


async def test_ingest_records_failed_index_status_on_qdrant_failure(monkeypatch) -> None:
    FakeQdrantVectorBackend.points = []
    FakeQdrantVectorBackend.fail = True
    monkeypatch.setattr(ingest_router, "QdrantVectorBackend", FakeQdrantVectorBackend)
    monkeypatch.setattr(
        ingest_router,
        "ingest_document",
        lambda file_path, file_type: {
            "chunks": [
                {
                    "chunk_index": 0,
                    "content": "hello",
                    "embedding": [0.1],
                    "metadata": {"source_type": file_type},
                }
            ]
        },
    )

    async with _client() as client:
        response = await client.post(
            "/ingest",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

    documents = SupabaseRepository().list_documents(user_id="00000000-0000-0000-0000-000000000001")
    assert response.status_code == 503
    assert documents[0]["index_status"] == "failed"
    assert documents[0]["index_backend"] == "qdrant_embedanything"
    assert "qdrant unavailable" in documents[0]["index_error"]


async def test_ingest_openapi_documents_error_responses() -> None:
    async with _client() as client:
        schema = (await client.get("/openapi.json")).json()

    assert {"400", "403", "500", "503"}.issubset(schema["paths"]["/ingest"]["post"]["responses"])
    assert {"403", "503"}.issubset(schema["paths"]["/ingest/documents"]["get"]["responses"])
    assert {"403", "503"}.issubset(schema["paths"]["/sessions"]["post"]["responses"])


async def test_query_history_requires_non_empty_session_id() -> None:
    async with _client() as client:
        response = await client.get("/query/history", params={"session_id": "", "limit": 10})

    assert response.status_code == 422


async def test_query_rejects_session_from_other_user() -> None:
    repository = SupabaseRepository()
    session_id = "30000000-0000-0000-0000-000000000003"
    repository.create_session(user_id="99999999-0000-0000-0000-000000000999", session_id=session_id)

    async with _client() as client:
        response = await client.post(
            "/query",
            json={"query": "mismatch", "session_id": session_id, "top_k": 1},
        )

    assert response.status_code == 403
    assert "Session is not accessible" in response.json()["detail"]
