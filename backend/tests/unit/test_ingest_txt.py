from pathlib import Path

from rag.ingest import ingest_document


def test_ingest_txt_creates_chunks(tmp_path: Path) -> None:
    content = "RAG platform testing text. " * 80
    file_path = tmp_path / "sample.txt"
    file_path.write_text(content, encoding="utf-8")

    result = ingest_document(str(file_path), "txt", chunk_size=300, chunk_overlap=50)

    assert result["chunks"]
    assert all("embedding" in item for item in result["chunks"])
