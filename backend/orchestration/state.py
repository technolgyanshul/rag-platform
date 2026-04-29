from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    query: str
    sources: list[dict[str, Any]]
    researcher_output: str
    critic_output: str
    synthesizer_output: str
    scorecard: dict[str, Any]
    agent_trace: list[dict[str, Any]]
    final_answer: str
