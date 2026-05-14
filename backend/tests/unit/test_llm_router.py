from __future__ import annotations

import pytest

from llms.router import LLMRouter, LLMRouterError


MESSAGES = [{"role": "user", "content": "question"}]


def test_router_dispatches_to_agent_provider_and_model() -> None:
    calls = []

    class FakeClient:
        def chat(self, messages, model, metadata=None):
            calls.append({"messages": messages, "model": model, "metadata": metadata})
            return "agent output"

    router = LLMRouter(provider_clients={"groq": FakeClient()})
    output = router.chat(
        provider="groq",
        model_name="llama-3.1-8b-instant",
        messages=MESSAGES,
        metadata={"agent_id": "a1"},
    )

    assert output == "agent output"
    assert calls == [
        {
            "messages": MESSAGES,
            "model": "llama-3.1-8b-instant",
            "metadata": {"agent_id": "a1"},
        }
    ]


def test_router_dispatches_sarvam_with_exact_model() -> None:
    calls = []

    class FakeClient:
        def chat(self, messages, model, metadata=None):
            calls.append({"messages": messages, "model": model, "metadata": metadata})
            return "sarvam output"

    router = LLMRouter(provider_clients={"sarvam": FakeClient()})

    assert router.chat(
        provider="sarvam",
        model_name="sarvam-m",
        messages=MESSAGES,
        metadata={"agent_name": "Synthesizer"},
    ) == "sarvam output"
    assert calls[0]["model"] == "sarvam-m"
    assert calls[0]["metadata"] == {"agent_name": "Synthesizer"}


def test_router_rejects_unknown_provider() -> None:
    router = LLMRouter(provider_clients={})

    with pytest.raises(LLMRouterError, match="Unsupported model provider: unknown"):
        router.chat(provider="unknown", model_name="model", messages=[], metadata={})


def test_provider_failure_includes_agent_provider_and_model() -> None:
    class FailingClient:
        def chat(self, messages, model, metadata=None):
            raise RuntimeError("provider exploded")

    router = LLMRouter(provider_clients={"groq": FailingClient()})

    with pytest.raises(LLMRouterError) as exc_info:
        router.chat(
            provider="groq",
            model_name="llama-3.1-8b-instant",
            messages=MESSAGES,
            metadata={"agent_name": "Researcher", "agent_id": "a1"},
        )

    message = str(exc_info.value)
    assert "Researcher" in message
    assert "a1" in message
    assert "groq" in message
    assert "llama-3.1-8b-instant" in message


def test_lmstudio_posts_openai_compatible_chat_completion() -> None:
    calls = []

    class FakeLMStudioClient:
        def chat(self, *, model_name, messages, base_url, passcode=None, timeout_seconds=30.0):
            calls.append(
                {
                    "model_name": model_name,
                    "messages": messages,
                    "base_url": base_url,
                    "passcode": passcode,
                    "timeout_seconds": timeout_seconds,
                }
            )
            return "local output"

    router = LLMRouter(provider_clients={"lmstudio": FakeLMStudioClient()})

    output = router.chat(
        provider="lmstudio",
        model_name="local-model",
        messages=MESSAGES,
        metadata={
            "provider_base_url": "http://localhost:1234",
            "provider_passcode": "secret",
            "timeout_seconds": 4,
        },
    )

    assert output == "local output"
    assert calls == [{"model_name": "local-model", "messages": MESSAGES, "base_url": "http://localhost:1234", "passcode": "secret", "timeout_seconds": 4.0}]


def test_lmstudio_requires_provider_base_url() -> None:
    router = LLMRouter(provider_clients={})

    with pytest.raises(LLMRouterError) as exc_info:
        router.chat(provider="lmstudio", model_name="local-model", messages=MESSAGES, metadata={"agent_id": "a1"})

    assert "provider_base_url" in str(exc_info.value)
    assert "lmstudio" in str(exc_info.value)
    assert "local-model" in str(exc_info.value)
