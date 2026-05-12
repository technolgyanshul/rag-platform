import pytest

from core.cors import get_cors_origins


def test_cors_rejects_wildcard_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValueError, match=r"cannot include '\*'"):
        get_cors_origins()


def test_cors_allows_demo_tunnel_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://rag.anshul-garg.com,http://localhost:3000",
    )

    assert get_cors_origins() == [
        "https://rag.anshul-garg.com",
        "http://localhost:3000",
    ]
