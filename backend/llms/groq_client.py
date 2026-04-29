from __future__ import annotations

import os


class GroqClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")

    def chat(self, messages: list[dict], model: str) -> str:
        if self.api_key:
            try:
                from groq import Groq

                client = Groq(api_key=self.api_key)
                completion = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
                return completion.choices[0].message.content or ""
            except Exception:
                pass

        last_prompt = messages[-1]["content"] if messages else ""
        return f"Fallback {model} response: {str(last_prompt)[:300]}"
