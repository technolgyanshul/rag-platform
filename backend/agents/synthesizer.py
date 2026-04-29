from __future__ import annotations

from llms.groq_client import GroqClient


DEFAULT_SYNTHESIZER_MODEL = "llama-3.1-70b-versatile"


def run_synthesizer(
    query: str,
    researcher_output: str,
    critic_output: str,
    sources: list[dict],
    model_name: str = DEFAULT_SYNTHESIZER_MODEL,
) -> str:
    source_refs = ", ".join(f"{source.get('filename')}#{source.get('chunk_index')}" for source in sources)
    prompt = (
        "Produce the final answer grounded in sources, applying critic feedback. "
        "Keep answer clear and include citations [filename#chunk-index].\n"
        f"Query: {query}\nSources: {source_refs}\nDraft: {researcher_output}\nCritique: {critic_output}"
    )
    client = GroqClient()
    return client.chat(messages=[{"role": "user", "content": prompt}], model=model_name)
