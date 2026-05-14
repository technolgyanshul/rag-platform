from __future__ import annotations

from types import SimpleNamespace

from rag.scorecard import (
    ANSWER_LENGTH_QUALITY_THRESHOLD,
    INSIGHT_BASE_SCORE,
    INSIGHT_CRITIC_BONUS,
    INSIGHT_DIVERSITY_BONUS_CAP,
    INSIGHT_SYNTHESIZER_BONUS,
    build_scorecard,
)


def _source(document_id: str = "doc-1", chunk_index: int = 0) -> dict[str, object]:
    return {
        "document_id": document_id,
        "filename": "policy.txt",
        "chunk_index": chunk_index,
        "content_preview": "Retrieved source text.",
        "score": 0.91,
    }


def _citation(document_id: str = "doc-1", chunk_index: int = 0) -> dict[str, object]:
    return {
        "document_id": document_id,
        "filename": "policy.txt",
        "chunk_index": chunk_index,
        "source_index": 1,
    }


def _trace(
    agent_name: str,
    agent_role: str,
    *,
    output: str = "useful output",
    status: str = "completed",
    model_name: str = "llama-3.1-8b-instant",
) -> SimpleNamespace:
    return SimpleNamespace(
        agent_name=agent_name,
        agent_role=agent_role,
        model_provider="groq",
        model_name=model_name,
        status=status,
        output=output,
        citations=[],
    )


def test_citation_accuracy_scores_strong_weak_and_missing_citation_paths() -> None:
    strong = build_scorecard(
        final_answer="Answer with a mapped citation.",
        sources=[_source()],
        citations=[_citation()],
        traces=[_trace("Researcher", "researcher")],
        retrieval_metadata={"top_k": 1},
    )
    weak = build_scorecard(
        final_answer="Answer with an unmapped citation.",
        sources=[_source()],
        citations=[_citation(document_id="missing-doc")],
        traces=[_trace("Researcher", "researcher")],
        retrieval_metadata={"top_k": 1},
    )
    missing = build_scorecard(
        final_answer="Answer without citations.",
        sources=[_source()],
        citations=[],
        traces=[_trace("Researcher", "researcher")],
        retrieval_metadata={"top_k": 1},
    )

    assert strong["citation_accuracy"] == 8
    assert weak["citation_accuracy"] == 5
    assert missing["citation_accuracy"] == 2


def test_citation_accuracy_treats_unmapped_citations_without_sources_as_missing() -> None:
    scorecard = build_scorecard(
        final_answer="Answer without retrieved sources.",
        sources=[],
        citations=[_citation()],
        traces=[_trace("Researcher", "researcher")],
        retrieval_metadata={"top_k": 1},
    )

    assert scorecard["citation_accuracy"] == 2


def test_overall_quality_applies_bonuses_and_caps_at_ten() -> None:
    scorecard = build_scorecard(
        final_answer="x" * ANSWER_LENGTH_QUALITY_THRESHOLD,
        sources=[_source()],
        citations=[_citation()],
        traces=[
            _trace("Researcher", "researcher"),
            _trace("Critic", "critic"),
            _trace("Synthesizer", "synthesizer"),
        ],
        retrieval_metadata={"top_k": 1},
    )

    assert scorecard["overall_quality"] == 9


def test_contributed_agents_require_completed_status_and_non_empty_output() -> None:
    scorecard = build_scorecard(
        final_answer="x" * ANSWER_LENGTH_QUALITY_THRESHOLD,
        sources=[_source()],
        citations=[_citation()],
        traces=[
            _trace("Researcher", "researcher"),
            _trace("Critic", "critic", output=""),
            _trace("Synthesizer", "synthesizer", status="failed"),
        ],
        retrieval_metadata={"top_k": 1},
    )

    assert scorecard["overall_quality"] == 8
    assert scorecard["model_contribution_breakdown"]["Researcher"]["contributed"] is True
    assert scorecard["model_contribution_breakdown"]["Critic"]["contributed"] is False
    assert scorecard["model_contribution_breakdown"]["Synthesizer"]["contributed"] is False


def test_insight_depth_rewards_diversity_and_critic_synthesizer_contributions() -> None:
    researcher_only = build_scorecard(
        final_answer="Short answer.",
        sources=[],
        citations=[],
        traces=[_trace("Researcher", "researcher")],
        retrieval_metadata={},
    )
    multi_role = build_scorecard(
        final_answer="Short answer.",
        sources=[],
        citations=[],
        traces=[
            _trace("Researcher", "researcher"),
            _trace("Critic", "critic"),
            _trace("Synthesizer", "synthesizer"),
        ],
        retrieval_metadata={},
    )

    expected_multi_role = (
        INSIGHT_BASE_SCORE
        + INSIGHT_DIVERSITY_BONUS_CAP
        + INSIGHT_CRITIC_BONUS
        + INSIGHT_SYNTHESIZER_BONUS
    )
    assert researcher_only["insight_depth"] == INSIGHT_BASE_SCORE
    assert multi_role["insight_depth"] == expected_multi_role
    assert multi_role["insight_depth"] > researcher_only["insight_depth"]
