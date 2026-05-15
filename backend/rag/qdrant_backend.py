from __future__ import annotations

import os
from enum import Enum
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from core.config import get_settings
from rag.vector_backend import RetrievedChunk, VectorPoint


try:
    from qdrant_client.http import models as qdrant_models
except ImportError:
    qdrant_models = None


class _FallbackDistance(Enum):
    COSINE = "Cosine"


class _FallbackVectorParams:
    def __init__(self, *, size: int, distance: _FallbackDistance) -> None:
        self.size = size
        self.distance = distance


class _FallbackMatchValue:
    def __init__(self, *, value: Any) -> None:
        self.value = value


class _FallbackFieldCondition:
    def __init__(self, *, key: str, match: _FallbackMatchValue) -> None:
        self.key = key
        self.match = match


class _FallbackFilter:
    def __init__(self, *, must: list[_FallbackFieldCondition]) -> None:
        self.must = must


class _FallbackPointStruct:
    def __init__(self, *, id: str, vector: list[float], payload: dict[str, Any]) -> None:
        self.id = id
        self.vector = vector
        self.payload = payload


class _Models:
    Distance = qdrant_models.Distance if qdrant_models else _FallbackDistance
    VectorParams = qdrant_models.VectorParams if qdrant_models else _FallbackVectorParams
    MatchValue = qdrant_models.MatchValue if qdrant_models else _FallbackMatchValue
    FieldCondition = qdrant_models.FieldCondition if qdrant_models else _FallbackFieldCondition
    Filter = qdrant_models.Filter if qdrant_models else _FallbackFilter
    PointStruct = qdrant_models.PointStruct if qdrant_models else _FallbackPointStruct


class QdrantVectorBackend:
    def __init__(
        self,
        *,
        client: Any | None = None,
        collection_name: str | None = None,
        vector_size: int | None = None,
    ) -> None:
        settings = get_settings()
        self.collection_name = collection_name or getattr(
            settings,
            "qdrant_collection",
            os.getenv("QDRANT_COLLECTION", "rag_chunks"),
        )
        self.vector_size = vector_size
        self._client = client
        self._collection_ready = False

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def upsert_points(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        self._ensure_collection(vector_size=len(points[0].embedding))
        qdrant_points = [
            _Models.PointStruct(
                id=deterministic_point_id(point.document_id, point.chunk_index),
                vector=point.embedding,
                payload=_payload_for_point(point),
            )
            for point in points
        ]
        self.client.upsert(collection_name=self.collection_name, points=qdrant_points)

    def search(self, *, query_vector: list[float], user_id: str, top_k: int) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if not query_vector:
            raise ValueError("query_vector must not be empty")

        self._ensure_collection(vector_size=len(query_vector))
        query_filter = _Models.Filter(
            must=[
                _Models.FieldCondition(
                    key="user_id",
                    match=_Models.MatchValue(value=user_id),
                )
            ]
        )
        results = self._search(query_vector=query_vector, query_filter=query_filter, top_k=top_k)
        chunks = [_retrieved_chunk(result) for result in results]
        chunks.sort(key=lambda chunk: chunk.score, reverse=True)
        return chunks

    def delete_document_points(self, *, user_id: str, document_id: str) -> None:
        """Remove all vector points for one user's document."""
        if not user_id.strip():
            raise ValueError("user_id must not be empty")
        if not document_id.strip():
            raise ValueError("document_id must not be empty")

        if not self.client.collection_exists(self.collection_name):
            return

        point_filter = _Models.Filter(
            must=[
                _Models.FieldCondition(
                    key="user_id",
                    match=_Models.MatchValue(value=user_id),
                ),
                _Models.FieldCondition(
                    key="document_id",
                    match=_Models.MatchValue(value=document_id),
                ),
            ]
        )
        self.client.delete(collection_name=self.collection_name, points_selector=point_filter)

    def _ensure_collection(self, *, vector_size: int) -> None:
        if self._collection_ready:
            return

        if self.vector_size is None:
            self.vector_size = vector_size
        if self.vector_size < 1:
            raise ValueError("vector_size must be >= 1")

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=_Models.VectorParams(
                    size=self.vector_size,
                    distance=_Models.Distance.COSINE,
                ),
            )
        self._collection_ready = True

    def _search(self, *, query_vector: list[float], query_filter: Any, top_k: int) -> list[Any]:
        if hasattr(self.client, "search"):
            return self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        return getattr(response, "points", response)

    def _build_client(self) -> Any:
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError("qdrant-client is required for QdrantVectorBackend") from exc

        settings = get_settings()
        url = getattr(settings, "qdrant_url", os.getenv("QDRANT_URL", ""))
        api_key = os.getenv("QDRANT_API_KEY")
        if url:
            return QdrantClient(url=url, api_key=api_key)
        return QdrantClient(path=os.getenv("QDRANT_PATH", "./qdrant_data"))


def deterministic_point_id(document_id: str, chunk_index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def _payload_for_point(point: VectorPoint) -> dict[str, Any]:
    return {
        "user_id": point.user_id,
        "document_id": point.document_id,
        "filename": point.filename,
        "file_type": point.file_type,
        "chunk_index": point.chunk_index,
        "content": point.content,
        "metadata": point.metadata,
    }


def _retrieved_chunk(result: Any) -> RetrievedChunk:
    payload = getattr(result, "payload", None) or {}
    return RetrievedChunk(
        user_id=str(payload.get("user_id", "")),
        document_id=str(payload.get("document_id", "")),
        filename=str(payload.get("filename", "")),
        file_type=str(payload.get("file_type", "")),
        chunk_index=int(payload.get("chunk_index", -1)),
        content=str(payload.get("content", "")),
        metadata=payload.get("metadata", {}) or {},
        score=float(getattr(result, "score", 0.0)),
    )
