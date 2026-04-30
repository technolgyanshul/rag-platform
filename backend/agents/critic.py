from __future__ import annotations

from core.config import get_settings
from llms.groq_client import GroqClient
from prompts.loader import render_prompt


DEFAULT_CRITIC_MODEL = "llama-3.1-8b-instant"


def run_critic(query: str, researcher_output: str, sources: list[dict], model_name: str = DEFAULT_CRITIC_MODEL) -> str:
    source_index = ", ".join(f"{source.get('filename')}#{source.get('chunk_index')}" for source in sources)
    prompt = render_prompt(
        template_name="critic_v1",
        variables={
            "query": query,
            "source_index": source_index,
            "researcher_output": researcher_output,
        },
    )
    client = GroqClient()
    return client.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model_name,
        metadata={"prompt_version": get_settings().rag_prompt_version, "agent": "Critic"},
    )
