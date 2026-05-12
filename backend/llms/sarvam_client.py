from __future__ import annotations

import logging
import os
import time
from typing import Any


logger = logging.getLogger(__name__)

DEFAULT_SARVAM_CHAT_MODEL = os.getenv("SARVAM_CHAT_MODEL", "sarvam-m")


class SarvamClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        self.timeout_seconds = float(os.getenv("SARVAM_TIMEOUT_SECONDS", "15"))
        self.max_retries = int(os.getenv("SARVAM_MAX_RETRIES", "1"))

    def chat(self, messages: list[dict], model: str | None = None, metadata: dict[str, Any] | None = None) -> str:
        event_meta = metadata or {}
        if not self.api_key:
            raise RuntimeError("SARVAM_API_KEY is not configured; cannot complete chat request")

        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests package is required for SarvamClient") from exc

        chat_model = model or DEFAULT_SARVAM_CHAT_MODEL
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    "https://api.sarvam.ai/v1/chat/completions",
                    headers={"api-subscription-key": self.api_key, "Content-Type": "application/json"},
                    json={"model": chat_model, "messages": messages, "temperature": 0.2},
                    timeout=self.timeout_seconds,
                )
                if response.ok:
                    payload = response.json()
                    return payload["choices"][0]["message"]["content"] or ""
                logger.warning(
                    "sarvam_chat_non_ok_response",
                    extra={"status_code": response.status_code, "attempt": attempt, **event_meta},
                )
                break
            except requests.Timeout as exc:
                if attempt < self.max_retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                raise RuntimeError("Sarvam chat request timed out") from exc
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                raise RuntimeError(f"Sarvam chat request failed: {exc}") from exc
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise RuntimeError(f"Sarvam chat response parse failed: {exc}") from exc

        raise RuntimeError("Sarvam chat request did not return a valid response")
