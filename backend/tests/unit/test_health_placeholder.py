import asyncio

from routers.health import health


def test_health_returns_ok_status() -> None:
    response = asyncio.run(health())
    assert response["status"] == "ok"
