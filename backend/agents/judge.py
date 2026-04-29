from __future__ import annotations

from llms.sarvam_client import SarvamClient


def run_judge(query: str, final_answer: str, sources: list[dict]) -> dict:
    client = SarvamClient()
    return client.judge(query=query, answer=final_answer, sources=sources)
