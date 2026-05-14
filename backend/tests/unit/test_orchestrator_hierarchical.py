from __future__ import annotations

import pytest

from rag.orchestrator import OrchestrationConfigError, Orchestrator
from tests.unit.test_orchestrator_sequential import FakeLLMRouter, FakeObserver, FakeTraceRepository, agent, query_context, source, team


def test_hierarchical_runs_planner_workers_then_merger() -> None:
    llm = FakeLLMRouter(outputs=["plan", "worker research", "worker critique", "merged answer"])

    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("hierarchical"),
        agents=[
            agent("Planner", "planner", 0),
            agent("Researcher", "researcher", 1),
            agent("Critic", "critic", 2),
            agent("Synthesizer", "synthesizer", 3),
        ],
        retrieved_context=[source("doc1")],
    )

    assert [call["agent_name"] for call in llm.calls] == ["Planner", "Researcher", "Critic", "Synthesizer"]
    assert "plan" in llm.calls[1]["messages"][-1]["content"]
    assert "worker research" in llm.calls[-1]["messages"][-1]["content"]
    assert result.final_answer == "merged answer"


def test_hierarchical_falls_back_to_first_agent_as_planner_and_planner_as_merger() -> None:
    llm = FakeLLMRouter(outputs=["plan", "worker output", "merged answer"])

    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("hierarchical"),
        agents=[agent("A", "assistant", 0), agent("B", "assistant", 1)],
        retrieved_context=[],
    )

    assert [call["agent_name"] for call in llm.calls] == ["A", "B", "A"]
    assert result.final_answer == "merged answer"


def test_hierarchical_requires_at_least_two_agents() -> None:
    with pytest.raises(OrchestrationConfigError, match="hierarchical requires at least two agents"):
        Orchestrator(repository=FakeTraceRepository(), llm_router=FakeLLMRouter(), observer=FakeObserver()).run(
            query_context(),
            team("hierarchical"),
            agents=[agent("Solo", "planner", 0)],
            retrieved_context=[],
        )
