from __future__ import annotations

import hashlib
import os


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


EMBEDDING_DIMENSION = 384
_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(model_name)
    except Exception:
        _embedding_model = False

    return _embedding_model


def _hash_embed_text(text: str) -> list[float]:
    seed = (text or "").encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    vector: list[float] = []

    while len(vector) < EMBEDDING_DIMENSION:
        for byte in digest:
            value = (byte / 255.0) * 2.0 - 1.0
            vector.append(value)
            if len(vector) == EMBEDDING_DIMENSION:
                break
        digest = hashlib.sha256(digest).digest()

    return vector


def embed_text(text: str) -> list[float]:
    model = _get_embedding_model()
    if model:
        vector = model.encode(text or "", normalize_embeddings=True).tolist()
        if len(vector) == EMBEDDING_DIMENSION:
            return vector
    return _hash_embed_text(text)


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return [embed_text(chunk) for chunk in chunks]
