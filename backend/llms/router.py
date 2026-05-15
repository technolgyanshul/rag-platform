from __future__ import annotations
"""Provider routing for chat completions across configured LLM backends."""

from typing import Any

from llms.groq_client import GroqClient
from llms.lmstudio_client import LMStudioClient, LMStudioError
from llms.sarvam_client import SarvamClient


class LLMRouterError(RuntimeError):
    """Raised when provider routing or provider invocation fails."""
    pass


class LLMRouter:
    """Dispatches chat requests to provider-specific clients."""

    def __init__(self, provider_clients: dict[str, Any] | None = None) -> None:
        self._provider_clients = provider_clients or {}

    def chat(
        self,
        provider: str,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Route a chat request to the selected provider and normalize failures."""
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
            client = self._provider_clients.get("lmstudio") or LMStudioClient()
            return self._chat_lmstudio(client=client, model_name=model_name, messages=messages, metadata=metadata)
        except Exception as exc:
            if isinstance(exc, LLMRouterError):
                raise
            raise LLMRouterError(self._failure_message(provider_name, model_name, metadata, exc)) from exc

    def _chat_lmstudio(
        self,
        client: LMStudioClient,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any],
    ) -> str:
        """Invoke LM Studio chat after validating required metadata."""
        base_url = str(metadata.get("provider_base_url") or "").strip().rstrip("/")
        if not base_url:
            raise LMStudioError(category="invalid_config", message="metadata.provider_base_url is required for lmstudio")
        passcode = metadata.get("provider_passcode")
        timeout = float(metadata.get("timeout_seconds", metadata.get("timeout", 30)))
        return client.chat(
            model_name=model_name,
            messages=messages,
            base_url=base_url,
            passcode=str(passcode) if isinstance(passcode, str) and passcode else None,
            timeout_seconds=timeout,
        )

    def _failure_message(
        self,
        provider: str,
        model_name: str,
        metadata: dict[str, Any],
        error: Exception,
    ) -> str:
        """Build a detailed error message with provider and agent context."""
        agent_bits = []
        if metadata.get("agent_name"):
            agent_bits.append(f"name={metadata['agent_name']}")
        if metadata.get("agent_id"):
            agent_bits.append(f"id={metadata['agent_id']}")
        agent_context = f" agent({', '.join(agent_bits)})" if agent_bits else ""
        if isinstance(error, LMStudioError):
            return (
                f"LLM provider failure for{agent_context} provider={provider} model={model_name} "
                f"category={error.category}: {error.message}"
            )
        return f"LLM provider failure for{agent_context} provider={provider} model={model_name}: {error}"
