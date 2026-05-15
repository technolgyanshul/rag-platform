from __future__ import annotations
"""Deterministic scoring utilities for RAG answer quality and trace contribution."""

from typing import Any


OVERALL_BASE_SCORE = 5
OVERALL_CITATION_BONUS = 1
OVERALL_AGENT_DIVERSITY_BONUS = 1
OVERALL_ANSWER_LENGTH_BONUS = 1
OVERALL_RETRIEVED_CONTEXT_BONUS = 1
ANSWER_LENGTH_QUALITY_THRESHOLD = 220

CITATION_STRONG_SCORE = 8
CITATION_WEAK_SCORE = 5
CITATION_MISSING_SCORE = 2

INSIGHT_BASE_SCORE = 3
INSIGHT_MEDIUM_ANSWER_THRESHOLD = 120
INSIGHT_MEDIUM_ANSWER_BONUS = 1
INSIGHT_LONG_ANSWER_THRESHOLD = 220
INSIGHT_LONG_ANSWER_BONUS = 2
INSIGHT_DIVERSITY_BONUS_PER_EXTRA_AGENT = 1
INSIGHT_DIVERSITY_BONUS_CAP = 2
INSIGHT_CRITIC_BONUS = 1
INSIGHT_SYNTHESIZER_BONUS = 2

MAX_SCORE = 10


def evaluate_scorecard(
    final_answer: str,
    sources: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    traces: list[Any],
    retrieval_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Compute the response scorecard from answer, sources, citations, and traces."""
    answer = final_answer or ""
    source_items = sources or []
    citation_items = citations or []
    trace_items = traces or []
    contributing_traces = [_trace for _trace in trace_items if _trace_contributed(_trace)]

    overall_quality = OVERALL_BASE_SCORE
    if citation_items:
        overall_quality += OVERALL_CITATION_BONUS
    if len(contributing_traces) >= 2:
        overall_quality += OVERALL_AGENT_DIVERSITY_BONUS
    if len(answer) >= ANSWER_LENGTH_QUALITY_THRESHOLD:
        overall_quality += OVERALL_ANSWER_LENGTH_BONUS
    if source_items:
        overall_quality += OVERALL_RETRIEVED_CONTEXT_BONUS

    citation_accuracy = _citation_accuracy(source_items, citation_items)
    insight_depth = _insight_depth(answer, contributing_traces)
    breakdown = _model_contribution_breakdown(trace_items)

    return {
        "overall_quality": min(overall_quality, MAX_SCORE),
        "citation_accuracy": citation_accuracy,
        "insight_depth": insight_depth,
        "model_contribution_breakdown": breakdown,
        "notes": (
            "Deterministic scorecard: "
            f"{len(source_items)} sources, {len(citation_items)} citations, "
            f"{len(contributing_traces)} contributing agents, "
            f"top_k={retrieval_metadata.get('top_k') if retrieval_metadata else None}."
        ),
    }


def _citation_accuracy(sources: list[dict[str, Any]], citations: list[dict[str, Any]]) -> int:
    """Return citation accuracy score from strong/weak/missing evidence matches."""
    if not citations:
        return CITATION_MISSING_SCORE
    if any(_citation_matches_source(citation, sources) for citation in citations):
        return CITATION_STRONG_SCORE
    if sources:
        return CITATION_WEAK_SCORE
    return CITATION_MISSING_SCORE


def _citation_matches_source(citation: dict[str, Any], sources: list[dict[str, Any]]) -> bool:
    """Check whether a citation maps to at least one retrieved source chunk."""
    source_index = _safe_int(citation.get("source_index"))
    if source_index is not None and 1 <= source_index <= len(sources):
        indexed_source = sources[source_index - 1]
        if _has_chunk_identity(citation):
            return _same_chunk(citation, indexed_source)
        return True

    return any(_same_chunk(citation, source) for source in sources)


def _same_chunk(citation: dict[str, Any], source: dict[str, Any]) -> bool:
    """Compare citation and source identity using document id + chunk index."""
    citation_document_id = str(citation.get("document_id") or "").strip()
    source_document_id = str(source.get("document_id") or "").strip()
    citation_chunk_index = _safe_int(citation.get("chunk_index"))
    source_chunk_index = _safe_int(source.get("chunk_index"))
    return (
        citation_document_id != ""
        and source_document_id != ""
        and citation_document_id == source_document_id
        and citation_chunk_index is not None
        and source_chunk_index is not None
        and citation_chunk_index == source_chunk_index
    )


def _has_chunk_identity(citation: dict[str, Any]) -> bool:
    """Return whether citation has enough identity fields for strict matching."""
    return bool(str(citation.get("document_id") or "").strip()) and _safe_int(citation.get("chunk_index")) is not None


def _insight_depth(final_answer: str, contributing_traces: list[Any]) -> int:
    """Score answer depth using length, role diversity, and role bonuses."""
    score = INSIGHT_BASE_SCORE
    answer_length = len(final_answer or "")
    if answer_length >= INSIGHT_LONG_ANSWER_THRESHOLD:
        score += INSIGHT_LONG_ANSWER_BONUS
    elif answer_length >= INSIGHT_MEDIUM_ANSWER_THRESHOLD:
        score += INSIGHT_MEDIUM_ANSWER_BONUS

    score += min(
        INSIGHT_DIVERSITY_BONUS_CAP,
        max(0, len(contributing_traces) - 1) * INSIGHT_DIVERSITY_BONUS_PER_EXTRA_AGENT,
    )

    contributed_roles = {_trace_value(trace, "agent_role").strip().lower() for trace in contributing_traces}
    if "critic" in contributed_roles or "reviewer" in contributed_roles or "judge" in contributed_roles:
        score += INSIGHT_CRITIC_BONUS
    if "synthesizer" in contributed_roles:
        score += INSIGHT_SYNTHESIZER_BONUS

    return min(score, MAX_SCORE)


def _model_contribution_breakdown(traces: list[Any]) -> dict[str, dict[str, Any]]:
    """Build per-agent contribution metadata for observability and UI display."""
    breakdown: dict[str, dict[str, Any]] = {}
    seen_names: dict[str, int] = {}
    for trace in traces:
        name = _trace_value(trace, "agent_name") or "Agent"
        seen_names[name] = seen_names.get(name, 0) + 1
        key = name if seen_names[name] == 1 else f"{name} #{seen_names[name]}"
        output = _trace_value(trace, "output")
        citations = _trace_raw_value(trace, "citations") or []
        breakdown[key] = {
            "agent_role": _trace_value(trace, "agent_role") or "agent",
            "model_provider": _trace_value(trace, "model_provider"),
            "model_name": _trace_value(trace, "model_name"),
            "status": _trace_value(trace, "status"),
            "contributed": _trace_contributed(trace),
            "output_chars": len(output),
            "citation_count": len(citations) if isinstance(citations, list) else 0,
        }
    return breakdown


def _trace_contributed(trace: Any) -> bool:
    """Return whether a trace produced non-empty output with completed status."""
    return _trace_value(trace, "status").strip().lower() == "completed" and bool(_trace_value(trace, "output").strip())


def _trace_value(trace: Any, key: str) -> str:
    """Read a stringified trace field from dict- or object-like traces."""
    value = _trace_raw_value(trace, key)
    return str(value or "")


def _trace_raw_value(trace: Any, key: str) -> Any:
    """Read a raw trace field from dict- or object-like traces."""
    if isinstance(trace, dict):
        return trace.get(key)
    return getattr(trace, key, None)


def _safe_int(value: Any) -> int | None:
    """Best-effort integer coercion that returns `None` on invalid inputs."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_scorecard(
    final_answer: str,
    sources: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    traces: list[Any],
    retrieval_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Backward-compatible alias for `evaluate_scorecard`."""
    # Backward-compatible alias used by existing call sites/tests.
    return evaluate_scorecard(
        final_answer=final_answer,
        sources=sources,
        citations=citations,
        traces=traces,
        retrieval_metadata=retrieval_metadata,
    )
