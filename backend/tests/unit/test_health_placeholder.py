from routers.health import health


def test_health_returns_ok_status() -> None:
    assert health()["status"] == "ok"
