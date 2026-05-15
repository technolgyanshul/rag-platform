from __future__ import annotations
"""Environment-driven backend configuration with validated defaults."""

import os
from dataclasses import dataclass
from functools import lru_cache


def _parse_int(name: str, default: int, min_value: int) -> int:
    """Read an integer environment variable with minimum-bound validation."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw_value}") from exc
    if value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {value}")
    return value


def _parse_float(name: str, default: float, min_value: float) -> float:
    """Read a float environment variable with minimum-bound validation."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {raw_value}") from exc
    if value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {value}")
    return value


def _parse_bool(name: str, default: bool) -> bool:
    """Read a truthy/falsey environment variable with a default fallback."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Typed runtime configuration consumed across backend modules."""
    log_level: str
    top_k: int
    max_query_length: int
    max_file_size_mb: int
    query_history_limit_default: int
    query_history_limit_max: int
    dashboard_days_default: int
    dashboard_days_max: int
    allowed_file_types: set[str]
    qdrant_url: str
    qdrant_collection: str
    embedanything_model: str
    embedanything_chunk_strategy: str
    embedanything_batch_size: int
    rag_prompt_version: str
    embedding_model_version: str
    index_version: str
    model_version: str
    clickhouse_enabled: bool
    clickhouse_host: str
    clickhouse_database: str
    clickhouse_username: str
    clickhouse_password: str
    clickhouse_strict: bool
    clickhouse_log_raw_payloads: bool
    clickhouse_connect_timeout_seconds: float
    clickhouse_read_timeout_seconds: float
    clickhouse_init_max_retries: int
    clickhouse_init_retry_backoff_seconds: float


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings parsed from environment variables."""
    allowed = {
        file_type.strip().lower()
        for file_type in os.getenv("ALLOWED_FILE_TYPES", "pdf,png,jpg,jpeg,txt").split(",")
        if file_type.strip()
    }
    if not allowed:
        raise ValueError("ALLOWED_FILE_TYPES must not be empty")

    return Settings(
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        top_k=_parse_int("TOP_K", default=5, min_value=1),
        max_query_length=_parse_int("MAX_QUERY_LENGTH", default=5000, min_value=1),
        max_file_size_mb=_parse_int("MAX_FILE_SIZE_MB", default=20, min_value=1),
        query_history_limit_default=_parse_int("QUERY_HISTORY_LIMIT_DEFAULT", default=50, min_value=1),
        query_history_limit_max=_parse_int("QUERY_HISTORY_LIMIT_MAX", default=200, min_value=1),
        dashboard_days_default=_parse_int("DASHBOARD_DAYS_DEFAULT", default=7, min_value=1),
        dashboard_days_max=_parse_int("DASHBOARD_DAYS_MAX", default=30, min_value=1),
        allowed_file_types=allowed,
        qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
        qdrant_collection=os.getenv("QDRANT_COLLECTION", "rag_documents"),
        embedanything_model=os.getenv("EMBEDANYTHING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        embedanything_chunk_strategy=os.getenv("EMBEDANYTHING_CHUNK_STRATEGY", "semantic"),
        embedanything_batch_size=_parse_int("EMBEDANYTHING_BATCH_SIZE", default=32, min_value=1),
        rag_prompt_version=os.getenv("RAG_PROMPT_VERSION", "rag_prompt_v1"),
        embedding_model_version=os.getenv("EMBEDDING_MODEL_VERSION", "sentence-transformers/all-MiniLM-L6-v2"),
        index_version=os.getenv("INDEX_VERSION", "embedanything-qdrant-semantic-v1"),
        model_version=os.getenv("MODEL_VERSION", "groq-sarvam-v1"),
        clickhouse_enabled=_parse_bool("CLICKHOUSE_ENABLED", default=False),
        clickhouse_host=os.getenv("CLICKHOUSE_HOST", ""),
        clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "rag_logs"),
        clickhouse_username=os.getenv("CLICKHOUSE_USERNAME", "default"),
        clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        clickhouse_strict=_parse_bool("CLICKHOUSE_STRICT", default=True),
        clickhouse_log_raw_payloads=_parse_bool("CLICKHOUSE_LOG_RAW_PAYLOADS", default=False),
        clickhouse_connect_timeout_seconds=_parse_float("CLICKHOUSE_CONNECT_TIMEOUT_SECONDS", default=5.0, min_value=0.1),
        clickhouse_read_timeout_seconds=_parse_float("CLICKHOUSE_READ_TIMEOUT_SECONDS", default=15.0, min_value=0.1),
        clickhouse_init_max_retries=_parse_int("CLICKHOUSE_INIT_MAX_RETRIES", default=2, min_value=0),
        clickhouse_init_retry_backoff_seconds=_parse_float("CLICKHOUSE_INIT_RETRY_BACKOFF_SECONDS", default=1.0, min_value=0.0),
    )
