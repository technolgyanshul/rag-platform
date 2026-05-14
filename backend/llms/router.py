from __future__ import annotations

from typing import Any

import requests

from llms.groq_client import GroqClient
from llms.sarvam_client import SarvamClient


class LLMRouterError(RuntimeError):
    pass


class LLMRouter:
    def __init__(self, provider_clients: dict[str, Any] | None = None) -> None:
        self._provider_clients = provider_clients or {}

    def chat(
        self,
        provider: str,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        metadata = metadata or {}
        provider_name = provider.lower().strip()

        if provider_name not in {"groq", "sarvam", "lmstudio"}:
            raise LLMRouterError(f"Unsupported model provider: {provider}")

        try:
            if provider_name == "groq":
                client = self._provider_clients.get("groq") or GroqClient()
                return client.chat(messages=messages, model=model_name, metadata=metadata)
            if provider_name == "sarvam":
                client = self._provider_clients.get("sarvam") or SarvamClient()
                return client.chat(messages=messages, model=model_name, metadata=metadata)
            return self._chat_lmstudio(model_name=model_name, messages=messages, metadata=metadata)
        except Exception as exc:
            if isinstance(exc, LLMRouterError):
                raise
            raise LLMRouterError(self._failure_message(provider_name, model_name, metadata, exc)) from exc

    def _chat_lmstudio(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any],
    ) -> str:
        base_url = str(metadata.get("provider_base_url") or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("metadata.provider_base_url is required for lmstudio")

        headers = {"Content-Type": "application/json"}
        passcode = metadata.get("provider_passcode")
        if passcode:
            headers["Authorization"] = f"Bearer {passcode}"

        timeout = metadata.get("timeout_seconds", metadata.get("timeout", 30))
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers=headers,
            json={"model": model_name, "messages": messages, "temperature": 0.2},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"] or ""

    def _failure_message(
        self,
        provider: str,
        model_name: str,
        metadata: dict[str, Any],
        error: Exception,
    ) -> str:
        agent_bits = []
        if metadata.get("agent_name"):
            agent_bits.append(f"name={metadata['agent_name']}")
        if metadata.get("agent_id"):
            agent_bits.append(f"id={metadata['agent_id']}")
        agent_context = f" agent({', '.join(agent_bits)})" if agent_bits else ""
        return f"LLM provider failure for{agent_context} provider={provider} model={model_name}: {error}"
