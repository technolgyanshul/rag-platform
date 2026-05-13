from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_compose_excludes_local_clickhouse_and_grafana() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    assert "clickhouse" not in compose["services"]
    assert "grafana" not in compose["services"]
    assert "clickhouse_data" not in compose.get("volumes", {})
    assert "grafana_data" not in compose.get("volumes", {})


def test_backend_clickhouse_env_defaults_to_non_blocking_cloud_settings() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    backend = compose["services"]["backend"]
    environment = set(backend["environment"])

    assert "CLICKHOUSE_ENABLED=${CLICKHOUSE_ENABLED:-false}" in environment
    assert "CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-}" in environment
    assert "CLICKHOUSE_STRICT=${CLICKHOUSE_STRICT:-false}" in environment
    assert "CLICKHOUSE_LOG_RAW_PAYLOADS=${CLICKHOUSE_LOG_RAW_PAYLOADS:-false}" in environment
    assert "CLICKHOUSE_CONNECT_TIMEOUT_SECONDS=${CLICKHOUSE_CONNECT_TIMEOUT_SECONDS:-5}" in environment
    assert "CLICKHOUSE_READ_TIMEOUT_SECONDS=${CLICKHOUSE_READ_TIMEOUT_SECONDS:-15}" in environment
    assert "CLICKHOUSE_INIT_MAX_RETRIES=${CLICKHOUSE_INIT_MAX_RETRIES:-2}" in environment
    assert "CLICKHOUSE_INIT_RETRY_BACKOFF_SECONDS=${CLICKHOUSE_INIT_RETRY_BACKOFF_SECONDS:-1}" in environment
    assert "clickhouse" not in backend.get("depends_on", {})
