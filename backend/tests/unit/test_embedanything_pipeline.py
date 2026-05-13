from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from rag import embedanything_pipeline as pipeline
from rag.embedanything_pipeline import EmbeddedChunk


def test_embed_file_semantic_normalizes_embedanything_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "source.txt"
    file_path.write_text("alpha beta gamma", encoding="utf-8")

    raw_chunks = [
        SimpleNamespace(text="alpha beta", embedding=[0.1, 0.2], metadata={"page": 1}),
        {"text": "gamma", "embedding": (0.3, 0.4), "metadata": {"page": 2}},
    ]
    monkeypatch.setattr(pipeline, "_embed_file_with_embedanything", lambda path: raw_chunks)

    chunks = pipeline.embed_file_semantic(str(file_path), "TXT")

    assert chunks == [
        EmbeddedChunk(
            chunk_index=0,
            content="alpha beta",
            embedding=[0.1, 0.2],
            metadata={"source_type": "txt", "page": 1},
        ),
        EmbeddedChunk(
            chunk_index=1,
            content="gamma",
            embedding=[0.3, 0.4],
            metadata={"source_type": "txt", "page": 2},
        ),
    ]


def test_embed_query_returns_normalized_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "_embed_query_with_embedanything", lambda query: (1, 2.5, 3))

    assert pipeline.embed_query("what is rag?") == [1.0, 2.5, 3.0]


def test_embed_query_falls_back_to_sequence_input_when_string_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeEmbedAnything:
        def embed_query(self, query, *, embedder):
            if isinstance(query, str):
                raise TypeError("Can't extract `str` to `Vec`")
            return [{"embedding": [0.4, 0.5, 0.6]}]

    monkeypatch.setattr(pipeline, "_import_embedanything", lambda: FakeEmbedAnything())
    monkeypatch.setattr(pipeline, "_get_embedding_model", lambda _module: object())

    embedding = pipeline._embed_query_with_embedanything("hello")

    assert embedding == {"embedding": [0.4, 0.5, 0.6]}


def test_missing_embedanything_dependency_fails_clearly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "source.txt"
    file_path.write_text("content", encoding="utf-8")

    def missing_dependency(path: str) -> list[object]:
        raise ImportError("No module named 'embed_anything'")

    monkeypatch.setattr(pipeline, "_embed_file_with_embedanything", missing_dependency)

    with pytest.raises(RuntimeError, match="embed-anything is required"):
        pipeline.embed_file_semantic(str(file_path), "txt")


def test_unsupported_file_type_fails_before_embedding(tmp_path: Path) -> None:
    file_path = tmp_path / "source.csv"
    file_path.write_text("a,b", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type: csv"):
        pipeline.embed_file_semantic(str(file_path), "csv")


def test_non_empty_file_with_no_semantic_content_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file_path = tmp_path / "source.txt"
    file_path.write_text("content that should produce chunks", encoding="utf-8")
    monkeypatch.setattr(pipeline, "_embed_file_with_embedanything", lambda path: [])

    with pytest.raises(RuntimeError, match="Semantic chunking returned no content"):
        pipeline.embed_file_semantic(str(file_path), "txt")


def test_empty_file_may_return_no_chunks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "empty.txt"
    file_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(pipeline, "_embed_file_with_embedanything", lambda path: [])

    assert pipeline.embed_file_semantic(str(file_path), "txt") == []


def test_missing_embedding_dimension_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "source.txt"
    file_path.write_text("content", encoding="utf-8")
    monkeypatch.setattr(
        pipeline,
        "_embed_file_with_embedanything",
        lambda path: [SimpleNamespace(text="content", embedding=[], metadata={})],
    )

    with pytest.raises(RuntimeError, match="Embedding dimension cannot be determined"):
        pipeline.embed_file_semantic(str(file_path), "txt")


def test_inconsistent_embedding_dimensions_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "source.txt"
    file_path.write_text("content", encoding="utf-8")
    monkeypatch.setattr(
        pipeline,
        "_embed_file_with_embedanything",
        lambda path: [
            SimpleNamespace(text="first", embedding=[0.1, 0.2], metadata={}),
            SimpleNamespace(text="second", embedding=[0.3], metadata={}),
        ],
    )

    with pytest.raises(RuntimeError, match="Inconsistent embedding dimension"):
        pipeline.embed_file_semantic(str(file_path), "txt")


def test_source_type_metadata_is_normalized(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "source.md"
    file_path.write_text("markdown content", encoding="utf-8")
    monkeypatch.setattr(
        pipeline,
        "_embed_file_with_embedanything",
        lambda path: [
            {"content": "markdown content", "embedding": [0.1], "metadata": {"source_type": "wrong"}}
        ],
    )

    chunks = pipeline.embed_file_semantic(str(file_path), " .MD ")

    assert chunks[0].metadata["source_type"] == "md"
