from __future__ import annotations

import logging
import os


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_MODEL_BGE = "BAAI/bge-base-en-v1.5"

EMBEDDING_DIMENSION = 384
EMBEDDING_DIMENSION_BGE = 768

_embedding_model = None
_embedding_model_bge = None
logger = logging.getLogger(__name__)


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(model_name)
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for embeddings. Install it with: pip install sentence-transformers"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Embedding model initialization failed: {exc}") from exc

    return _embedding_model


def _get_bge_model():
    global _embedding_model_bge
    if _embedding_model_bge is not None:
        return _embedding_model_bge

    try:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL_BGE", DEFAULT_EMBEDDING_MODEL_BGE)
        _embedding_model_bge = SentenceTransformer(model_name)
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for BGE embeddings. Install it with: pip install sentence-transformers"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"BGE embedding model initialization failed: {exc}") from exc

    return _embedding_model_bge


def embed_text(text: str) -> list[float]:
    model = _get_embedding_model()
    vector = model.encode(text or "", normalize_embeddings=True).tolist()
    if len(vector) != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Unexpected embedding dimension: expected {EMBEDDING_DIMENSION}, got {len(vector)}"
        )
    return vector


def embed_text_bge(text: str) -> list[float]:
    model = _get_bge_model()
    vector = model.encode(text or "", normalize_embeddings=True).tolist()
    if len(vector) != EMBEDDING_DIMENSION_BGE:
        raise RuntimeError(
            f"Unexpected BGE embedding dimension: expected {EMBEDDING_DIMENSION_BGE}, got {len(vector)}"
        )
    return vector


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return [embed_text(chunk) for chunk in chunks]


def embed_chunks_bge(chunks: list[str]) -> list[list[float]]:
    return [embed_text_bge(chunk) for chunk in chunks]
