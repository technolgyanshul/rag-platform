from __future__ import annotations

import os
from pathlib import Path

import pytest

from rag.embedanything_pipeline import embed_query
from rag.ingest import ingest_document
from rag.qdrant_backend import QdrantVectorBackend
from rag.vector_backend import VectorPoint


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_QDRANT_TESTS", "false").lower() != "true",
    reason="Requires RUN_QDRANT_TESTS=true, Qdrant, and local EmbedAnything model availability",
)


def test_qdrant_embedanything_txt_smoke(tmp_path: Path) -> None:
    user_id = "smoke-user"
    document_id = "smoke-document"
    file_path = tmp_path / "smoke.txt"
    file_path.write_text("Qdrant smoke retrieval phrase for semantic indexing.", encoding="utf-8")

    ingestion_result = ingest_document(str(file_path), "txt")
    points = [
        VectorPoint(
            user_id=user_id,
            document_id=document_id,
            filename=file_path.name,
            file_type="txt",
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            embedding=chunk["embedding"],
            metadata=chunk.get("metadata", {}),
        )
        for chunk in ingestion_result["chunks"]
    ]

    backend = QdrantVectorBackend()
    backend.upsert_points(points)
    rows = backend.search(
        query_vector=embed_query("semantic indexing smoke phrase"),
        user_id=user_id,
        top_k=3,
    )

    assert rows
    assert rows[0].document_id == document_id
