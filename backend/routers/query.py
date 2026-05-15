from __future__ import annotations
"""Query endpoints for retrieval, orchestration, and history access."""

import logging
import re
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

import observability
from core.auth import AuthUser, get_current_user
from core.config import get_settings
from db.supabase import SupabaseRepository
from llms.router import LLMRouter
from rag.orchestrator import (
    OrchestrationConfigError,
    OrchestrationExecutionError,
    OrchestrationResult,
    Orchestrator,
    QueryContext,
)
from rag.retriever import format_sources, retrieve_chunks
from rag.scorecard import evaluate_scorecard


QUERY_ROUTE_PREFIX = "/query"

router = APIRouter(prefix=QUERY_ROUTE_PREFIX, tags=["query"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Inbound payload for running a query within a session/team."""
    query: str = Field(min_length=1, max_length=get_settings().max_query_length)
    session_id: UUID
    team_id: UUID
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceItem(BaseModel):
    """Retrieved source preview returned with query responses."""
    document_id: str
    filename: str
    chunk_index: int
    content_preview: str
    score: float


class RetrievalMetadata(BaseModel):
    """Retrieval configuration metadata attached to query responses."""
    embedding_model_version: str
    index_version: str
    top_k: int


class CitationItem(BaseModel):
    """Citation reference to a retrieved source chunk."""
    document_id: str
    filename: str
    chunk_index: int
    source_index: int


class AgentTraceItem(BaseModel):
    """Per-agent execution trace included in query responses."""
    id: str | None = None
    agent_id: str | None = None
    agent_name: str
    agent_role: str
    model_provider: str
    model_name: str
    status: str
    latency_ms: int | None = None
    output: str
    error: str | None = None
    citations: list[dict[str, Any]]


class ScorecardResponse(BaseModel):
    """Deterministic quality scorecard returned for a query."""
    overall_quality: int | None = None
    citation_accuracy: int | None = None
    insight_depth: int | None = None
    model_contribution_breakdown: dict[str, Any]
    notes: str | None = None


class QueryResponse(BaseModel):
    """Primary response model for `/query` execution."""
    query_id: str | None = None
    query: str
    final_answer: str
    reasoning: str | None = None
    sources: list[SourceItem]
    citations: list[CitationItem] = []
    traces: list[AgentTraceItem] = []
    scorecard: ScorecardResponse | None = None
    retrieval_count: int
    insufficient_context: bool
    model_version: str
    retrieval_metadata: RetrievalMetadata


class QueryHistoryItem(BaseModel):
    """Compact query-history row for list endpoints."""
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
    """Split optional `<think>` content from final user-facing answer text."""
    match = _THINK_TAG_PATTERN.search(raw_text or "")
    if not match:
        return None, (raw_text or "").strip()

    reasoning = match.group(1).strip() or None
    answer = _THINK_TAG_PATTERN.sub("", raw_text).strip()
    if not answer:
        answer = "Insufficient context to answer from uploaded documents."
    return reasoning, answer


def _scorecard_response(scorecard: dict[str, Any]) -> ScorecardResponse:
    """Normalize internal scorecard dict into response model."""
    return ScorecardResponse(
        overall_quality=scorecard.get("overall_quality"),
        citation_accuracy=scorecard.get("citation_accuracy"),
        insight_depth=scorecard.get("insight_depth"),
        model_contribution_breakdown=dict(scorecard.get("model_contribution_breakdown") or {}),
        notes=scorecard.get("notes"),
    )


def _trace_items(result: OrchestrationResult) -> list[AgentTraceItem]:
    """Project orchestrator traces into API response trace models."""
    return [
        AgentTraceItem(
            id=trace.id,
            agent_id=trace.agent_id,
            agent_name=trace.agent_name,
            agent_role=trace.agent_role,
            model_provider=trace.model_provider,
            model_name=trace.model_name,
            status=trace.status,
            latency_ms=trace.latency_ms,
            output=trace.output,
            error=trace.error,
            citations=trace.citations,
        )
        for trace in result.traces
    ]


def _serialize_json_list(items: list[Any]) -> list[dict[str, Any]]:
    """Serialize mixed Pydantic/dict collections to plain JSON-serializable dicts."""
    serialized: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "model_dump"):
            serialized.append(item.model_dump())
        else:
            serialized.append(dict(item))
    return serialized


def _documents_indexed_without_hits(documents: list[dict[str, Any]]) -> bool:
    """Detect when docs exist but retrieval returned no chunks from the active index."""
    if not documents:
        return False
    return any(str(document.get("index_status", "")).strip().lower() == "indexed" for document in documents)


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
    """Execute retrieval + orchestration and persist a query result."""
    settings = get_settings()
    request_id = getattr(request.state, "request_id", "unknown")
    query_start = time.perf_counter()
    observer = observability.get_observability()
    logger.info(
        "query_request_started",
        extra={
            "request_id": request_id,
            "session_id": str(payload.session_id),
            "team_id": str(payload.team_id),
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
            "team_id": str(payload.team_id),
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
            metadata={"session_id": str(payload.session_id), "team_id": str(payload.team_id)},
        )
        requested_team_id = str(payload.team_id)
        team = repository.get_team(user_id=auth_user.user_id, team_id=requested_team_id)
        if team is None:
            raise HTTPException(status_code=403, detail="Selected team is not accessible for this user")
        session = repository.get_session(user_id=auth_user.user_id, session_id=str(payload.session_id))
        if session is None:
            session = repository.create_session(
                user_id=auth_user.user_id,
                session_id=str(payload.session_id),
                team_id=requested_team_id,
                title="Chat session",
            )
            observer.record_trace_event(
                event_name="query_session_created",
                request_id=request_id,
                user_id=auth_user.user_id,
                route=QUERY_ROUTE_PREFIX,
                component="supabase",
                metadata={"session_id": str(payload.session_id), "team_id": requested_team_id},
            )
        session_team_id = str(session.get("team_id", "")).strip()
        if not session_team_id:
            raise HTTPException(status_code=503, detail="Session team is missing")
        if session_team_id != requested_team_id:
            raise HTTPException(status_code=409, detail="Session belongs to a different team than the requested team")
        agents = repository.list_agents(user_id=auth_user.user_id, team_id=requested_team_id)
        if not agents:
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
            metadata={"session_id": str(payload.session_id), "team_id": str(payload.team_id)},
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
            metadata={"session_id": str(payload.session_id), "team_id": str(payload.team_id), "query": payload.query},
            error=error,
        )
        raise HTTPException(status_code=503, detail="Retrieval temporarily unavailable") from error

    if not sources:
        try:
            documents = repository.list_documents(user_id=auth_user.user_id)
        except Exception:
            documents = []
        if _documents_indexed_without_hits(documents):
            final_answer = (
                "No retrieval results were returned from the active vector index, even though documents are indexed. "
                "Please re-index or re-upload documents for this workspace."
            )
        else:
            final_answer = (
                "Insufficient context to answer from uploaded documents. "
                "Please upload more relevant files or rephrase the query."
            )
        retrieval_metadata = {
            "embedding_model_version": settings.embedanything_model,
            "index_version": settings.index_version,
            "top_k": selected_top_k,
        }
        scorecard = evaluate_scorecard(
            final_answer=final_answer,
            sources=[],
            citations=[],
            traces=[],
            retrieval_metadata=retrieval_metadata,
        )
        total_response_ms = int((time.perf_counter() - query_start) * 1000)
        try:
            query_row = repository.create_query(
                session_id=str(payload.session_id),
                query_text=payload.query,
                user_id=auth_user.user_id,
                response_time_ms=None,
            )
            repository.create_message(
                user_id=auth_user.user_id,
                session_id=str(payload.session_id),
                role="user",
                content=payload.query,
                metadata={"query_id": query_row["id"]},
            )
            repository.save_scorecard(
                user_id=auth_user.user_id,
                session_id=str(payload.session_id),
                query_id=query_row["id"],
                **scorecard,
            )
            query_row = repository.update_query_result(
                user_id=auth_user.user_id,
                query_id=query_row["id"],
                final_answer=final_answer,
                scorecard=scorecard,
                response_time_ms=total_response_ms,
                sources=[],
                citations=[],
                retrieval_metadata=retrieval_metadata,
                model_version=settings.model_version,
                insufficient_context=True,
            )
            repository.create_message(
                user_id=auth_user.user_id,
                session_id=str(payload.session_id),
                role="assistant",
                content=final_answer,
                metadata={"query_id": query_row["id"]},
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
            citations=[],
            traces=[],
            scorecard=_scorecard_response(scorecard),
            retrieval_count=0,
            insufficient_context=True,
            model_version=settings.model_version,
            retrieval_metadata=RetrievalMetadata(
                embedding_model_version=settings.embedanything_model,
                index_version=settings.index_version,
                top_k=selected_top_k,
            ),
        )

    total_response_ms = int((time.perf_counter() - query_start) * 1000)
    try:
        query_row = repository.create_query(
            session_id=str(payload.session_id),
            query_text=payload.query,
            user_id=auth_user.user_id,
            response_time_ms=None,
        )
        repository.create_message(
            user_id=auth_user.user_id,
            session_id=str(payload.session_id),
            role="user",
            content=payload.query,
            metadata={"query_id": query_row["id"]},
        )
        orchestrator = Orchestrator(
            repository=repository,
            llm_router=LLMRouter(),
            observer=observer,
        )
        result = orchestrator.run(
            QueryContext(
                user_id=auth_user.user_id,
                session_id=str(payload.session_id),
                query_id=str(query_row["id"]),
                query=payload.query,
                request_id=request_id,
            ),
            team=team,
            agents=agents,
            retrieved_context=sources,
        )
        reasoning, final_answer = _split_reasoning_and_answer(result.final_answer)
        query_row = repository.update_query_result(
            user_id=auth_user.user_id,
            query_id=str(query_row["id"]),
            final_answer=final_answer,
            scorecard=result.scorecard,
            response_time_ms=int((time.perf_counter() - query_start) * 1000),
            sources=_serialize_json_list(sources),
            citations=_serialize_json_list(result.citations),
            retrieval_metadata={
                "embedding_model_version": settings.embedanything_model,
                "index_version": settings.index_version,
                "top_k": selected_top_k,
            },
            model_version=settings.model_version,
            insufficient_context=False,
        )
        repository.create_message(
            user_id=auth_user.user_id,
            session_id=str(payload.session_id),
            role="assistant",
            content=final_answer,
            metadata={"query_id": query_row["id"]},
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
    except OrchestrationConfigError as error:
        total_response_ms = int((time.perf_counter() - query_start) * 1000)
        try:
            repository.update_query_result(
                user_id=auth_user.user_id,
                query_id=str(query_row["id"]),
                final_answer=str(error),
                scorecard={"overall_quality": 3, "citation_accuracy": 3, "insight_depth": 3},
                response_time_ms=total_response_ms,
            )
        except Exception:
            logger.exception("query_orchestration_config_failure_persistence_failed", extra={"request_id": request_id})
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OrchestrationExecutionError as error:
        total_response_ms = int((time.perf_counter() - query_start) * 1000)
        try:
            repository.update_query_result(
                user_id=auth_user.user_id,
                query_id=str(query_row["id"]),
                final_answer=str(error),
                scorecard={"overall_quality": 3, "citation_accuracy": 3, "insight_depth": 3},
                response_time_ms=total_response_ms,
            )
        except Exception:
            logger.exception("query_orchestration_execution_failure_persistence_failed", extra={"request_id": request_id})
        raise HTTPException(status_code=503, detail=str(error)) from error
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
        citations=result.citations,
        traces=_trace_items(result),
        scorecard=_scorecard_response(result.scorecard),
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
    """Return persisted query history for a specific session."""
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
    """Return recent query history across the authenticated user scope."""
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
