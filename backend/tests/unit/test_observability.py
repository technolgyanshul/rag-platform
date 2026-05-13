from collections.abc import Generator

import pytest

from core.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_clickhouse_settings_defaults_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "CLICKHOUSE_ENABLED",
        "CLICKHOUSE_HOST",
        "CLICKHOUSE_DATABASE",
        "CLICKHOUSE_USERNAME",
        "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_STRICT",
        "CLICKHOUSE_LOG_RAW_PAYLOADS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.clickhouse_enabled is False
    assert settings.clickhouse_host == ""
    assert settings.clickhouse_database == "rag_logs"
    assert settings.clickhouse_username == "default"
    assert settings.clickhouse_password == ""
    assert settings.clickhouse_strict is True
    assert settings.clickhouse_log_raw_payloads is False


def test_clickhouse_settings_accept_cloud_connection_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLICKHOUSE_ENABLED", "true")
    monkeypatch.setenv("CLICKHOUSE_HOST", "https://abc123.us-east-1.aws.clickhouse.cloud:8443")
    monkeypatch.setenv("CLICKHOUSE_DATABASE", "rag_logs")
    monkeypatch.setenv("CLICKHOUSE_USERNAME", "cloud_user")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "cloud_password")
    monkeypatch.setenv("CLICKHOUSE_STRICT", "true")
    monkeypatch.setenv("CLICKHOUSE_LOG_RAW_PAYLOADS", "false")

    settings = get_settings()

    assert settings.clickhouse_enabled is True
    assert settings.clickhouse_host == "https://abc123.us-east-1.aws.clickhouse.cloud:8443"
    assert settings.clickhouse_database == "rag_logs"
    assert settings.clickhouse_username == "cloud_user"
    assert settings.clickhouse_password == "cloud_password"
    assert settings.clickhouse_strict is True
    assert settings.clickhouse_log_raw_payloads is False


def test_observability_redacts_auth_headers_and_preserves_payload() -> None:
    from observability import sanitize_metadata

    payload = sanitize_metadata(
        {
            "headers": {
                "authorization": "Bearer secret-token",
                "x-request-id": "req-1",
                "cookie": "session=secret",
            },
            "query": "what happened?",
        },
        log_raw_payloads=True,
    )

    assert payload["headers"]["authorization"] == "[redacted]"
    assert payload["headers"]["cookie"] == "[redacted]"
    assert payload["headers"]["x-request-id"] == "req-1"
    assert payload["query"] == "what happened?"


def test_observability_strict_mode_reraises_write_failures() -> None:
    from observability import ClickHouseObservability

    class BrokenClient:
        def insert(self, *args, **kwargs):
            raise RuntimeError("clickhouse down")

    service = ClickHouseObservability(
        enabled=True,
        strict=True,
        log_raw_payloads=True,
        client=BrokenClient(),
    )

    with pytest.raises(RuntimeError, match="clickhouse down"):
        service.record_trace_event(event_name="query_started", request_id="req-1")


def test_observability_disabled_mode_skips_client_writes() -> None:
    from observability import ClickHouseObservability

    class BrokenClient:
        def insert(self, *args, **kwargs):
            raise AssertionError("disabled observability must not write")

    service = ClickHouseObservability(enabled=False, strict=True, client=BrokenClient())

    service.record_trace_event(event_name="query_started", request_id="req-1")


def test_observability_enabled_requires_clickhouse_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLICKHOUSE_ENABLED", "true")
    monkeypatch.delenv("CLICKHOUSE_HOST", raising=False)

    from observability import ClickHouseObservability

    service = ClickHouseObservability(enabled=True, strict=True)

    with pytest.raises(RuntimeError, match="CLICKHOUSE_HOST is required"):
        service.record_trace_event(event_name="query_started", request_id="req-1")
