from __future__ import annotations

from llms.groq_client import GroqClient


DEFAULT_CRITIC_MODEL = "llama-3.1-8b-instant"


def run_critic(query: str, researcher_output: str, sources: list[dict], model_name: str = DEFAULT_CRITIC_MODEL) -> str:
    source_index = ", ".join(f"{source.get('filename')}#{source.get('chunk_index')}" for source in sources)
    prompt = (
        "Critique the draft answer for unsupported claims and missing evidence. "
        "Return concise bullet points.\n"
        f"Query: {query}\nSources: {source_index}\nDraft:\n{researcher_output}"
    )
    client = GroqClient()
    return client.chat(messages=[{"role": "user", "content": prompt}], model=model_name)
