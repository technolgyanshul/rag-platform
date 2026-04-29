from __future__ import annotations

from pathlib import Path
from typing import Any

from rag.chunking import chunk_text
from rag.embeddings import embed_chunks
from rag.image_text import extract_image_text


def parse_document(file_path: str, file_type: str) -> str:
    normalized_type = file_type.lower()
    if normalized_type == "pdf":
        return _parse_pdf(file_path)
    if normalized_type == "txt":
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    if normalized_type in {"png", "jpg", "jpeg"}:
        return extract_image_text(file_path)
    raise ValueError(f"Unsupported file type: {file_type}")


def ingest_document(file_path: str, file_type: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> dict[str, Any]:
    extracted_text = parse_document(file_path=file_path, file_type=file_type)
    chunks = chunk_text(extracted_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    embeddings = embed_chunks(chunks)
    chunk_payload = [
        {
            "chunk_index": index,
            "content": chunk,
            "embedding": embedding,
            "metadata": {"source_type": file_type.lower()},
        }
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    return {"extracted_text": extracted_text, "chunks": chunk_payload}


def _parse_pdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("pypdf is required for PDF ingestion") from error

    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    combined = "\n".join(page.strip() for page in pages if page.strip())
    return combined
