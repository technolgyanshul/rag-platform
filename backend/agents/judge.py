from __future__ import annotations

from core.config import get_settings
from llms.sarvam_client import SarvamClient


def run_judge(query: str, final_answer: str, sources: list[dict]) -> dict:
    client = SarvamClient()
    return client.judge(
        query=query,
        answer=final_answer,
        sources=sources,
        metadata={"prompt_version": get_settings().rag_prompt_version, "agent": "Judge"},
    )
