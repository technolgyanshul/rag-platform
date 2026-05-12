from __future__ import annotations

import json
import logging
import traceback
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from core.config import get_settings


logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "apikey",
    "api_key",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "token",
}


def sanitize_metadata(value: Any, *, log_raw_payloads: bool) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                sanitized[key_text] = "[redacted]"
            elif not log_raw_payloads and key_text.lower() in {"payload", "body", "query", "answer", "prompt", "content", "sources"}:
                sanitized[key_text] = _summarize_value(item)
            else:
                sanitized[key_text] = sanitize_metadata(item, log_raw_payloads=log_raw_payloads)
        return sanitized
    if isinstance(value, list):
        return [sanitize_metadata(item, log_raw_payloads=log_raw_payloads) for item in value]
    if isinstance(value, tuple):
        return [sanitize_metadata(item, log_raw_payloads=log_raw_payloads) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in SENSITIVE_KEYS or any(part in lowered for part in ("password", "secret", "token"))


def _summarize_value(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"type": "str", "length": len(value), "preview": value[:120]}
    if isinstance(value, (list, tuple)):
        return {"type": "list", "length": len(value)}
    if isinstance(value, dict):
        return {"type": "dict", "keys": sorted(str(key) for key in value.keys())}
    return {"type": type(value).__name__}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=str, separators=(",", ":"))


class ClickHouseObservability:
    def __init__(
        self,
        *,
        enabled: bool,
        strict: bool,
        log_raw_payloads: bool = True,
        client: Any | None = None,
        database: str = "rag_logs",
    ) -> None:
        self.enabled = enabled
        self.strict = strict
        self.log_raw_payloads = log_raw_payloads
        self._client = client
        self.database = database

    def initialize(self) -> None:
        if not self.enabled:
            return
        client = self._get_client()
        statements = [
            f"CREATE DATABASE IF NOT EXISTS {self.database}",
            f"""
            CREATE TABLE IF NOT EXISTS {self.database}.trace_events (
                event_time DateTime64(3, 'UTC'),
                event_name LowCardinality(String),
                request_id String,
                trace_id String,
                user_id String,
                route String,
                component String,
                level LowCardinality(String),
                status LowCardinality(String),
                duration_ms Nullable(Int64),
                metadata_json String,
                error_type String,
                error_message String,
                stack_trace String
            ) ENGINE = MergeTree
            ORDER BY (event_time, event_name, request_id)
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.database}.ui_events (
                event_time DateTime64(3, 'UTC'),
                client_timestamp String,
                event_name LowCardinality(String),
                request_id String,
                user_id String,
                page String,
                component String,
                action String,
                payload_json String,
                browser_json String
            ) ENGINE = MergeTree
            ORDER BY (event_time, event_name, user_id)
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.database}.infra_checks (
                event_time DateTime64(3, 'UTC'),
                service LowCardinality(String),
                status LowCardinality(String),
                duration_ms Nullable(Int64),
                metadata_json String,
                error_message String
            ) ENGINE = MergeTree
            ORDER BY (event_time, service)
            """,
        ]
        try:
            for statement in statements:
                client.command(statement)
        except Exception:
            self._handle_write_failure()

    def record_trace_event(
        self,
        *,
        event_name: str,
        request_id: str = "",
        trace_id: str = "",
        user_id: str = "",
        route: str = "",
        component: str = "",
        level: str = "INFO",
        status: str = "",
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        error: BaseException | None = None,
    ) -> None:
        if not self.enabled:
            return
        row = [
            datetime.now(UTC),
            event_name,
            request_id,
            trace_id,
            user_id,
            route,
            component,
            level,
            status,
            duration_ms,
            _json_dumps(sanitize_metadata(metadata or {}, log_raw_payloads=self.log_raw_payloads)),
            type(error).__name__ if error else "",
            str(error) if error else "",
            "".join(traceback.format_exception(error)) if error else "",
        ]
        self._insert(
            f"{self.database}.trace_events",
            [row],
            [
                "event_time",
                "event_name",
                "request_id",
                "trace_id",
                "user_id",
                "route",
                "component",
                "level",
                "status",
                "duration_ms",
                "metadata_json",
                "error_type",
                "error_message",
                "stack_trace",
            ],
        )

    def record_ui_event(
        self,
        *,
        event_name: str,
        request_id: str = "",
        user_id: str = "",
        page: str = "",
        component: str = "",
        action: str = "",
        payload: dict[str, Any] | None = None,
        browser: dict[str, Any] | None = None,
        client_timestamp: str = "",
    ) -> None:
        if not self.enabled:
            return
        row = [
            datetime.now(UTC),
            client_timestamp,
            event_name,
            request_id,
            user_id,
            page,
            component,
            action,
            _json_dumps(sanitize_metadata(payload or {}, log_raw_payloads=self.log_raw_payloads)),
            _json_dumps(sanitize_metadata(browser or {}, log_raw_payloads=self.log_raw_payloads)),
        ]
        self._insert(
            f"{self.database}.ui_events",
            [row],
            [
                "event_time",
                "client_timestamp",
                "event_name",
                "request_id",
                "user_id",
                "page",
                "component",
                "action",
                "payload_json",
                "browser_json",
            ],
        )

    def record_infra_check(
        self,
        *,
        service: str,
        status: str,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        error_message: str = "",
    ) -> None:
        if not self.enabled:
            return
        row = [
            datetime.now(UTC),
            service,
            status,
            duration_ms,
            _json_dumps(sanitize_metadata(metadata or {}, log_raw_payloads=self.log_raw_payloads)),
            error_message,
        ]
        self._insert(
            f"{self.database}.infra_checks",
            [row],
            ["event_time", "service", "status", "duration_ms", "metadata_json", "error_message"],
        )

    def _insert(self, table: str, rows: list[list[Any]], column_names: list[str]) -> None:
        try:
            self._get_client().insert(table, rows, column_names=column_names)
        except Exception:
            self._handle_write_failure()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        settings = get_settings()
        try:
            import clickhouse_connect
        except ImportError as exc:
            raise RuntimeError("clickhouse-connect is required for ClickHouse observability") from exc

        parsed = urlparse(settings.clickhouse_host)
        secure = parsed.scheme == "https"
        self._client = clickhouse_connect.get_client(
            host=parsed.hostname or settings.clickhouse_host,
            port=parsed.port or (8443 if secure else 8123),
            username=settings.clickhouse_username,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
            secure=secure,
            connect_timeout=2,
            send_receive_timeout=3,
        )
        return self._client

    def _handle_write_failure(self) -> None:
        if self.strict:
            raise
        logger.exception("clickhouse_observability_write_failed")


_OBSERVABILITY: ClickHouseObservability | None = None


def get_observability() -> ClickHouseObservability:
    global _OBSERVABILITY
    if _OBSERVABILITY is None:
        settings = get_settings()
        _OBSERVABILITY = ClickHouseObservability(
            enabled=settings.clickhouse_enabled,
            strict=settings.clickhouse_strict,
            log_raw_payloads=settings.clickhouse_log_raw_payloads,
            database=settings.clickhouse_database,
        )
    return _OBSERVABILITY


def reset_observability() -> None:
    global _OBSERVABILITY
    _OBSERVABILITY = None
