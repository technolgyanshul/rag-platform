from __future__ import annotations

import importlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from core.config import get_settings


DEFAULT_EMBEDANYTHING_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
DEFAULT_SEMANTIC_ENCODER_MODEL = "jinaai/jina-embeddings-v2-small-en"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_BATCH_SIZE = 32
EMBEDDING_DIMENSION_UNDETERMINED = "Embedding dimension cannot be determined"

SUPPORTED_FILE_TYPES = {"pdf", "txt", "md", "markdown", "png", "jpg", "jpeg", "wav"}

_embedding_model: Any | None = None
_semantic_encoder: Any | None = None
_text_embed_config: Any | None = None


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk_index: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any]


def embed_file_semantic(file_path: str, file_type: str) -> list[EmbeddedChunk]:
    normalized_type = _normalize_file_type(file_type)
    path = Path(file_path)
    non_empty_file = path.exists() and path.stat().st_size > 0

    try:
        raw_chunks = _embed_file_with_embedanything(str(path), normalized_type)
    except ImportError as exc:
        raise RuntimeError(
            "embed-anything is required for semantic embedding. Install it with: pip install embed-anything"
        ) from exc

    chunks = _normalize_chunks(raw_chunks, normalized_type)
    if non_empty_file and not chunks:
        raise RuntimeError(f"Semantic chunking returned no content for non-empty file: {file_path}")
    return chunks


def embed_query(query: str) -> list[float]:
    try:
        raw_embedding = _embed_query_with_embedanything(query or "")
    except ImportError as exc:
        raise RuntimeError(
            "embed-anything is required for query embedding. Install it with: pip install embed-anything"
        ) from exc
    return _normalize_embedding(raw_embedding)


def _embed_file_with_embedanything(file_path: str, file_type: str) -> Iterable[Any]:
    embed_anything = _import_embedanything()
    model = _get_embedding_model(embed_anything)
    config = _get_text_embed_config(embed_anything)
    return embed_anything.embed_file(file_path, embedder=model, config=config)


def _embed_query_with_embedanything(query: str) -> Any:
    embed_anything = _import_embedanything()
    model = _get_embedding_model(embed_anything)

    if callable(getattr(embed_anything, "embed_query", None)):
        return embed_anything.embed_query(query, embedder=model)
    if callable(getattr(model, "embed_query", None)):
        return model.embed_query(query)
    if callable(getattr(model, "embed_text", None)):
        return model.embed_text(query)
    if callable(getattr(model, "encode", None)):
        return model.encode(query)
    if callable(getattr(model, "embed", None)):
        raw = model.embed([query])
        return _first_embedding_result(raw)

    return _embed_query_via_temp_file(embed_anything, model, query)


def _import_embedanything() -> Any:
    try:
        return importlib.import_module("embed_anything")
    except ImportError as exc:
        raise ImportError("No module named 'embed_anything'") from exc


def _get_embedding_model(embed_anything: Any) -> Any:
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    model_id = getattr(get_settings(), "embedanything_model", DEFAULT_EMBEDANYTHING_MODEL)
    embedding_model = embed_anything.EmbeddingModel
    which_model = getattr(embed_anything, "WhichModel", None)
    bert_model = getattr(which_model, "Bert", None) if which_model is not None else None

    try:
        if bert_model is not None:
            _embedding_model = embedding_model.from_pretrained_hf(bert_model, model_id=model_id)
        else:
            _embedding_model = embedding_model.from_pretrained_hf(model_id=model_id)
    except TypeError:
        _embedding_model = embedding_model.from_pretrained_hf(model_id=model_id)

    return _embedding_model


def _get_semantic_encoder(embed_anything: Any) -> Any:
    global _semantic_encoder
    if _semantic_encoder is not None:
        return _semantic_encoder

    model_id = os.getenv("EMBEDANYTHING_SEMANTIC_ENCODER_MODEL", DEFAULT_SEMANTIC_ENCODER_MODEL)
    embedding_model = embed_anything.EmbeddingModel
    which_model = getattr(embed_anything, "WhichModel", None)
    jina_model = getattr(which_model, "Jina", None) if which_model is not None else None

    try:
        if jina_model is not None:
            _semantic_encoder = embedding_model.from_pretrained_hf(jina_model, model_id=model_id)
        else:
            _semantic_encoder = embedding_model.from_pretrained_hf(model_id=model_id)
    except TypeError:
        _semantic_encoder = embedding_model.from_pretrained_hf(model_id=model_id)

    return _semantic_encoder


def _get_text_embed_config(embed_anything: Any) -> Any:
    global _text_embed_config
    if _text_embed_config is not None:
        return _text_embed_config

    _text_embed_config = embed_anything.TextEmbedConfig(
        chunk_size=int(os.getenv("EMBEDANYTHING_CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE))),
        batch_size=int(os.getenv("EMBEDANYTHING_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))),
        splitting_strategy="semantic",
        semantic_encoder=_get_semantic_encoder(embed_anything),
    )
    return _text_embed_config


def _embed_query_via_temp_file(embed_anything: Any, model: Any, query: str) -> Any:
    config = _get_text_embed_config(embed_anything)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8") as handle:
        handle.write(query)
        handle.flush()
        raw_chunks = embed_anything.embed_file(handle.name, embedder=model, config=config)
    return _first_embedding_result(raw_chunks)


def _first_embedding_result(raw_result: Any) -> Any:
    if isinstance(raw_result, dict):
        return raw_result
    if isinstance(raw_result, (str, bytes)):
        return raw_result
    try:
        iterator = iter(raw_result)
    except TypeError:
        return raw_result

    for item in iterator:
        return item
    return []


def _normalize_chunks(raw_chunks: Iterable[Any], file_type: str) -> list[EmbeddedChunk]:
    normalized_chunks: list[EmbeddedChunk] = []
    expected_dimension: int | None = None

    if raw_chunks is None:
        return normalized_chunks

    for raw_chunk in raw_chunks:
        content = _extract_content(raw_chunk).strip()
        if not content:
            continue

        embedding = _normalize_embedding(_extract_embedding(raw_chunk))
        if expected_dimension is None:
            expected_dimension = len(embedding)
        elif len(embedding) != expected_dimension:
            raise RuntimeError(
                f"Inconsistent embedding dimension: expected {expected_dimension}, got {len(embedding)}"
            )

        metadata = _extract_metadata(raw_chunk)
        metadata["source_type"] = file_type
        normalized_chunks.append(
            EmbeddedChunk(
                chunk_index=len(normalized_chunks),
                content=content,
                embedding=embedding,
                metadata=metadata,
            )
        )

    return normalized_chunks


def _normalize_embedding(raw_embedding: Any) -> list[float]:
    embedding = _extract_embedding(raw_embedding)
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()

    if isinstance(embedding, dict):
        embedding = embedding.get("embedding") or embedding.get("vector")
    elif isinstance(embedding, list) and embedding and hasattr(embedding[0], "embedding"):
        embedding = embedding[0].embedding

    if embedding is None or isinstance(embedding, (str, bytes)):
        raise RuntimeError(EMBEDDING_DIMENSION_UNDETERMINED)

    try:
        vector = [float(value) for value in embedding]
    except (TypeError, ValueError) as exc:
        raise RuntimeError(EMBEDDING_DIMENSION_UNDETERMINED) from exc

    if not vector:
        raise RuntimeError(EMBEDDING_DIMENSION_UNDETERMINED)
    return vector


def _extract_content(raw_chunk: Any) -> str:
    if isinstance(raw_chunk, dict):
        value = raw_chunk.get("text", raw_chunk.get("content", ""))
    else:
        value = getattr(raw_chunk, "text", getattr(raw_chunk, "content", ""))
    return "" if value is None else str(value)


def _extract_embedding(raw_value: Any) -> Any:
    if isinstance(raw_value, dict):
        return raw_value.get("embedding", raw_value.get("vector", raw_value))
    return getattr(raw_value, "embedding", raw_value)


def _extract_metadata(raw_chunk: Any) -> dict[str, Any]:
    if isinstance(raw_chunk, dict):
        metadata = raw_chunk.get("metadata", {})
    else:
        metadata = getattr(raw_chunk, "metadata", {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def _normalize_file_type(file_type: str) -> str:
    normalized_type = file_type.strip().lower().lstrip(".")
    if normalized_type not in SUPPORTED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {file_type}")
    return normalized_type
