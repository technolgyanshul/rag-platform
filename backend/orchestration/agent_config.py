from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agents.critic import DEFAULT_CRITIC_MODEL
from agents.researcher import DEFAULT_RESEARCHER_MODEL
from agents.synthesizer import DEFAULT_SYNTHESIZER_MODEL


@dataclass
class AgentConfig:
    model_name: str
    system_prompt: str | None


_DEFAULTS: dict[str, AgentConfig] = {
    "researcher": AgentConfig(model_name=DEFAULT_RESEARCHER_MODEL, system_prompt=None),
    "critic":     AgentConfig(model_name=DEFAULT_CRITIC_MODEL,     system_prompt=None),
    "synthesizer":AgentConfig(model_name=DEFAULT_SYNTHESIZER_MODEL, system_prompt=None),
    "judge":      AgentConfig(model_name="sarvam-judge-model",     system_prompt=None),
}


def build_agent_configs(db_rows: list[dict[str, Any]]) -> dict[str, AgentConfig]:
    configs = {role: AgentConfig(cfg.model_name, cfg.system_prompt) for role, cfg in _DEFAULTS.items()}
    for row in db_rows:
        role = (row.get("role") or "").lower().strip()
        if role not in configs:
            continue
        configs[role] = AgentConfig(
            model_name=row.get("model_name") or configs[role].model_name,
            system_prompt=row.get("system_prompt"),
        )
    return configs
