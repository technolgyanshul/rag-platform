from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class LMStudioError(RuntimeError):
    category: str
    message: str

    def __str__(self) -> str:
        return self.message


class LMStudioClient:
    def chat(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        base_url: str,
        passcode: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> str:
        payload = self._request_json(
            method="POST",
            url=f"{self._api_base(base_url)}/chat/completions",
            passcode=passcode,
            timeout_seconds=timeout_seconds,
            json={"model": model_name, "messages": messages, "temperature": 0.2},
        )
        try:
            return str(payload["choices"][0]["message"]["content"] or "")
        except Exception as error:
            raise LMStudioError(category="malformed_response", message="LM Studio returned an invalid chat response payload") from error

    def health(
        self,
        base_url: str,
        passcode: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> dict[str, Any]:
        payload = self._request_json(
            method="GET",
            url=f"{self._api_base(base_url)}/models",
            passcode=passcode,
            timeout_seconds=timeout_seconds,
            json=None,
        )
        models = payload.get("data")
        if not isinstance(models, list):
            raise LMStudioError(category="malformed_response", message="LM Studio health check returned an invalid models payload")
        return {"ok": True, "models_count": len(models)}

    def list_models(
        self,
        base_url: str,
        passcode: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> list[str]:
        payload = self._request_json(
            method="GET",
            url=f"{self._api_base(base_url)}/models",
            passcode=passcode,
            timeout_seconds=timeout_seconds,
            json=None,
        )
        items = payload.get("data")
        if not isinstance(items, list):
            raise LMStudioError(category="malformed_response", message="LM Studio returned an invalid model list payload")
        names: list[str] = []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                names.append(item["id"].strip())
        return names

    def _request_json(
        self,
        *,
        method: str,
        url: str,
        passcode: str | None,
        timeout_seconds: float,
        json: dict[str, Any] | None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if passcode:
            headers["Authorization"] = f"Bearer {passcode}"
        try:
            response = requests.request(method=method, url=url, headers=headers, json=json, timeout=timeout_seconds)
            if response.status_code in {401, 403}:
                raise LMStudioError(category="auth_rejection", message="LM Studio rejected the provided passcode")
            if response.status_code >= 400:
                detail = self._response_detail(response)
                category = "model_missing" if "model" in detail.lower() and "not" in detail.lower() else "upstream_error"
                raise LMStudioError(category=category, message=f"LM Studio request failed ({response.status_code}): {detail}")
            payload = response.json()
            if not isinstance(payload, dict):
                raise LMStudioError(category="malformed_response", message="LM Studio returned a non-object JSON payload")
            return payload
        except requests.Timeout as error:
            raise LMStudioError(category="timeout", message="LM Studio request timed out") from error
        except requests.ConnectionError as error:
            raise LMStudioError(category="unreachable_server", message="LM Studio server is unreachable") from error
        except ValueError as error:
            raise LMStudioError(category="malformed_response", message="LM Studio returned invalid JSON") from error
        except LMStudioError:
            raise
        except Exception as error:
            raise LMStudioError(category="upstream_error", message=f"LM Studio request failed: {error}") from error

    @staticmethod
    def _api_base(base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if not normalized:
            raise LMStudioError(category="invalid_config", message="LM Studio base URL is required")
        if normalized.endswith("/v1"):
            return normalized
        return f"{normalized}/v1"

    @staticmethod
    def _response_detail(response: requests.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("error") or payload.get("detail") or payload.get("message")
                if isinstance(detail, str) and detail.strip():
                    return detail.strip()
        except Exception:
            pass
        text = (response.text or "").strip()
        return text or "unknown error"
