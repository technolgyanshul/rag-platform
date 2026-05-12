import pytest

from core.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_include_qdrant_embedanything_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "QDRANT_URL",
        "QDRANT_COLLECTION",
        "EMBEDANYTHING_MODEL",
        "EMBEDANYTHING_CHUNK_STRATEGY",
        "EMBEDANYTHING_BATCH_SIZE",
        "INDEX_VERSION",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.qdrant_collection == "rag_documents"
    assert settings.embedanything_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.embedanything_chunk_strategy == "semantic"
    assert settings.embedanything_batch_size == 32
    assert settings.index_version == "embedanything-qdrant-semantic-v1"


def test_settings_read_qdrant_embedanything_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_COLLECTION", "custom_docs")
    monkeypatch.setenv("EMBEDANYTHING_MODEL", "BAAI/bge-base-en-v1.5")
    monkeypatch.setenv("EMBEDANYTHING_CHUNK_STRATEGY", "sentence")
    monkeypatch.setenv("EMBEDANYTHING_BATCH_SIZE", "8")
    monkeypatch.setenv("INDEX_VERSION", "custom-index-v2")

    settings = get_settings()

    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection == "custom_docs"
    assert settings.embedanything_model == "BAAI/bge-base-en-v1.5"
    assert settings.embedanything_chunk_strategy == "sentence"
    assert settings.embedanything_batch_size == 8
    assert settings.index_version == "custom-index-v2"
