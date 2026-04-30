from __future__ import annotations

import logging
import os
import time
from typing import Any


logger = logging.getLogger(__name__)


class SarvamClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        self.timeout_seconds = float(os.getenv("SARVAM_TIMEOUT_SECONDS", "15"))
        self.max_retries = int(os.getenv("SARVAM_MAX_RETRIES", "1"))

    def judge(self, query: str, answer: str, sources: list[dict], metadata: dict[str, Any] | None = None) -> dict:
        event_meta = metadata or {}
        if self.api_key:
            try:
                import requests
            except ImportError as exc:
                logger.warning("requests_sdk_unavailable", extra={"error": str(exc), **event_meta})
            else:
                for attempt in range(self.max_retries + 1):
                    try:
                        response = requests.post(
                            "https://api.sarvam.ai/v1/judge",
                            headers={"api-subscription-key": self.api_key, "Content-Type": "application/json"},
                            json={"query": query, "answer": answer, "sources": sources},
                            timeout=self.timeout_seconds,
                        )
                        if response.ok:
                            payload = response.json()
                            return {
                                "overall": float(payload.get("overall", 0)),
                                "citation_accuracy": float(payload.get("citation_accuracy", 0)),
                                "insight_depth": float(payload.get("insight_depth", 0)),
                                "reasoning": str(payload.get("reasoning", "")),
                            }
                        logger.warning(
                            "sarvam_judge_non_ok_response",
                            extra={"status_code": response.status_code, "attempt": attempt, **event_meta},
                        )
                        break
                    except requests.Timeout as exc:
                        if attempt < self.max_retries:
                            time.sleep(0.4 * (attempt + 1))
                            continue
                        logger.exception(
                            "sarvam_judge_timeout",
                            extra={"timeout_seconds": self.timeout_seconds, "attempt": attempt, **event_meta},
                        )
                        break
                    except requests.RequestException as exc:
                        if attempt < self.max_retries:
                            time.sleep(0.4 * (attempt + 1))
                            continue
                        logger.exception(
                            "sarvam_judge_request_failed",
                            extra={"error": str(exc), "attempt": attempt, **event_meta},
                        )
                        break
                    except (TypeError, ValueError, KeyError) as exc:
                        logger.exception("sarvam_judge_response_parse_failed", extra={"error": str(exc), **event_meta})
                        break

        citation_accuracy = 8.0 if sources else 3.0
        insight_depth = 7.0 if len(answer) > 80 else 5.0
        overall = round((citation_accuracy + insight_depth) / 2, 1)
        return {
            "overall": overall,
            "citation_accuracy": citation_accuracy,
            "insight_depth": insight_depth,
            "reasoning": "Fallback judge score based on source coverage and answer depth.",
        }
