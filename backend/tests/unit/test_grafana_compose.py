from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_compose_includes_grafana_with_clickhouse_dependency() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    grafana = compose["services"]["grafana"]

    assert grafana["image"].startswith("grafana/grafana")
    assert "3001:3000" in grafana["ports"]
    assert grafana["depends_on"]["clickhouse"]["condition"] == "service_healthy"
    assert "./grafana/provisioning:/etc/grafana/provisioning:ro" in grafana["volumes"]


def test_grafana_clickhouse_datasource_is_provisioned() -> None:
    datasource_path = ROOT / "grafana" / "provisioning" / "datasources" / "clickhouse.yml"
    datasource = yaml.safe_load(datasource_path.read_text())

    clickhouse = datasource["datasources"][0]

    assert clickhouse["name"] == "ClickHouse"
    assert clickhouse["type"] == "grafana-clickhouse-datasource"
    assert clickhouse["jsonData"]["host"] == "clickhouse"
    assert clickhouse["jsonData"]["defaultDatabase"] == "rag_logs"
