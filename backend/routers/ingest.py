from __future__ import annotations

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from core.config import get_settings
from db.supabase import SupabaseRepository
from rag.ingest import ingest_document


router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = logging.getLogger(__name__)


settings = get_settings()
ALLOWED_FILE_TYPES = settings.allowed_file_types
MAX_FILE_SIZE_MB = settings.max_file_size_mb


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    chunks_created: int


_INGEST_IDEMPOTENCY_CACHE: dict[str, IngestResponse] = {}


@router.post("", response_model=IngestResponse)
async def ingest(
    request: Request,
    file: UploadFile = File(...),
    team_id: str = Form(..., min_length=1, max_length=128),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> IngestResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    if idempotency_key and idempotency_key in _INGEST_IDEMPOTENCY_CACHE:
        logger.info("ingest_request_idempotent_replay", extra={"request_id": request_id, "team_id": team_id})
        return _INGEST_IDEMPOTENCY_CACHE[idempotency_key]
    extension = Path(file.filename or "").suffix.lower().replace(".", "")
    logger.info(
        "ingest_request_started",
        extra={"request_id": request_id, "team_id": team_id, "filename": file.filename or "untitled", "file_type": extension},
    )
    if extension not in ALLOWED_FILE_TYPES:
        logger.warning(
            "ingest_request_unsupported_file_type",
            extra={"request_id": request_id, "team_id": team_id, "file_type": extension},
        )
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")

    payload = await file.read()
    size_in_mb = len(payload) / (1024 * 1024)
    if size_in_mb > MAX_FILE_SIZE_MB:
        logger.warning(
            "ingest_request_file_too_large",
            extra={"request_id": request_id, "team_id": team_id, "size_mb": round(size_in_mb, 3), "max_mb": MAX_FILE_SIZE_MB},
        )
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB")

    if not payload:
        logger.warning("ingest_request_empty_payload", extra={"request_id": request_id, "team_id": team_id})
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
        temp_file.write(payload)
        temp_path = temp_file.name

    try:
        ingestion_result = ingest_document(file_path=temp_path, file_type=extension)
    except RuntimeError as error:
        logger.exception("ingest_request_runtime_error", extra={"request_id": request_id, "team_id": team_id, "error": str(error)})
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ValueError as error:
        logger.warning("ingest_request_validation_error", extra={"request_id": request_id, "team_id": team_id, "error": str(error)})
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        Path(temp_path).unlink(missing_ok=True)

    chunks = ingestion_result["chunks"]
    repository = SupabaseRepository()
    try:
        document_row = repository.insert_document(
            team_id=team_id,
            filename=file.filename or "untitled",
            file_type=extension,
            chunk_count=len(chunks),
        )
        repository.insert_chunks(document_id=document_row["id"], chunks=chunks)
    except Exception as error:
        logger.exception("ingest_request_persistence_failed", extra={"request_id": request_id, "team_id": team_id})
        raise HTTPException(status_code=503, detail="Document persistence temporarily unavailable") from error
    logger.info(
        "ingest_request_completed",
        extra={
            "request_id": request_id,
            "team_id": team_id,
            "document_id": document_row["id"],
            "file_type": extension,
            "chunk_count": len(chunks),
        },
    )

    response = IngestResponse(
        document_id=document_row["id"],
        filename=file.filename or "untitled",
        file_type=extension,
        chunks_created=len(chunks),
    )
    if idempotency_key:
        _INGEST_IDEMPOTENCY_CACHE[idempotency_key] = response
    return response


@router.get("/documents")
def list_documents(request: Request, team_id: str = Query(..., min_length=1, max_length=128)) -> list[dict[str, object]]:
    request_id = getattr(request.state, "request_id", "unknown")
    repository = SupabaseRepository()
    try:
        return repository.list_documents(team_id=team_id)
    except Exception as error:
        logger.exception("ingest_documents_list_failed", extra={"request_id": request_id, "team_id": team_id})
        raise HTTPException(status_code=503, detail="Document listing temporarily unavailable") from error
