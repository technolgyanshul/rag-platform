from __future__ import annotations

import pytest
import requests

from llms.lmstudio_client import LMStudioClient, LMStudioError


def test_chat_success_with_v1_suffix(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    def fake_request(method, url, headers, json, timeout):
        calls.append({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(requests, "request", fake_request)
    output = LMStudioClient().chat(
        model_name="local-model",
        messages=[{"role": "user", "content": "hi"}],
        base_url="http://localhost:1234/v1",
        passcode="secret",
        timeout_seconds=3,
    )
    assert output == "ok"
    assert calls[0]["url"] == "http://localhost:1234/v1/chat/completions"


def test_health_unreachable_maps_category(monkeypatch) -> None:
    def fake_request(**_kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "request", fake_request)
    with pytest.raises(LMStudioError) as exc_info:
        LMStudioClient().health(base_url="http://localhost:1234")
    assert exc_info.value.category == "unreachable_server"


def test_model_list_payload_validation(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"data": "bad-shape"}

    monkeypatch.setattr(requests, "request", lambda **_kwargs: FakeResponse())
    with pytest.raises(LMStudioError) as exc_info:
        LMStudioClient().list_models(base_url="http://localhost:1234")
    assert exc_info.value.category == "malformed_response"
