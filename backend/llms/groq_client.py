from __future__ import annotations

import logging
import os


logger = logging.getLogger(__name__)


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
            except ImportError as exc:
                logger.warning("Groq SDK unavailable, using fallback response", extra={"model": model, "error": str(exc)})
            except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
                logger.exception("Groq response parsing failed, using fallback response", extra={"model": model, "error": str(exc)})
            except Exception as exc:
                logger.exception("Groq chat request failed, using fallback response", extra={"model": model, "error": str(exc)})

        last_prompt = messages[-1]["content"] if messages else ""
        return f"Fallback {model} response: {str(last_prompt)[:300]}"
