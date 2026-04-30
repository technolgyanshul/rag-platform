from __future__ import annotations

from core.config import get_settings
from llms.groq_client import GroqClient
from prompts.loader import render_prompt


DEFAULT_SYNTHESIZER_MODEL = "llama-3.1-70b-versatile"


def run_synthesizer(
    query: str,
    researcher_output: str,
    critic_output: str,
    sources: list[dict],
    model_name: str = DEFAULT_SYNTHESIZER_MODEL,
) -> str:
    source_refs = ", ".join(f"{source.get('filename')}#{source.get('chunk_index')}" for source in sources)
    prompt = render_prompt(
        template_name="synthesizer_v1",
        variables={
            "query": query,
            "source_refs": source_refs,
            "researcher_output": researcher_output,
            "critic_output": critic_output,
        },
    )
    client = GroqClient()
    return client.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model_name,
        metadata={"prompt_version": get_settings().rag_prompt_version, "agent": "Synthesizer"},
    )
