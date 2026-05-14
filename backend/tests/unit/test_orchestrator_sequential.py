from __future__ import annotations

from typing import Any

import pytest

import rag.orchestrator as orchestrator_module
from rag.orchestrator import (
    OrchestrationConfigError,
    OrchestrationExecutionError,
    Orchestrator,
    QueryContext,
)


class FakeTraceRepository:
    def __init__(self) -> None:
        self.traces: list[dict[str, Any]] = []
        self.scorecards: list[dict[str, Any]] = []

    def create_agent_trace(self, **kwargs: Any) -> dict[str, Any]:
        row = {"id": f"trace-{len(self.traces) + 1}", **kwargs}
        self.traces.append(row)
        return row

    def save_scorecard(self, **kwargs: Any) -> dict[str, Any]:
        row = {"id": f"scorecard-{len(self.scorecards) + 1}", **kwargs}
        self.scorecards.append(row)
        return row


class FakeLLMRouter:
    def __init__(self, outputs: list[str] | None = None, error_on_call: int | None = None) -> None:
        self.outputs = outputs or []
        self.error_on_call = error_on_call
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        provider: str,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        metadata = metadata or {}
        self.calls.append(
            {
                "provider": provider,
                "model_name": model_name,
                "messages": messages,
                "agent_name": metadata.get("agent_name"),
            }
        )
        if self.error_on_call == len(self.calls):
            raise RuntimeError("provider exploded")
        return self.outputs[len(self.calls) - 1] if len(self.calls) <= len(self.outputs) else f"output {len(self.calls)}"


class FakeObserver:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record_trace_event(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


def query_context() -> QueryContext:
    return QueryContext(user_id="u1", session_id="s1", query_id="q1", query="Question", request_id="req-1")


def team(rule: str) -> dict[str, Any]:
    return {"id": "t1", "domain": "Policy", "collaboration_rule": rule}


def agent(name: str, role: str, execution_order: int, *, created_at: str | None = None) -> dict[str, Any]:
    return {
        "id": f"agent-{name.lower()}",
        "name": name,
        "role": role,
        "system_prompt": f"Act as {role}",
        "model_provider": "groq",
        "model_name": "llama-3.1-8b-instant",
        "execution_order": execution_order,
        "created_at": created_at or f"2026-01-01T00:00:0{execution_order}Z",
    }


def source(document_id: str) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "filename": f"{document_id}.pdf",
        "chunk_index": 0,
        "content_preview": "Relevant policy text",
        "score": 0.91,
    }


def test_orchestrator_dispatches_by_collaboration_rule() -> None:
    orchestrator = Orchestrator(
        repository=FakeTraceRepository(),
        llm_router=FakeLLMRouter(outputs=["seq output"]),
        observer=FakeObserver(),
    )

    result = orchestrator.run(
        query_context(),
        team=team("sequential"),
        agents=[agent("Researcher", "researcher", 0)],
        retrieved_context=[source("doc1")],
    )

    assert result.final_answer == "seq output"
    assert result.collaboration_rule == "sequential"


def test_unsupported_collaboration_rule_raises_config_error() -> None:
    with pytest.raises(OrchestrationConfigError, match="Unsupported collaboration rule"):
        Orchestrator(repository=FakeTraceRepository(), llm_router=FakeLLMRouter(), observer=FakeObserver()).run(
            query_context(),
            team=team("round_robin"),
            agents=[agent("Researcher", "researcher", 0)],
            retrieved_context=[],
        )


def test_sequential_runs_agents_by_execution_order_and_uses_synthesizer_final() -> None:
    llm = FakeLLMRouter(outputs=["research", "critique", "synthesis"])
    repository = FakeTraceRepository()
    observer = FakeObserver()

    result = Orchestrator(repository=repository, llm_router=llm, observer=observer).run(
        query_context(),
        team("sequential"),
        agents=[
            agent("Synthesizer", "synthesizer", 2),
            agent("Researcher", "researcher", 0),
            agent("Critic", "critic", 1),
        ],
        retrieved_context=[source("doc1")],
    )

    assert [call["agent_name"] for call in llm.calls] == ["Researcher", "Critic", "Synthesizer"]
    assert result.final_answer == "synthesis"
    assert [trace.status for trace in result.traces] == ["completed", "completed", "completed"]
    assert len(repository.traces) == 3
    assert repository.scorecards[0]["overall_quality"] == 8
    assert repository.scorecards[0]["citation_accuracy"] == 8
    assert repository.scorecards[0]["insight_depth"] == 8
    assert repository.scorecards[0]["model_contribution_breakdown"]["Researcher"] == {
        "agent_role": "researcher",
        "model_provider": "groq",
        "model_name": "llama-3.1-8b-instant",
        "status": "completed",
        "contributed": True,
        "output_chars": len("research"),
        "citation_count": 0,
    }
    assert result.citations == [{"document_id": "doc1", "filename": "doc1.pdf", "chunk_index": 0, "source_index": 1}]
    assert "Previous agent outputs" in llm.calls[1]["messages"][-1]["content"]
    assert [event["event_name"] for event in observer.events].count("agent_step_completed") == 3
    assert observer.events[0]["event_name"] == "orchestration_started"
    assert observer.events[-1]["event_name"] == "orchestration_finished"


def test_sequential_uses_last_output_when_no_synthesizer_runs() -> None:
    result = Orchestrator(repository=FakeTraceRepository(), llm_router=FakeLLMRouter(outputs=["first", "last"]), observer=FakeObserver()).run(
        query_context(),
        team("sequential"),
        agents=[agent("Researcher", "researcher", 0), agent("Critic", "critic", 1)],
        retrieved_context=[],
    )

    assert result.final_answer == "last"


def test_orchestrator_uses_evaluator_output_for_persisted_scorecard(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluated_scorecard = {
        "overall_quality": 6,
        "citation_accuracy": 4,
        "insight_depth": 5,
        "model_contribution_breakdown": {"Researcher": {"contributed": True}},
        "notes": "evaluator output",
    }
    captured_payload: dict[str, Any] = {}

    def _fake_evaluator(
        *,
        final_answer: str,
        sources: list[dict[str, Any]],
        citations: list[dict[str, Any]],
        traces: list[Any],
        retrieval_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        captured_payload["final_answer"] = final_answer
        captured_payload["sources"] = sources
        captured_payload["citations"] = citations
        captured_payload["trace_count"] = len(traces)
        captured_payload["retrieval_metadata"] = retrieval_metadata
        return evaluated_scorecard

    monkeypatch.setattr(orchestrator_module, "evaluate_scorecard", _fake_evaluator)

    repository = FakeTraceRepository()
    result = Orchestrator(repository=repository, llm_router=FakeLLMRouter(outputs=["research"]), observer=FakeObserver()).run(
        query_context(),
        team("sequential"),
        agents=[agent("Researcher", "researcher", 0)],
        retrieved_context=[source("doc1")],
    )

    assert captured_payload["final_answer"] == "research"
    assert captured_payload["trace_count"] == 1
    assert captured_payload["sources"][0]["document_id"] == "doc1"
    assert captured_payload["citations"][0]["source_index"] == 1
    assert captured_payload["retrieval_metadata"] == {"source_count": 1}
    assert repository.scorecards[0]["overall_quality"] == 6
    assert repository.scorecards[0]["citation_accuracy"] == 4
    assert repository.scorecards[0]["insight_depth"] == 5
    assert result.scorecard == evaluated_scorecard


def test_sequential_persists_failed_trace_and_stops() -> None:
    llm = FakeLLMRouter(outputs=["research"], error_on_call=2)
    repository = FakeTraceRepository()
    observer = FakeObserver()

    with pytest.raises(OrchestrationExecutionError, match="Critic"):
        Orchestrator(repository=repository, llm_router=llm, observer=observer).run(
            query_context(),
            team("sequential"),
            agents=[agent("Researcher", "researcher", 0), agent("Critic", "critic", 1), agent("Synthesizer", "synthesizer", 2)],
            retrieved_context=[source("doc1")],
        )

    assert [call["agent_name"] for call in llm.calls] == ["Researcher", "Critic"]
    assert repository.traces[-1]["agent_name"] == "Critic"
    assert repository.traces[-1]["status"] == "failed"
    assert "model_provider" in repository.traces[-1]
    assert [event["event_name"] for event in observer.events][-2:] == ["agent_step_failed", "orchestration_failed"]
