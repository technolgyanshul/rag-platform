from db.supabase import SupabaseRepository, reset_fallback_store


USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_CHUNKING_CONFIG = {"chunk_size": 1000, "chunk_overlap": 150}


def setup_function() -> None:
    reset_fallback_store()


def test_insert_document_persists_file_metadata_and_versions() -> None:
    repository = SupabaseRepository()
    chunking_config = {"chunk_size": 800, "chunk_overlap": 120}

    document = repository.insert_document(
        user_id=USER_ID,
        filename="source.pdf",
        file_type="pdf",
        chunk_count=3,
        storage_path=f"{USER_ID}/source.pdf",
        content_type="application/pdf",
        file_size_bytes=12345,
        file_sha256="file-sha",
        extracted_text_sha256="text-sha",
        chunking_config=chunking_config,
        embedding_model_version="text-embedding-3-small@2026-05-08",
        embedding_bge_model_version="bge-m3@2026-05-08",
        index_version="v1",
        document_id="10000000-0000-0000-0000-000000000001",
    )

    assert document["id"] == "10000000-0000-0000-0000-000000000001"
    assert document["team_id"] == USER_ID
    assert document["storage_bucket"] == "knowledge-files"
    assert document["storage_path"] == f"{USER_ID}/source.pdf"
    assert document["content_type"] == "application/pdf"
    assert document["file_size_bytes"] == 12345
    assert document["file_sha256"] == "file-sha"
    assert document["extracted_text_sha256"] == "text-sha"
    assert document["chunking_config"] == chunking_config
    assert document["embedding_model_version"] == "text-embedding-3-small@2026-05-08"
    assert document["embedding_bge_model_version"] == "bge-m3@2026-05-08"
    assert document["index_version"] == "v1"


def test_find_document_by_fingerprint_returns_matching_document() -> None:
    repository = SupabaseRepository()
    repository.insert_document(
        user_id=USER_ID,
        filename="duplicate.txt",
        file_type="txt",
        chunk_count=1,
        storage_path=f"{USER_ID}/duplicate.txt",
        content_type="text/plain",
        file_size_bytes=5,
        file_sha256="same-file-sha",
        extracted_text_sha256="same-text-sha",
        chunking_config=DEFAULT_CHUNKING_CONFIG,
        embedding_model_version="embedding-v1",
        embedding_bge_model_version="bge-v1",
        index_version="index-v1",
    )

    match = repository.find_document_by_fingerprint(
        user_id=USER_ID,
        file_sha256="same-file-sha",
        chunking_config=DEFAULT_CHUNKING_CONFIG,
        embedding_model_version="embedding-v1",
        embedding_bge_model_version="bge-v1",
        index_version="index-v1",
    )
    miss = repository.find_document_by_fingerprint(
        user_id=USER_ID,
        file_sha256="same-file-sha",
        chunking_config={"chunk_size": 500, "chunk_overlap": 50},
        embedding_model_version="embedding-v1",
        embedding_bge_model_version="bge-v1",
        index_version="index-v1",
    )

    assert match is not None
    assert match["filename"] == "duplicate.txt"
    assert miss is None


def test_create_document_download_url_returns_fallback_signed_url() -> None:
    repository = SupabaseRepository()
    document = repository.insert_document(
        user_id=USER_ID,
        filename="download.txt",
        file_type="txt",
        chunk_count=1,
        storage_path=f"{USER_ID}/download.txt",
        content_type="text/plain",
        file_size_bytes=8,
        file_sha256="download-file-sha",
        extracted_text_sha256="download-text-sha",
        embedding_model_version="embedding-v1",
        embedding_bge_model_version="bge-v1",
        index_version="index-v1",
    )

    url = repository.create_document_download_url(user_id=USER_ID, document_id=document["id"])

    assert url == f"http://localhost/storage/v1/object/sign/knowledge-files/{USER_ID}/download.txt"
    assert url.endswith(document["storage_path"])
