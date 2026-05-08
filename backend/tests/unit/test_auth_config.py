from core.auth import get_current_user


class _Response:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


def test_get_current_user_prefers_backend_anon_key(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "backend-anon")
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "frontend-publishable")

    def _fake_get(_url: str, headers: dict[str, str], timeout: int) -> _Response:
        assert headers["apikey"] == "backend-anon"
        assert headers["Authorization"] == "Bearer token-1"
        assert timeout == 8
        return _Response(200, {"id": "123", "email": "dev@example.com"})

    monkeypatch.setattr("core.auth.requests.get", _fake_get)
    user = get_current_user(authorization="Bearer token-1")
    assert user.user_id == "123"
    assert user.email == "dev@example.com"
