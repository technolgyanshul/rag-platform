from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from orchestration.graph import run_graph
from rag.retriever import format_sources, retrieve_chunks


router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    team_id: str = Field(min_length=1)
    session_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class QueryResponse(BaseModel):
    query: str
    final_answer: str
    sources: list[dict[str, Any]]
    scorecard: dict[str, Any] | None = None
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_count: int
    insufficient_context: bool


@router.post("", response_model=QueryResponse)
def run_query(payload: QueryRequest) -> QueryResponse:
    rows = retrieve_chunks(query=payload.query, team_id=payload.team_id, top_k=payload.top_k)
    sources = format_sources(rows)

    if not sources:
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
    return QueryResponse(
        query=payload.query,
        final_answer=graph_result["final_answer"],
        sources=sources,
        scorecard=graph_result["scorecard"],
        agent_trace=graph_result["agent_trace"],
        retrieval_count=len(sources),
        insufficient_context=False,
    )
