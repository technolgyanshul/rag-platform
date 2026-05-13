from __future__ import annotations

from dataclasses import dataclass


class ModelValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model_name: str


_ALLOWED_MODELS: dict[str, set[str]] = {
    "ollama": {
        "llama3.1:8b",
        "llama3.2:3b",
        "mistral:7b",
    },
    "groq": {
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
    },
    "sarvam": {
        "sarvam-m",
    },
}

_DEFAULT_SELECTION = ModelSelection(provider="ollama", model_name="llama3.1:8b")


def default_model_selection() -> ModelSelection:
    return _DEFAULT_SELECTION


def validate_model_selection(provider: str, model_name: str) -> ModelSelection:
    normalized_provider = provider.strip().lower()
    normalized_model_name = model_name.strip()

    if not normalized_provider:
        raise ModelValidationError("Model provider is required")
    if not normalized_model_name:
        raise ModelValidationError("Model name is required")

    allowed_for_provider = _ALLOWED_MODELS.get(normalized_provider)
    if allowed_for_provider is None:
        raise ModelValidationError(f"Unsupported model provider: {provider}")

    if normalized_model_name not in allowed_for_provider:
        raise ModelValidationError(f"Unsupported model for {normalized_provider}: {model_name}")

    return ModelSelection(provider=normalized_provider, model_name=normalized_model_name)
