from __future__ import annotations

import logging
import time
from collections import OrderedDict
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from core.auth import AuthUser, get_current_user
from core.config import get_settings
from db.supabase import SupabaseRepository
from rag.ingest import ingest_document


router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = logging.getLogger(__name__)

settings = get_settings()
ALLOWED_FILE_TYPES = settings.allowed_file_types
MAX_FILE_SIZE_MB = settings.max_file_size_mb
IDEMPOTENCY_MAX_ENTRIES = 1000
IDEMPOTENCY_TTL_SECONDS = 60 * 60


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    chunks_created: int


_INGEST_IDEMPOTENCY_CACHE: OrderedDict[str, tuple[float, IngestResponse]] = OrderedDict()


def _evict_old_idempotency_entries() -> None:
    now = time.time()
    keys_to_delete = [key for key, (created_at, _) in _INGEST_IDEMPOTENCY_CACHE.items() if now - created_at > IDEMPOTENCY_TTL_SECONDS]
    for key in keys_to_delete:
        _INGEST_IDEMPOTENCY_CACHE.pop(key, None)

    while len(_INGEST_IDEMPOTENCY_CACHE) > IDEMPOTENCY_MAX_ENTRIES:
        _INGEST_IDEMPOTENCY_CACHE.popitem(last=False)


@router.post("", response_model=IngestResponse)
async def ingest(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
    file: UploadFile = File(...),
    team_id: UUID = Form(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> IngestResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    _evict_old_idempotency_entries()

    if idempotency_key and idempotency_key in _INGEST_IDEMPOTENCY_CACHE:
        _, cached = _INGEST_IDEMPOTENCY_CACHE[idempotency_key]
        logger.info("ingest_request_idempotent_replay", extra={"request_id": request_id, "team_id": str(team_id)})
        return cached

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
    try:
        document_row = repository.insert_document(
            user_id=auth_user.user_id,
            team_id=str(team_id),
            filename=file.filename or "untitled",
            file_type=extension,
            chunk_count=len(chunks),
        )
        repository.insert_chunks(document_id=document_row["id"], chunks=chunks)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("ingest_request_persistence_failed", extra={"request_id": request_id, "team_id": str(team_id)})
        raise HTTPException(status_code=503, detail="Document persistence temporarily unavailable") from error

    response = IngestResponse(
        document_id=document_row["id"],
        filename=file.filename or "untitled",
        file_type=extension,
        chunks_created=len(chunks),
    )
    if idempotency_key:
        _INGEST_IDEMPOTENCY_CACHE[idempotency_key] = (time.time(), response)
    _evict_old_idempotency_entries()
    return response


@router.get("/documents")
def list_documents(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
    team_id: UUID = Query(...),
) -> list[dict[str, object]]:
    request_id = getattr(request.state, "request_id", "unknown")
    repository = SupabaseRepository()
    try:
        return repository.list_documents(user_id=auth_user.user_id, team_id=str(team_id))
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("ingest_documents_list_failed", extra={"request_id": request_id, "team_id": str(team_id)})
        raise HTTPException(status_code=503, detail="Document listing temporarily unavailable") from error
