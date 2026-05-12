from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VectorPoint:
    user_id: str
    document_id: str
    filename: str
    file_type: str
    chunk_index: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    user_id: str
    document_id: str
    filename: str
    file_type: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    score: float
