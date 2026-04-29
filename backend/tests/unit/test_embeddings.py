from rag.embeddings import EMBEDDING_DIMENSION, embed_text


def test_embed_text_dimension() -> None:
    vector = embed_text("hello")
    assert len(vector) == EMBEDDING_DIMENSION
