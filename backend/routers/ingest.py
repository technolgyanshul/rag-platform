from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from db.supabase import SupabaseRepository
from rag.ingest import ingest_document


router = APIRouter(prefix="/ingest", tags=["ingest"])


ALLOWED_FILE_TYPES = {file_type.strip().lower() for file_type in os.getenv("ALLOWED_FILE_TYPES", "pdf,png,jpg,jpeg,txt").split(",")}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    chunks_created: int


@router.post("", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), team_id: str = Form(...)) -> IngestResponse:
    extension = Path(file.filename or "").suffix.lower().replace(".", "")
    if extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")

    payload = await file.read()
    size_in_mb = len(payload) / (1024 * 1024)
    if size_in_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB")

    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
        temp_file.write(payload)
        temp_path = temp_file.name

    try:
        ingestion_result = ingest_document(file_path=temp_path, file_type=extension)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        Path(temp_path).unlink(missing_ok=True)

    chunks = ingestion_result["chunks"]
    repository = SupabaseRepository()
    document_row = repository.insert_document(
        team_id=team_id,
        filename=file.filename or "untitled",
        file_type=extension,
        chunk_count=len(chunks),
    )
    repository.insert_chunks(document_id=document_row["id"], chunks=chunks)

    return IngestResponse(
        document_id=document_row["id"],
        filename=file.filename or "untitled",
        file_type=extension,
        chunks_created=len(chunks),
    )


@router.get("/documents")
def list_documents(team_id: str) -> list[dict[str, object]]:
    repository = SupabaseRepository()
    return repository.list_documents(team_id=team_id)
