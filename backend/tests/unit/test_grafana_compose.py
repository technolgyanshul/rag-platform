from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_compose_excludes_local_clickhouse_and_grafana() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    assert "clickhouse" not in compose["services"]
    assert "grafana" not in compose["services"]
    assert "clickhouse_data" not in compose.get("volumes", {})
    assert "grafana_data" not in compose.get("volumes", {})


def test_backend_clickhouse_env_requires_cloud_host_without_local_fallback() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    backend = compose["services"]["backend"]
    environment = set(backend["environment"])

    assert "CLICKHOUSE_HOST=${CLICKHOUSE_HOST:?Set CLICKHOUSE_HOST to your ClickHouse Cloud HTTPS URL}" in environment
    assert "CLICKHOUSE_LOG_RAW_PAYLOADS=${CLICKHOUSE_LOG_RAW_PAYLOADS:-false}" in environment
    assert "clickhouse" not in backend.get("depends_on", {})
