from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Query
from fastapi import HTTPException
from fastapi import Request
from pydantic import BaseModel, Field

from core.config import get_settings
from db.supabase import SupabaseRepository
from orchestration.graph import run_graph
from rag.retriever import format_sources, retrieve_chunks


router = APIRouter(prefix="/query", tags=["query"])
logger = logging.getLogger(__name__)


def _log_session_event(
    repository: SupabaseRepository,
    *,
    session_id: str,
    team_id: str,
    request_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    try:
        repository.save_session_log(
            session_id=session_id,
            team_id=team_id,
            event_type=event_type,
            payload=payload,
            request_id=request_id,
        )
    except Exception:
        logger.exception(
            "query_session_event_log_failed",
            extra={"request_id": request_id, "session_id": session_id, "team_id": team_id, "event_type": event_type},
        )


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=get_settings().max_query_length)
    team_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
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
    sources: list[SourceItem]
    scorecard: dict[str, Any] | None = None
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
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


@router.post("", response_model=QueryResponse)
def run_query(payload: QueryRequest, request: Request) -> QueryResponse:
    settings = get_settings()
    repository = SupabaseRepository()
    request_id = getattr(request.state, "request_id", "unknown")
    query_start = time.perf_counter()
    _log_session_event(
        repository,
        session_id=payload.session_id,
        team_id=payload.team_id,
        request_id=request_id,
        event_type="query_started",
        payload={"top_k": payload.top_k or settings.top_k, "query": payload.query},
    )
    logger.info(
        "query_request_started",
        extra={"request_id": request_id, "team_id": payload.team_id, "session_id": payload.session_id, "top_k": payload.top_k},
    )
    selected_top_k = payload.top_k or settings.top_k
    try:
        rows = retrieve_chunks(query=payload.query, team_id=payload.team_id, top_k=selected_top_k)
        sources = format_sources(rows)
    except ValueError as error:
        logger.warning("query_request_validation_failed", extra={"request_id": request_id, "error": str(error)})
        raise HTTPException(status_code=400, detail="Invalid query payload") from error
    except Exception as error:
        logger.exception("query_request_retrieval_failed", extra={"request_id": request_id, "team_id": payload.team_id})
        raise HTTPException(status_code=503, detail="Retrieval temporarily unavailable") from error

    if not sources:
        _log_session_event(
            repository,
            session_id=payload.session_id,
            team_id=payload.team_id,
            request_id=request_id,
            event_type="query_completed",
            payload={
                "query": payload.query,
                "retrieval_count": 0,
                "insufficient_context": True,
                "latency_ms": int((time.perf_counter() - query_start) * 1000),
            },
        )
        logger.info(
            "query_request_no_sources",
            extra={
                "request_id": request_id,
                "team_id": payload.team_id,
                "session_id": payload.session_id,
                "retrieval_count": 0,
                "latency_ms": int((time.perf_counter() - query_start) * 1000),
            },
        )
        return QueryResponse(
            query=payload.query,
            final_answer=(
                "Insufficient context to answer from uploaded documents. "
                "Please upload more relevant files or rephrase the query."
            ),
            sources=[],
            scorecard=None,
            agent_trace=[],
            retrieval_count=0,
            insufficient_context=True,
            model_version=settings.model_version,
            retrieval_metadata=RetrievalMetadata(
                embedding_model_version=settings.embedding_model_version,
                index_version=settings.index_version,
                top_k=selected_top_k,
            ),
        )

    try:
        graph_result = run_graph(query=payload.query, sources=sources)
    except Exception as error:
        logger.exception("query_request_orchestration_failed", extra={"request_id": request_id})
        raise HTTPException(status_code=503, detail="Answer generation temporarily unavailable") from error

    total_response_ms = int((time.perf_counter() - query_start) * 1000)
    try:
        query_row = repository.save_query(
            session_id=payload.session_id,
            query_text=payload.query,
            final_answer=graph_result["final_answer"],
            scorecard=graph_result["scorecard"],
            response_time_ms=total_response_ms,
        )
        repository.save_agent_traces(query_id=query_row["id"], traces=graph_result["agent_trace"])
        _log_session_event(
            repository,
            session_id=payload.session_id,
            team_id=payload.team_id,
            request_id=request_id,
            event_type="query_completed",
            payload={
                "query_id": query_row["id"],
                "query": payload.query,
                "retrieval_count": len(sources),
                "insufficient_context": False,
                "latency_ms": total_response_ms,
            },
        )
    except Exception as error:
        _log_session_event(
            repository,
            session_id=payload.session_id,
            team_id=payload.team_id,
            request_id=request_id,
            event_type="query_persistence_failed",
            payload={"error": str(error), "query": payload.query},
        )
        logger.exception("query_request_persistence_failed", extra={"request_id": request_id, "session_id": payload.session_id})
        raise HTTPException(status_code=503, detail="Query persistence temporarily unavailable") from error

    logger.info(
        "query_request_completed",
        extra={
            "request_id": request_id,
            "query_id": query_row["id"],
            "team_id": payload.team_id,
            "session_id": payload.session_id,
            "retrieval_count": len(sources),
            "latency_ms": total_response_ms,
        },
    )

    return QueryResponse(
        query_id=query_row["id"],
        query=payload.query,
        final_answer=graph_result["final_answer"],
        sources=sources,
        scorecard=graph_result["scorecard"],
        agent_trace=graph_result["agent_trace"],
        retrieval_count=len(sources),
        insufficient_context=False,
        model_version=settings.model_version,
        retrieval_metadata=RetrievalMetadata(
            embedding_model_version=settings.embedding_model_version,
            index_version=settings.index_version,
            top_k=selected_top_k,
        ),
    )


@router.get("/history", response_model=list[QueryHistoryItem])
def query_history(
    request: Request,
    session_id: str = Query(..., min_length=1, max_length=128),
    limit: int = Query(get_settings().query_history_limit_default, ge=1, le=get_settings().query_history_limit_max),
) -> list[QueryHistoryItem]:
    request_id = getattr(request.state, "request_id", "unknown")
    repository = SupabaseRepository()
    try:
        rows = repository.list_queries(session_id=session_id, limit=limit)
    except Exception as error:
        logger.exception("query_history_request_failed", extra={"request_id": request_id, "session_id": session_id})
        raise HTTPException(status_code=503, detail="Query history temporarily unavailable") from error
    return [QueryHistoryItem(**row) for row in rows]
