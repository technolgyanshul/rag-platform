from __future__ import annotations

import os

from llms.groq_client import GroqClient


DEFAULT_RAG_MODEL = os.getenv("RAG_MODEL", "llama-3.1-8b-instant")


def generate_answer(query: str, sources: list[dict], model_name: str | None = None) -> str:
    if not os.getenv("GROQ_API_KEY") and not os.getenv("SARVAM_API_KEY"):
        return _extractive_answer(query=query, sources=sources)

    context = "\n\n".join(
        f"[{index}] {source['filename']} chunk {source['chunk_index']}:\n{source['content_preview']}"
        for index, source in enumerate(sources, start=1)
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Answer using only the provided retrieved context. "
                "If the context is insufficient, say so clearly. "
                "Cite sources with bracketed source numbers such as [1]."
            ),
        },
        {
            "role": "user",
            "content": f"Question:\n{query}\n\nRetrieved context:\n{context}",
        },
    ]
    return GroqClient().chat(
        messages=messages,
        model=model_name or DEFAULT_RAG_MODEL,
        metadata={"component": "rag_generator"},
    )


def _extractive_answer(query: str, sources: list[dict]) -> str:
    cited_lines = [
        f"[{index}] {source['content_preview']}"
        for index, source in enumerate(sources, start=1)
        if source.get("content_preview")
    ]
    if not cited_lines:
        return "Insufficient context to answer from uploaded documents."
    return f"Based on the retrieved documents for '{query}':\n" + "\n".join(cited_lines)
