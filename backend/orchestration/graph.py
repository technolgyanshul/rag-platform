from __future__ import annotations

import time
from typing import Any

from agents.critic import DEFAULT_CRITIC_MODEL, run_critic
from agents.judge import run_judge
from agents.researcher import DEFAULT_RESEARCHER_MODEL, run_researcher
from agents.synthesizer import DEFAULT_SYNTHESIZER_MODEL, run_synthesizer
from orchestration.state import GraphState


def _run_step(state: GraphState, agent_name: str, model_name: str, runner) -> Any:
    start = time.perf_counter()
    output = runner()
    duration_ms = int((time.perf_counter() - start) * 1000)
    trace_row = {
        "agent_name": agent_name,
        "model_name": model_name,
        "output": output,
        "response_time_ms": duration_ms,
    }
    state.setdefault("agent_trace", []).append(trace_row)
    return output


def run_graph(query: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    state: GraphState = {
        "query": query,
        "sources": sources,
        "agent_trace": [],
    }

    state["researcher_output"] = _run_step(
        state,
        "Researcher",
        DEFAULT_RESEARCHER_MODEL,
        lambda: run_researcher(query=query, sources=sources, model_name=DEFAULT_RESEARCHER_MODEL),
    )

    state["critic_output"] = _run_step(
        state,
        "Critic",
        DEFAULT_CRITIC_MODEL,
        lambda: run_critic(
            query=query,
            researcher_output=state["researcher_output"],
            sources=sources,
            model_name=DEFAULT_CRITIC_MODEL,
        ),
    )

    state["synthesizer_output"] = _run_step(
        state,
        "Synthesizer",
        DEFAULT_SYNTHESIZER_MODEL,
        lambda: run_synthesizer(
            query=query,
            researcher_output=state["researcher_output"],
            critic_output=state["critic_output"],
            sources=sources,
            model_name=DEFAULT_SYNTHESIZER_MODEL,
        ),
    )

    state["final_answer"] = state["synthesizer_output"]

    state["scorecard"] = _run_step(
        state,
        "Judge",
        "sarvam-judge-model",
        lambda: run_judge(query=query, final_answer=state["final_answer"], sources=sources),
    )

    return {
        "final_answer": state["final_answer"],
        "agent_trace": state["agent_trace"],
        "scorecard": state["scorecard"],
    }
