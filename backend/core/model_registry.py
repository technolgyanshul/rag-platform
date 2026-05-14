from __future__ import annotations

import os
from dataclasses import dataclass


class ModelValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model_name: str


_DEFAULT_GROQ_MODELS = "llama-3.1-8b-instant,llama-3.3-70b-versatile"
_DEFAULT_SARVAM_MODELS = "sarvam-m"


def _parse_models_env(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def allowed_models() -> dict[str, set[str]]:
    groq_models = _parse_models_env(os.getenv("GROQ_AGENT_MODELS", _DEFAULT_GROQ_MODELS))
    sarvam_models = _parse_models_env(os.getenv("SARVAM_AGENT_MODELS", _DEFAULT_SARVAM_MODELS))
    sarvam_chat_model = os.getenv("SARVAM_CHAT_MODEL", "").strip()
    if sarvam_chat_model:
        sarvam_models.add(sarvam_chat_model)
    if not groq_models:
        groq_models = _parse_models_env(_DEFAULT_GROQ_MODELS)
    if not sarvam_models:
        sarvam_models = _parse_models_env(_DEFAULT_SARVAM_MODELS)
    return {
        "groq": groq_models,
        "sarvam": sarvam_models,
        # LM Studio is user-hosted; model names are validated as non-empty text.
        "lmstudio": set(),
    }


def model_catalog() -> dict[str, list[str]]:
    models = allowed_models()
    return {
        "groq": sorted(models["groq"]),
        "sarvam": sorted(models["sarvam"]),
        "lmstudio": [],
    }


def default_model_selection() -> ModelSelection:
    models = allowed_models()
    provider = "groq" if models["groq"] else "sarvam"
    choices = models[provider]
    model_name = sorted(choices)[0] if choices else ""
    return ModelSelection(provider=provider, model_name=model_name)


def validate_model_selection(provider: str, model_name: str) -> ModelSelection:
    normalized_provider = provider.strip().lower()
    normalized_model_name = model_name.strip()

    if not normalized_provider:
        raise ModelValidationError("Model provider is required")
    if not normalized_model_name:
        raise ModelValidationError("Model name is required")

    allowed_for_provider = allowed_models().get(normalized_provider)
    if allowed_for_provider is None:
        raise ModelValidationError(f"Unsupported model provider: {provider}")

    if normalized_provider == "lmstudio":
        return ModelSelection(provider=normalized_provider, model_name=normalized_model_name)

    if normalized_model_name not in allowed_for_provider:
        raise ModelValidationError(f"Unsupported model for {normalized_provider}: {model_name}")

    return ModelSelection(provider=normalized_provider, model_name=normalized_model_name)
