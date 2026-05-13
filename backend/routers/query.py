from __future__ import annotations

import logging
import re
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

import observability
from core.auth import AuthUser, get_current_user
from core.config import get_settings
from db.supabase import SupabaseRepository
from rag.generator import generate_answer
from rag.retriever import format_sources, retrieve_chunks


QUERY_ROUTE_PREFIX = "/query"

router = APIRouter(prefix=QUERY_ROUTE_PREFIX, tags=["query"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=get_settings().max_query_length)
    session_id: UUID
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceItem(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    content_preview: str
    score: float


class RetrievalMetadata(BaseModel):
    embedding_model_version: str
    index_version: str
    top_k: int


class QueryResponse(BaseModel):
    query_id: str | None = None
    query: str
    final_answer: str
    reasoning: str | None = None
    sources: list[SourceItem]
    retrieval_count: int
    insufficient_context: bool
    model_version: str
    retrieval_metadata: RetrievalMetadata


class QueryHistoryItem(BaseModel):
    id: str
    session_id: str
    query_text: str
    final_answer: str
    overall_score: float | None = None
    citation_accuracy: float | None = None
    insight_depth: float | None = None
    response_time_ms: int | None = None
    created_at: str


_THINK_TAG_PATTERN = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)


def _split_reasoning_and_answer(raw_text: str) -> tuple[str | None, str]:
    match = _THINK_TAG_PATTERN.search(raw_text or "")
    if not match:
        return None, (raw_text or "").strip()

    reasoning = match.group(1).strip() or None
    answer = _THINK_TAG_PATTERN.sub("", raw_text).strip()
    if not answer:
        answer = "Insufficient context to answer from uploaded documents."
    return reasoning, answer


@router.post(
    "",
    response_model=QueryResponse,
    responses={
        400: {"description": "Invalid query payload"},
        403: {"description": "Forbidden"},
        409: {"description": "Team has no agents configured"},
        503: {
            "description": (
                "Query processing temporarily unavailable during retrieval, "
                "persistence, or answer generation."
            )
        },
    },
)
async def run_query(payload: QueryRequest, request: Request, auth_user: AuthUser = Depends(get_current_user)) -> QueryResponse:
    settings = get_settings()
    request_id = getattr(request.state, "request_id", "unknown")
    query_start = time.perf_counter()
    observer = observability.get_observability()
    logger.info(
        "query_request_started",
        extra={
            "request_id": request_id,
            "session_id": str(payload.session_id),
            "user_id": auth_user.user_id,
            "top_k": payload.top_k,
        },
    )
    observer.record_trace_event(
        event_name="query_request_started",
        request_id=request_id,
        user_id=auth_user.user_id,
        route=QUERY_ROUTE_PREFIX,
        component="query_router",
        metadata={
            "session_id": str(payload.session_id),
            "query": payload.query,
            "top_k": payload.top_k,
        },
    )

    selected_top_k = payload.top_k or settings.top_k
    try:
        repository = SupabaseRepository()
        observer.record_trace_event(
            event_name="query_repository_ready",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="supabase",
            metadata={"session_id": str(payload.session_id)},
        )
        session = repository.get_session(user_id=auth_user.user_id, session_id=str(payload.session_id))
        if session is None:
            session = repository.create_session(
                user_id=auth_user.user_id,
                session_id=str(payload.session_id),
                title="Chat session",
            )
            observer.record_trace_event(
                event_name="query_session_created",
                request_id=request_id,
                user_id=auth_user.user_id,
                route=QUERY_ROUTE_PREFIX,
                component="supabase",
                metadata={"session_id": str(payload.session_id)},
            )
        session_team_id = str(session.get("team_id", "")).strip()
        if not session_team_id:
            raise HTTPException(status_code=503, detail="Session team is missing")
        if not repository.team_has_agents(user_id=auth_user.user_id, team_id=session_team_id):
            raise HTTPException(status_code=409, detail="Team must have at least one agent before chat")

        retrieval_start = time.perf_counter()
        rows = retrieve_chunks(
            query=payload.query,
            user_id=auth_user.user_id,
            top_k=selected_top_k,
        )
        sources = format_sources(rows)
        observer.record_trace_event(
            event_name="query_retrieval_finished",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="retriever",
            duration_ms=int((time.perf_counter() - retrieval_start) * 1000),
            metadata={"query": payload.query, "top_k": selected_top_k, "rows": rows, "sources": sources},
        )
    except ValueError as error:
        logger.warning("query_request_validation_failed", extra={"request_id": request_id, "error": str(error)})
        observer.record_trace_event(
            event_name="query_request_validation_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="query_router",
            level="WARNING",
            status="failed",
            metadata={"query": payload.query, "top_k": selected_top_k},
            error=error,
        )
        raise HTTPException(status_code=400, detail="Invalid query payload") from error
    except PermissionError as error:
        observer.record_trace_event(
            event_name="query_request_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="query_router",
            level="WARNING",
            status="failed",
            metadata={"session_id": str(payload.session_id)},
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("query_request_retrieval_failed", extra={"request_id": request_id, "user_id": auth_user.user_id})
        observer.record_trace_event(
            event_name="query_request_retrieval_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="query_router",
            level="ERROR",
            status="failed",
            metadata={"session_id": str(payload.session_id), "query": payload.query},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Retrieval temporarily unavailable") from error

    if not sources:
        final_answer = (
            "Insufficient context to answer from uploaded documents. "
            "Please upload more relevant files or rephrase the query."
        )
        total_response_ms = int((time.perf_counter() - query_start) * 1000)
        try:
            query_row = repository.save_query(
                session_id=str(payload.session_id),
                query_text=payload.query,
                final_answer=final_answer,
                scorecard=None,
                response_time_ms=total_response_ms,
                user_id=auth_user.user_id,
            )
            observer.record_trace_event(
                event_name="query_persistence_finished",
                request_id=request_id,
                user_id=auth_user.user_id,
                route=QUERY_ROUTE_PREFIX,
                component="supabase",
                status="saved",
                metadata={"query_id": query_row["id"], "session_id": str(payload.session_id), "response_time_ms": total_response_ms},
            )
        except PermissionError as error:
            observer.record_trace_event(
                event_name="query_persistence_permission_failed",
                request_id=request_id,
                user_id=auth_user.user_id,
                route=QUERY_ROUTE_PREFIX,
                component="supabase",
                level="WARNING",
                status="failed",
                error=error,
            )
            raise HTTPException(status_code=403, detail=str(error)) from error
        except Exception as error:
            logger.exception("query_request_persistence_failed", extra={"request_id": request_id, "session_id": str(payload.session_id)})
            observer.record_trace_event(
                event_name="query_request_persistence_failed",
                request_id=request_id,
                user_id=auth_user.user_id,
                route=QUERY_ROUTE_PREFIX,
                component="supabase",
                level="ERROR",
                status="failed",
                metadata={"session_id": str(payload.session_id)},
                error=error,
            )
            raise HTTPException(status_code=503, detail="Query persistence temporarily unavailable") from error

        observer.record_trace_event(
            event_name="query_insufficient_context",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="query_router",
            status="insufficient_context",
            duration_ms=total_response_ms,
            metadata={"query": payload.query, "top_k": selected_top_k},
        )
        return QueryResponse(
            query_id=query_row["id"],
            query=payload.query,
            final_answer=final_answer,
            sources=[],
            retrieval_count=0,
            insufficient_context=True,
            model_version=settings.model_version,
            retrieval_metadata=RetrievalMetadata(
                embedding_model_version=settings.embedanything_model,
                index_version=settings.index_version,
                top_k=selected_top_k,
            ),
        )

    try:
        generation_start = time.perf_counter()
        generated_text = generate_answer(query=payload.query, sources=sources)
        reasoning, final_answer = _split_reasoning_and_answer(generated_text)
        observer.record_trace_event(
            event_name="query_generation_finished",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="generator",
            duration_ms=int((time.perf_counter() - generation_start) * 1000),
            metadata={"query": payload.query, "sources": sources, "final_answer": final_answer, "reasoning": reasoning},
        )
    except Exception as error:
        logger.exception("query_request_generation_failed", extra={"request_id": request_id})
        observer.record_trace_event(
            event_name="query_request_generation_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="generator",
            level="ERROR",
            status="failed",
            metadata={"query": payload.query, "sources": sources},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Answer generation temporarily unavailable") from error

    total_response_ms = int((time.perf_counter() - query_start) * 1000)
    try:
        query_row = repository.save_query(
            session_id=str(payload.session_id),
            query_text=payload.query,
            final_answer=final_answer,
            scorecard=None,
            response_time_ms=total_response_ms,
            user_id=auth_user.user_id,
        )
        observer.record_trace_event(
            event_name="query_persistence_finished",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="supabase",
            status="saved",
            metadata={"query_id": query_row["id"], "session_id": str(payload.session_id), "response_time_ms": total_response_ms},
        )
    except PermissionError as error:
        observer.record_trace_event(
            event_name="query_persistence_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="supabase",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("query_request_persistence_failed", extra={"request_id": request_id, "session_id": str(payload.session_id)})
        observer.record_trace_event(
            event_name="query_request_persistence_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=QUERY_ROUTE_PREFIX,
            component="supabase",
            level="ERROR",
            status="failed",
            metadata={"session_id": str(payload.session_id)},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Query persistence temporarily unavailable") from error

    observer.record_trace_event(
        event_name="query_request_finished",
        request_id=request_id,
        user_id=auth_user.user_id,
        route=QUERY_ROUTE_PREFIX,
        component="query_router",
        status="success",
        duration_ms=total_response_ms,
        metadata={"query_id": query_row["id"], "retrieval_count": len(sources), "final_answer": final_answer},
    )

    return QueryResponse(
        query_id=query_row["id"],
        query=payload.query,
        final_answer=final_answer,
        reasoning=reasoning,
        sources=sources,
        retrieval_count=len(sources),
        insufficient_context=False,
        model_version=settings.model_version,
        retrieval_metadata=RetrievalMetadata(
            embedding_model_version=settings.embedanything_model,
            index_version=settings.index_version,
            top_k=selected_top_k,
        ),
    )


@router.get(
    "/history",
    response_model=list[QueryHistoryItem],
    responses={
        403: {"description": "Forbidden"},
        503: {"description": "Query history temporarily unavailable"},
    },
)
async def query_history(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
    session_id: UUID = Query(...),
    limit: int = Query(get_settings().query_history_limit_default, ge=1, le=get_settings().query_history_limit_max),
) -> list[QueryHistoryItem]:
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        rows = repository.list_queries(session_id=str(session_id), user_id=auth_user.user_id, limit=limit)
        observer.record_trace_event(
            event_name="query_history_loaded",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=f"{QUERY_ROUTE_PREFIX}/history",
            component="query_router",
            metadata={"session_id": str(session_id), "limit": limit, "row_count": len(rows)},
        )
    except PermissionError as error:
        observer.record_trace_event(
            event_name="query_history_permission_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=f"{QUERY_ROUTE_PREFIX}/history",
            component="query_router",
            level="WARNING",
            status="failed",
            error=error,
        )
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Exception as error:
        logger.exception("query_history_request_failed", extra={"request_id": request_id, "session_id": str(session_id)})
        observer.record_trace_event(
            event_name="query_history_request_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=f"{QUERY_ROUTE_PREFIX}/history",
            component="query_router",
            level="ERROR",
            status="failed",
            metadata={"session_id": str(session_id)},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Query history temporarily unavailable") from error
    return [QueryHistoryItem(**row) for row in rows]


@router.get(
    "/history/recent",
    response_model=list[QueryHistoryItem],
    responses={
        503: {"description": "Recent query history temporarily unavailable"},
    },
)
async def query_history_recent(
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
    limit: int = Query(get_settings().query_history_limit_default, ge=1, le=get_settings().query_history_limit_max),
) -> list[QueryHistoryItem]:
    request_id = getattr(request.state, "request_id", "unknown")
    observer = observability.get_observability()
    try:
        repository = SupabaseRepository()
        rows = repository.list_recent_queries(user_id=auth_user.user_id, limit=limit)
        observer.record_trace_event(
            event_name="query_history_recent_loaded",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=f"{QUERY_ROUTE_PREFIX}/history/recent",
            component="query_router",
            metadata={"limit": limit, "row_count": len(rows)},
        )
    except Exception as error:
        logger.exception("query_history_recent_request_failed", extra={"request_id": request_id})
        observer.record_trace_event(
            event_name="query_history_recent_request_failed",
            request_id=request_id,
            user_id=auth_user.user_id,
            route=f"{QUERY_ROUTE_PREFIX}/history/recent",
            component="query_router",
            level="ERROR",
            status="failed",
            metadata={"limit": limit},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Recent query history temporarily unavailable") from error
    return [QueryHistoryItem(**row) for row in rows]
