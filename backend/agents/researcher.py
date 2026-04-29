from __future__ import annotations

from llms.groq_client import GroqClient


DEFAULT_RESEARCHER_MODEL = "llama-3.1-8b-instant"


def run_researcher(query: str, sources: list[dict], model_name: str = DEFAULT_RESEARCHER_MODEL) -> str:
    source_context = "\n".join(
        f"- {source.get('filename', 'unknown')}#{source.get('chunk_index', -1)}: {source.get('content_preview', '')}"
        for source in sources
    )
    prompt = (
        "Answer the user query using only provided sources. Include citations like [filename#chunk-index].\n"
        f"Query: {query}\nSources:\n{source_context}"
    )
    client = GroqClient()
    return client.chat(messages=[{"role": "user", "content": prompt}], model=model_name)
