from rag.chunking import chunk_text


def test_chunk_text_splits_with_overlap() -> None:
    text = "a" * 2400
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)

    assert len(chunks) == 3
    assert len(chunks[0]) == 1000
    assert len(chunks[1]) == 1000
    assert len(chunks[2]) == 800
