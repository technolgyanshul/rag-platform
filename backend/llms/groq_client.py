from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any


logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "20"))
        self.max_retries = int(os.getenv("GROQ_MAX_RETRIES", "2"))

    def chat(self, messages: list[dict], model: str, metadata: dict[str, Any] | None = None) -> str:
        event_meta = metadata or {}
        if self.api_key:
            for attempt in range(self.max_retries + 1):
                try:
                    return self._chat_with_timeout(messages=messages, model=model)
                except ImportError as exc:
                    logger.warning(
                        "groq_sdk_unavailable",
                        extra={"model": model, "error": str(exc), "attempt": attempt, **event_meta},
                    )
                    break
                except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
                    logger.exception(
                        "groq_response_parse_failed",
                        extra={"model": model, "error": str(exc), "attempt": attempt, **event_meta},
                    )
                    break
                except FutureTimeoutError as exc:
                    if attempt < self.max_retries:
                        time.sleep(0.3 * (attempt + 1))
                        continue
                    logger.exception(
                        "groq_request_timeout",
                        extra={"model": model, "timeout_seconds": self.timeout_seconds, "attempt": attempt, **event_meta},
                    )
                    break
                except Exception as exc:
                    if attempt < self.max_retries:
                        time.sleep(0.3 * (attempt + 1))
                        continue
                    logger.exception(
                        "groq_chat_request_failed",
                        extra={"model": model, "error": str(exc), "attempt": attempt, **event_meta},
                    )
                    break

        last_prompt = messages[-1]["content"] if messages else ""
        return f"Fallback {model} response: {str(last_prompt)[:300]}"

    def _chat_with_timeout(self, messages: list[dict], model: str) -> str:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._chat_once, messages, model)
            return future.result(timeout=self.timeout_seconds)

    def _chat_once(self, messages: list[dict], model: str) -> str:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
        return completion.choices[0].message.content or ""
