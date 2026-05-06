import pytest

from core.cors import get_cors_origins


def test_cors_rejects_wildcard_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValueError, match=r"cannot include '\*'"):
        get_cors_origins()
