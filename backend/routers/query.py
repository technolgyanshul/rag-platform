from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from db.supabase import SupabaseRepository
from orchestration.graph import run_graph
from rag.retriever import format_sources, retrieve_chunks


router = APIRouter(prefix="/query", tags=["query"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    team_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class QueryResponse(BaseModel):
    query_id: str | None = None
    query: str
    final_answer: str
    sources: list[dict[str, Any]]
    scorecard: dict[str, Any] | None = None
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_count: int
    insufficient_context: bool


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
def run_query(payload: QueryRequest) -> QueryResponse:
    request_id = str(uuid4())
    query_start = time.perf_counter()
    logger.info(
        "query_request_started",
        extra={"request_id": request_id, "team_id": payload.team_id, "session_id": payload.session_id, "top_k": payload.top_k},
    )
    rows = retrieve_chunks(query=payload.query, team_id=payload.team_id, top_k=payload.top_k)
    sources = format_sources(rows)

    if not sources:
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
        )

    graph_result = run_graph(query=payload.query, sources=sources)
    repository = SupabaseRepository()
    total_response_ms = int((time.perf_counter() - query_start) * 1000)
    query_row = repository.save_query(
        session_id=payload.session_id,
        query_text=payload.query,
        final_answer=graph_result["final_answer"],
        scorecard=graph_result["scorecard"],
        response_time_ms=total_response_ms,
    )
    repository.save_agent_traces(query_id=query_row["id"], traces=graph_result["agent_trace"])

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
    )


@router.get("/history", response_model=list[QueryHistoryItem])
def query_history(session_id: str, limit: int = 50) -> list[QueryHistoryItem]:
    repository = SupabaseRepository()
    rows = repository.list_queries(session_id=session_id, limit=limit)
    return [QueryHistoryItem(**row) for row in rows]
