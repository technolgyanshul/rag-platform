from rag import embeddings
from rag.embeddings import EMBEDDING_DIMENSION, embed_text


class FakeVector(list):
    def tolist(self) -> list[float]:
        return list(self)


class FakeEmbeddingModel:
    def encode(self, text: str, normalize_embeddings: bool) -> FakeVector:
        return FakeVector([0.1] * EMBEDDING_DIMENSION)


def test_embed_text_dimension(monkeypatch) -> None:
    monkeypatch.setattr(embeddings, "_embedding_model", FakeEmbeddingModel())
    vector = embed_text("hello")
    assert len(vector) == EMBEDDING_DIMENSION
