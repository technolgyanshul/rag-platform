from pathlib import Path

from rag.embedanything_pipeline import EmbeddedChunk
from rag.ingest import ingest_document


def test_ingest_txt_uses_embedanything_semantic_chunks(monkeypatch, tmp_path: Path) -> None:
    content = "RAG platform testing text. " * 80
    file_path = tmp_path / "sample.txt"
    file_path.write_text(content, encoding="utf-8")
    calls = []

    def fake_embed_file_semantic(file_path: str, file_type: str) -> list[EmbeddedChunk]:
        calls.append((file_path, file_type))
        return [
            EmbeddedChunk(
                chunk_index=0,
                content="semantic chunk",
                embedding=[0.1, 0.2],
                metadata={"source_type": "txt"},
            )
        ]

    monkeypatch.setattr("rag.ingest.embed_file_semantic", fake_embed_file_semantic)

    result = ingest_document(str(file_path), "txt", chunk_size=300, chunk_overlap=50)

    assert calls == [(str(file_path), "txt")]
    assert result["chunks"] == [
        {
            "chunk_index": 0,
            "content": "semantic chunk",
            "embedding": [0.1, 0.2],
            "metadata": {"source_type": "txt"},
        }
    ]
