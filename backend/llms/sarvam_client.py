from __future__ import annotations

import logging
import os


logger = logging.getLogger(__name__)


class SarvamClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("SARVAM_API_KEY", "")

    def judge(self, query: str, answer: str, sources: list[dict]) -> dict:
        if self.api_key:
            try:
                import requests

                response = requests.post(
                    "https://api.sarvam.ai/v1/judge",
                    headers={"api-subscription-key": self.api_key, "Content-Type": "application/json"},
                    json={"query": query, "answer": answer, "sources": sources},
                    timeout=15,
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
                    "Sarvam judge returned non-OK response, using fallback score",
                    extra={"status_code": response.status_code},
                )
            except ImportError as exc:
                logger.warning("Requests SDK unavailable, using fallback score", extra={"error": str(exc)})
            except requests.RequestException as exc:
                logger.exception("Sarvam judge request failed, using fallback score", extra={"error": str(exc)})
            except (TypeError, ValueError, KeyError) as exc:
                logger.exception("Sarvam judge response parse failed, using fallback score", extra={"error": str(exc)})

        citation_accuracy = 8.0 if sources else 3.0
        insight_depth = 7.0 if len(answer) > 80 else 5.0
        overall = round((citation_accuracy + insight_depth) / 2, 1)
        return {
            "overall": overall,
            "citation_accuracy": citation_accuracy,
            "insight_depth": insight_depth,
            "reasoning": "Fallback judge score based on source coverage and answer depth.",
        }
