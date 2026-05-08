from __future__ import annotations

import logging
import time
from typing import Any

from agents.critic import run_critic
from agents.judge import run_judge
from agents.researcher import run_researcher
from agents.synthesizer import run_synthesizer
from db.supabase import SupabaseRepository
from orchestration.agent_config import build_agent_configs
from orchestration.state import GraphState


logger = logging.getLogger(__name__)


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


def run_graph(
    query: str,
    sources: list[dict[str, Any]],
    team_id: str | None = None,
) -> dict[str, Any]:
    db_rows: list[dict[str, Any]] = []
    if team_id:
        try:
            db_rows = SupabaseRepository().get_agents_for_team(team_id)
        except Exception as exc:
            logger.warning("agent_config_load_failed", extra={"team_id": team_id, "error": str(exc)})

    configs = build_agent_configs(db_rows)

    state: GraphState = {
        "query": query,
        "sources": sources,
        "agent_trace": [],
    }

    researcher_cfg = configs["researcher"]
    state["researcher_output"] = _run_step(
        state,
        "Researcher",
        researcher_cfg.model_name,
        lambda: run_researcher(
            query=query,
            sources=sources,
            model_name=researcher_cfg.model_name,
            system_prompt=researcher_cfg.system_prompt,
        ),
    )

    critic_cfg = configs["critic"]
    state["critic_output"] = _run_step(
        state,
        "Critic",
        critic_cfg.model_name,
        lambda: run_critic(
            query=query,
            researcher_output=state["researcher_output"],
            sources=sources,
            model_name=critic_cfg.model_name,
            system_prompt=critic_cfg.system_prompt,
        ),
    )

    synthesizer_cfg = configs["synthesizer"]
    state["synthesizer_output"] = _run_step(
        state,
        "Synthesizer",
        synthesizer_cfg.model_name,
        lambda: run_synthesizer(
            query=query,
            researcher_output=state["researcher_output"],
            critic_output=state["critic_output"],
            sources=sources,
            model_name=synthesizer_cfg.model_name,
            system_prompt=synthesizer_cfg.system_prompt,
        ),
    )

    state["final_answer"] = state["synthesizer_output"]

    judge_cfg = configs["judge"]
    state["scorecard"] = _run_step(
        state,
        "Judge",
        judge_cfg.model_name,
        lambda: run_judge(query=query, final_answer=state["final_answer"], sources=sources),
    )

    return {
        "final_answer": state["final_answer"],
        "agent_trace": state["agent_trace"],
        "scorecard": state["scorecard"],
    }
