from __future__ import annotations

import logging
import time
from collections import OrderedDict
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel

import observability
from core.auth import AuthUser, get_current_user
from core.config import get_settings
from db.supabase import SupabaseRepository
from rag.ingest import ingest_document
from rag.qdrant_backend import QdrantVectorBackend
from rag.vector_backend import VectorPoint


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


class DocumentListItem(BaseModel):
    id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: str
    index_backend: str = "legacy_supabase_pgvector"
    index_status: str = "legacy_unindexed"
    indexed_at: str | None = None
    index_error: str | None = None


class DocumentDownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int


_INGEST_IDEMPOTENCY_CACHE: OrderedDict[str, tuple[float, IngestResponse]] = OrderedDict()


def _evict_old_idempotency_entries() -> None:
    now = time.time()
    keys_to_delete = [key for key, (created_at, _) in _INGEST_IDEMPOTENCY_CACHE.items() if now - created_at > IDEMPOTENCY_TTL_SECONDS]
    for key in keys_to_delete:
        _INGEST_IDEMPOTENCY_CACHE.pop(key, None)

    while len(_INGEST_IDEMPOTENCY_CACHE) > IDEMPOTENCY_MAX_ENTRIES:
        _INGEST_IDEMPOTENCY_CACHE.popitem(last=False)


@router.post("", response_model=IngestResponse, responses={400: {}, 403: {}, 500: {}, 503: {}})
async def ingest(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> IngestResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    ingest_start = time.perf_counter()
    _evict_old_idempotency_entries()

    cache_key = f"{auth_user.user_id}:{idempotency_key}" if idempotency_key else None
    if cache_key and cache_key in _INGEST_IDEMPOTENCY_CACHE:
        _, cached = _INGEST_IDEMPOTENCY_CACHE[cache_key]
        logger.info("ingest_request_idempotent_replay", extra={"request_id": request_id, "user_id": auth_user.user_id})
        observer.record_trace_event(
            event_name="ingest_idempotent_replay",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            metadata={"filename": file.filename, "idempotency_key": idempotency_key},
        )
        return cached

    extension = Path(file.filename or "").suffix.lower().replace(".", "")
    if extension not in ALLOWED_FILE_TYPES:
        observer.record_trace_event(
            event_name="ingest_validation_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            level="WARNING",
            status="failed",
            metadata={"filename": file.filename, "extension": extension, "allowed_file_types": sorted(ALLOWED_FILE_TYPES)},
        )
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")

    try:
        repository = SupabaseRepository()
        observer.record_trace_event(
            event_name="ingest_repository_ready",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="supabase",
            metadata={"filename": file.filename, "file_type": extension},
        )
    except Exception as error:
        logger.exception("ingest_repository_unavailable", extra={"request_id": request_id, "user_id": auth_user.user_id})
        observer.record_trace_event(
            event_name="ingest_repository_unavailable",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="supabase",
            level="ERROR",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=503, detail="Document persistence temporarily unavailable") from error

    payload = await file.read()
    size_in_mb = len(payload) / (1024 * 1024)
    if size_in_mb > MAX_FILE_SIZE_MB:
        observer.record_trace_event(
            event_name="ingest_validation_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            level="WARNING",
            status="failed",
            metadata={"filename": file.filename, "size_bytes": len(payload), "max_file_size_mb": MAX_FILE_SIZE_MB},
        )
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB")
    if not payload:
        observer.record_trace_event(
            event_name="ingest_validation_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            level="WARNING",
            status="failed",
            metadata={"filename": file.filename, "size_bytes": 0},
        )
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    temp_path = _write_temp_upload(payload, extension)
    observer.record_trace_event(
        event_name="ingest_temp_file_created",
        request_id=request_id,
        user_id=auth_user.user_id,
        route="/ingest",
        component="ingest_router",
        metadata={"filename": file.filename, "file_type": extension, "size_bytes": len(payload), "temp_path": temp_path},
    )

    try:
        document_row = repository.insert_document(
            user_id=auth_user.user_id,
            filename=file.filename or "untitled",
            file_type=extension,
            chunk_count=0,
            embedding_model_version=settings.embedanything_model,
            index_version=settings.index_version,
            index_backend="qdrant_embedanything",
            index_status="indexing",
        )
        observer.record_trace_event(
            event_name="ingest_document_row_created",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="supabase",
            metadata={"document": document_row},
        )
        pipeline_start = time.perf_counter()
        ingestion_result = ingest_document(file_path=temp_path, file_type=extension)
        chunks = ingestion_result["chunks"]
        observer.record_trace_event(
            event_name="ingest_pipeline_finished",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_pipeline",
            duration_ms=int((time.perf_counter() - pipeline_start) * 1000),
            metadata={"filename": file.filename, "chunks": chunks},
        )
        qdrant_start = time.perf_counter()
        QdrantVectorBackend().upsert_points(
            [
                VectorPoint(
                    user_id=auth_user.user_id,
                    document_id=document_row["id"],
                    filename=file.filename or "untitled",
                    file_type=extension,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    embedding=chunk["embedding"],
                    metadata=chunk.get("metadata", {}),
                )
                for chunk in chunks
            ]
        )
        observer.record_trace_event(
            event_name="ingest_qdrant_upsert_finished",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="qdrant",
            duration_ms=int((time.perf_counter() - qdrant_start) * 1000),
            metadata={"document_id": document_row["id"], "chunk_count": len(chunks)},
        )
        document_row["chunk_count"] = len(chunks)
        repository.update_document_index_status(
            user_id=auth_user.user_id,
            document_id=document_row["id"],
            status="indexed",
            backend="qdrant_embedanything",
            chunk_count=len(chunks),
        )
        observer.record_trace_event(
            event_name="ingest_document_indexed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="supabase",
            status="indexed",
            metadata={"document_id": document_row["id"], "chunk_count": len(chunks)},
        )
    except RuntimeError as error:
        if "document_row" in locals():
            repository.update_document_index_status(
                user_id=auth_user.user_id,
                document_id=document_row["id"],
                status="failed",
                backend="qdrant_embedanything",
                error=str(error)[:500],
            )
        observer.record_trace_event(
            event_name="ingest_indexing_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            level="ERROR",
            status="failed",
            metadata={"filename": file.filename, "document_id": document_row["id"] if "document_row" in locals() else None},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Document indexing temporarily unavailable") from error
    except ValueError as error:
        observer.record_trace_event(
            event_name="ingest_value_error",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PermissionError as error:
        observer.record_trace_event(
            event_name="ingest_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("ingest_request_indexing_failed", extra={"request_id": request_id, "user_id": auth_user.user_id})
        if "document_row" in locals():
            repository.update_document_index_status(
                user_id=auth_user.user_id,
                document_id=document_row["id"],
                status="failed",
                backend="qdrant_embedanything",
                error=str(error)[:500],
            )
        observer.record_trace_event(
            event_name="ingest_request_indexing_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest",
            component="ingest_router",
            level="ERROR",
            status="failed",
            metadata={"filename": file.filename, "document_id": document_row["id"] if "document_row" in locals() else None},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Document indexing temporarily unavailable") from error
    finally:
        Path(temp_path).unlink(missing_ok=True)

    response = IngestResponse(
        document_id=document_row["id"],
        filename=file.filename or "untitled",
        file_type=extension,
        chunks_created=len(chunks),
    )
    if cache_key:
        _INGEST_IDEMPOTENCY_CACHE[cache_key] = (time.time(), response)
    _evict_old_idempotency_entries()
    observer.record_trace_event(
        event_name="ingest_request_finished",
        request_id=request_id,
        user_id=auth_user.user_id,
        route="/ingest",
        component="ingest_router",
        status="success",
        duration_ms=int((time.perf_counter() - ingest_start) * 1000),
        metadata=response.model_dump(),
    )
    return response


@router.get("/documents", response_model=list[DocumentListItem], responses={403: {}, 503: {}})
async def list_documents(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
) -> list[DocumentListItem]:
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        rows = repository.list_documents(user_id=auth_user.user_id)
        observer.record_trace_event(
            event_name="ingest_documents_loaded",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest/documents",
            component="ingest_router",
            metadata={"row_count": len(rows), "documents": rows},
        )
    except PermissionError as error:
        observer.record_trace_event(
            event_name="ingest_documents_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest/documents",
            component="ingest_router",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("ingest_documents_list_failed", extra={"request_id": request_id, "user_id": auth_user.user_id})
        observer.record_trace_event(
            event_name="ingest_documents_list_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest/documents",
            component="ingest_router",
            level="ERROR",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=503, detail="Document listing temporarily unavailable") from error
    return [DocumentListItem(**row) for row in rows]


@router.get("/documents/{document_id}/download", response_model=DocumentDownloadResponse, responses={403: {}, 503: {}})
async def create_document_download_url(
    document_id: str,
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
) -> DocumentDownloadResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    expires_in_seconds = 300
    try:
        repository = SupabaseRepository()
        url = repository.create_document_download_url(
            user_id=auth_user.user_id,
            document_id=document_id,
            expires_in_seconds=expires_in_seconds,
        )
        observer.record_trace_event(
            event_name="ingest_document_download_url_created",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest/documents/{document_id}/download",
            component="ingest_router",
            metadata={"document_id": document_id, "expires_in_seconds": expires_in_seconds, "url": url},
        )
    except PermissionError as error:
        observer.record_trace_event(
            event_name="ingest_document_download_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest/documents/{document_id}/download",
            component="ingest_router",
            level="WARNING",
            status="failed",
            metadata={"document_id": document_id},
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("ingest_document_download_url_failed", extra={"request_id": request_id, "document_id": document_id})
        observer.record_trace_event(
            event_name="ingest_document_download_url_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route="/ingest/documents/{document_id}/download",
            component="ingest_router",
            level="ERROR",
            status="failed",
            metadata={"document_id": document_id},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Document download temporarily unavailable") from error
    return DocumentDownloadResponse(url=url, expires_in_seconds=expires_in_seconds)


def _write_temp_upload(payload: bytes, extension: str) -> str:
    with NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
        temp_file.write(payload)
        return temp_file.name
