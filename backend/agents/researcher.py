from __future__ import annotations

from core.config import get_settings
from llms.groq_client import GroqClient
from prompts.loader import render_prompt


DEFAULT_RESEARCHER_MODEL = "llama-3.1-8b-instant"


def run_researcher(
    query: str,
    sources: list[dict],
    model_name: str = DEFAULT_RESEARCHER_MODEL,
    system_prompt: str | None = None,
) -> str:
    source_context = "\n".join(
        f"- {source.get('filename', 'unknown')}#{source.get('chunk_index', -1)}: {source.get('content_preview', '')}"
        for source in sources
    )
    prompt = render_prompt(
        template_name="researcher_v1",
        variables={
            "query": query,
            "source_context": source_context,
        },
    )
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    client = GroqClient()
    return client.chat(
        messages=messages,
        model=model_name,
        metadata={"prompt_version": get_settings().rag_prompt_version, "agent": "Researcher"},
    )
