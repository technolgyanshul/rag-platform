from __future__ import annotations

import pytest

from rag.orchestrator import OrchestrationConfigError, Orchestrator
from tests.unit.test_orchestrator_sequential import FakeLLMRouter, FakeObserver, FakeTraceRepository, agent, query_context, source, team


def test_debate_uses_independent_phase_then_critic_resolver() -> None:
    llm = FakeLLMRouter(outputs=["research position", "synthesis position", "resolved answer"])

    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("debate"),
        agents=[
            agent("Researcher", "researcher", 0),
            agent("Critic", "critic", 1),
            agent("Synthesizer", "synthesizer", 2),
        ],
        retrieved_context=[source("doc1")],
    )

    assert [call["agent_name"] for call in llm.calls] == ["Researcher", "Synthesizer", "Critic"]
    assert "research position" in llm.calls[-1]["messages"][-1]["content"]
    assert "Resolve the debate" in llm.calls[-1]["messages"][-1]["content"]
    assert result.final_answer == "resolved answer"
    assert len(result.traces) == 3


def test_debate_requires_at_least_two_agents() -> None:
    with pytest.raises(OrchestrationConfigError, match="debate requires at least two agents"):
        Orchestrator(repository=FakeTraceRepository(), llm_router=FakeLLMRouter(), observer=FakeObserver()).run(
            query_context(),
            team("debate"),
            agents=[agent("Solo", "researcher", 0)],
            retrieved_context=[],
        )


def test_debate_without_priority_resolver_uses_highest_ordered_agent() -> None:
    llm = FakeLLMRouter(outputs=["a position", "b opening", "b resolved"])

    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("debate"),
        agents=[agent("A", "assistant", 0), agent("B", "assistant", 1)],
        retrieved_context=[],
    )

    assert [call["agent_name"] for call in llm.calls] == ["A", "B", "B"]
    assert result.final_answer == "b resolved"


def test_debate_uses_separate_synthesizer_as_optional_finalizer() -> None:
    llm = FakeLLMRouter(outputs=["research position", "judge opening", "resolved answer", "final synthesis"])

    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("debate"),
        agents=[
            agent("Researcher", "researcher", 0),
            agent("Judge", "judge", 1),
            agent("Synthesizer", "synthesizer", 2),
        ],
        retrieved_context=[source("doc1")],
    )

    assert [call["agent_name"] for call in llm.calls] == ["Researcher", "Judge", "Judge", "Synthesizer"]
    assert result.final_answer == "final synthesis"
