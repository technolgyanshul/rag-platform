import httpx
import pytest

import observability
from main import app


pytestmark = pytest.mark.anyio


async def test_ui_event_endpoint_writes_authenticated_event(monkeypatch) -> None:
    captured = []

    class FakeObservability:
        def record_trace_event(self, **kwargs):
            return None

        def record_ui_event(self, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(observability, "get_observability", lambda: FakeObservability())

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/observability/ui-events",
            json={
                "event_name": "query_submit",
                "page": "/chat",
                "component": "QueryInput",
                "action": "submit",
                "payload": {"query": "hello"},
                "client_timestamp": "2026-05-12T12:00:00Z",
                "browser": {"userAgent": "vitest"},
            },
        )

    assert response.status_code == 202
    assert captured[0]["event_name"] == "query_submit"
    assert captured[0]["user_id"] == "00000000-0000-0000-0000-000000000001"
    assert captured[0]["payload"]["query"] == "hello"


async def test_ui_event_endpoint_surfaces_strict_clickhouse_failure(monkeypatch) -> None:
    class FakeObservability:
        def record_trace_event(self, **kwargs):
            return None

        def record_ui_event(self, **kwargs):
            raise RuntimeError("clickhouse down")

    monkeypatch.setattr(observability, "get_observability", lambda: FakeObservability())

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/observability/ui-events",
            json={"event_name": "query_submit", "page": "/chat"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Observability temporarily unavailable"
