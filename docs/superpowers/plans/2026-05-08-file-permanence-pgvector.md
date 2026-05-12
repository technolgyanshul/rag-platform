# File Permanence + pgvector Reuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store uploaded source files permanently in Supabase Storage and keep/reuse embeddings in Supabase Postgres pgvector so duplicate uploads do not recompute vectors.

**Architecture:** Keep the existing `chunks.embedding vector(384)` and `chunks.embedding_bge vector(768)` columns as the source of truth for vectors. Add a private Supabase Storage bucket for original files, add storage/hash metadata to `documents`, and check for an existing document by file hash + ingest config before OCR/chunking/embedding. Downloads go through a backend-owned signed URL endpoint after repository ownership checks.

**Tech Stack:** FastAPI, Supabase Python client, Supabase Storage, Postgres, pgvector, Next.js/TypeScript, Vitest, pytest.

---

## Current Findings

- Original files are temporary only: `backend/routers/ingest.py` writes upload bytes to `NamedTemporaryFile`, ingests text/chunks, then deletes the temp file.
- Vector persistence already exists in Supabase Postgres: `chunks.embedding vector(384)` in `001_initial_schema.sql` and `chunks.embedding_bge vector(768)` in `002_hybrid_search.sql`.
- Retrieval already uses Supabase pgvector through `hybrid_match_chunks()` when Supabase is active.
- Recompute still happens on every upload because there is no `file_sha256` duplicate check before `ingest_document()`.
- In-memory fallback is used for tests/dev when `ALLOW_INMEMORY_REPOSITORY=true` or pytest is active.

## Supabase Docs Notes Checked

- Storage buckets are private by default; private assets are downloaded either through authenticated download or signed URLs.
- Storage uploads require `INSERT` policies on `storage.objects` for user-side uploads; upsert also requires `SELECT` and `UPDATE`.
- Server-side usage with the service role bypasses Storage RLS, so the backend must enforce ownership before returning signed URLs.
- This plan uses backend/server uploads and backend-generated signed URLs, not direct browser uploads.

## File Map

- Create: `supabase/migrations/003_file_storage_and_document_hashes.sql`
- Modify: `backend/db/supabase.py`
- Modify: `backend/routers/ingest.py`
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/knowledge/page.tsx`
- Test: `backend/tests/integration/test_file_persistence.py`
- Test: `frontend/lib/api.test.ts`
- Docs: `Readme2.md`

---

### Task 1: Add Storage Bucket and Document Metadata Migration

**Files:**
- Create: `supabase/migrations/003_file_storage_and_document_hashes.sql`

- [ ] **Step 1: Create migration file**

Create `supabase/migrations/003_file_storage_and_document_hashes.sql` with:

```sql
-- Migration 003: Permanent source file storage + duplicate ingest detection

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'knowledge-files',
  'knowledge-files',
  false,
  20971520,
  array[
    'application/pdf',
    'text/plain',
    'image/png',
    'image/jpeg'
  ]
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

alter table documents
  add column if not exists storage_bucket text not null default 'knowledge-files',
  add column if not exists storage_path text,
  add column if not exists content_type text,
  add column if not exists file_size_bytes bigint not null default 0,
  add column if not exists file_sha256 text,
  add column if not exists extracted_text_sha256 text,
  add column if not exists chunking_config jsonb not null default '{"chunk_size":1000,"chunk_overlap":150}',
  add column if not exists embedding_model_version text,
  add column if not exists embedding_bge_model_version text,
  add column if not exists index_version text;

create index if not exists documents_file_sha256_idx
  on documents(team_id, file_sha256)
  where file_sha256 is not null;

create unique index if not exists documents_unique_ingest_fingerprint_idx
  on documents(team_id, file_sha256, embedding_model_version, embedding_bge_model_version, index_version, chunking_config)
  where file_sha256 is not null;

create index if not exists documents_storage_path_idx
  on documents(storage_bucket, storage_path)
  where storage_path is not null;
```

- [ ] **Step 2: Verify migration syntax locally**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('supabase/migrations/003_file_storage_and_document_hashes.sql').read_text()
required = ['storage.buckets', 'storage_path', 'file_sha256', 'documents_unique_ingest_fingerprint_idx']
missing = [item for item in required if item not in text]
raise SystemExit(f'Missing migration markers: {missing}' if missing else 0)
PY
```

Expected: exit code `0`.

- [ ] **Step 3: Commit migration**

```bash
git add supabase/migrations/003_file_storage_and_document_hashes.sql
git commit -m "feat: add permanent file storage metadata"
```

---

### Task 2: Extend Repository for Storage, Duplicate Lookup, and Signed URLs

**Files:**
- Modify: `backend/db/supabase.py`
- Test: `backend/tests/integration/test_file_persistence.py`

- [ ] **Step 1: Write failing repository tests**

Create `backend/tests/integration/test_file_persistence.py`:

```python
from db.supabase import SupabaseRepository


def test_document_hash_lookup_reuses_existing_document() -> None:
    repository = SupabaseRepository()
    user_id = '00000000-0000-0000-0000-000000000001'
    document = repository.insert_document(
        user_id=user_id,
        filename='sample.txt',
        file_type='txt',
        chunk_count=1,
        storage_path=f'{user_id}/sample-doc/sample.txt',
        content_type='text/plain',
        file_size_bytes=12,
        file_sha256='abc123',
        extracted_text_sha256='def456',
        chunking_config={'chunk_size': 1000, 'chunk_overlap': 150},
        embedding_model_version='sentence-transformers/all-MiniLM-L6-v2',
        embedding_bge_model_version='BAAI/bge-base-en-v1.5',
        index_version='local-dev',
    )

    existing = repository.find_document_by_fingerprint(
        user_id=user_id,
        file_sha256='abc123',
        chunking_config={'chunk_size': 1000, 'chunk_overlap': 150},
        embedding_model_version='sentence-transformers/all-MiniLM-L6-v2',
        embedding_bge_model_version='BAAI/bge-base-en-v1.5',
        index_version='local-dev',
    )

    assert existing is not None
    assert existing['id'] == document['id']
    assert existing['storage_path'] == f'{user_id}/sample-doc/sample.txt'


def test_create_document_download_url_requires_owned_document() -> None:
    repository = SupabaseRepository()
    user_id = '00000000-0000-0000-0000-000000000001'
    document = repository.insert_document(
        user_id=user_id,
        filename='sample.txt',
        file_type='txt',
        chunk_count=1,
        storage_path=f'{user_id}/sample-doc/sample.txt',
        content_type='text/plain',
        file_size_bytes=12,
        file_sha256='abc123',
    )

    signed_url = repository.create_document_download_url(
        user_id=user_id,
        document_id=document['id'],
        expires_in_seconds=300,
    )

    assert signed_url.endswith(document['storage_path'])
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
cd backend
ALLOW_INMEMORY_REPOSITORY=true pytest tests/integration/test_file_persistence.py -q
```

Expected: fails because new repository methods/arguments do not exist.

- [ ] **Step 3: Update fallback store and `insert_document` signature**

Modify `SupabaseRepository.insert_document()` to accept optional metadata:

```python
def insert_document(
    self,
    user_id: str,
    filename: str,
    file_type: str,
    chunk_count: int,
    storage_path: str | None = None,
    content_type: str | None = None,
    file_size_bytes: int = 0,
    file_sha256: str | None = None,
    extracted_text_sha256: str | None = None,
    chunking_config: dict[str, Any] | None = None,
    embedding_model_version: str | None = None,
    embedding_bge_model_version: str | None = None,
    index_version: str | None = None,
) -> dict[str, Any]:
```

Include these fields in `payload`:

```python
"storage_bucket": "knowledge-files",
"storage_path": storage_path,
"content_type": content_type,
"file_size_bytes": file_size_bytes,
"file_sha256": file_sha256,
"extracted_text_sha256": extracted_text_sha256,
"chunking_config": chunking_config or {"chunk_size": 1000, "chunk_overlap": 150},
"embedding_model_version": embedding_model_version,
"embedding_bge_model_version": embedding_bge_model_version,
"index_version": index_version,
```

- [ ] **Step 4: Add duplicate lookup method**

Add to `SupabaseRepository`:

```python
def find_document_by_fingerprint(
    self,
    user_id: str,
    file_sha256: str,
    chunking_config: dict[str, Any],
    embedding_model_version: str,
    embedding_bge_model_version: str,
    index_version: str,
) -> dict[str, Any] | None:
    workspace_id = self._ensure_workspace(user_id)
    if self._client:
        result = (
            self._client.table('documents')
            .select('*')
            .eq('team_id', workspace_id)
            .eq('file_sha256', file_sha256)
            .eq('embedding_model_version', embedding_model_version)
            .eq('embedding_bge_model_version', embedding_bge_model_version)
            .eq('index_version', index_version)
            .limit(1)
            .execute()
        )
        for row in result.data or []:
            if row.get('chunking_config') == chunking_config:
                return row
        return None

    for row in _FALLBACK.documents:
        if (
            row.get('team_id') == workspace_id
            and row.get('file_sha256') == file_sha256
            and row.get('chunking_config') == chunking_config
            and row.get('embedding_model_version') == embedding_model_version
            and row.get('embedding_bge_model_version') == embedding_bge_model_version
            and row.get('index_version') == index_version
        ):
            return row
    return None
```

- [ ] **Step 5: Add Storage upload method**

Add to `SupabaseRepository`:

```python
def upload_document_file(
    self,
    storage_path: str,
    payload: bytes,
    content_type: str | None,
) -> None:
    if self._client:
        options = {'content-type': content_type or 'application/octet-stream', 'upsert': False}
        self._client.storage.from_('knowledge-files').upload(storage_path, payload, options)
        return
```

No-op in fallback mode because tests do not need external storage.

- [ ] **Step 6: Add signed URL method**

Add to `SupabaseRepository`:

```python
def create_document_download_url(
    self,
    user_id: str,
    document_id: str,
    expires_in_seconds: int = 300,
) -> str:
    workspace_id = self._ensure_workspace(user_id)
    if self._client:
        result = (
            self._client.table('documents')
            .select('id, team_id, storage_path')
            .eq('id', document_id)
            .eq('team_id', workspace_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise PermissionError('Document is not accessible for this user')
        storage_path = result.data[0].get('storage_path')
        if not storage_path:
            raise FileNotFoundError('Document file is not available in storage')
        response = self._client.storage.from_('knowledge-files').create_signed_url(storage_path, expires_in_seconds)
        signed_url = response.get('signedURL') or response.get('signedUrl') or response.get('signed_url')
        if not signed_url:
            raise RuntimeError('Failed to create signed download URL')
        return signed_url

    for row in _FALLBACK.documents:
        if row.get('id') == document_id and row.get('team_id') == workspace_id:
            storage_path = row.get('storage_path')
            if not storage_path:
                raise FileNotFoundError('Document file is not available in storage')
            return f'http://localhost/storage/v1/object/sign/knowledge-files/{storage_path}'
    raise PermissionError('Document is not accessible for this user')
```

- [ ] **Step 7: Run repository tests**

```bash
cd backend
ALLOW_INMEMORY_REPOSITORY=true pytest tests/integration/test_file_persistence.py -q
```

Expected: `2 passed`.

- [ ] **Step 8: Commit repository changes**

```bash
git add backend/db/supabase.py backend/tests/integration/test_file_persistence.py
git commit -m "feat: persist document storage metadata"
```

---

### Task 3: Update Ingest Route to Store Files and Reuse Existing Vectors

**Files:**
- Modify: `backend/routers/ingest.py`
- Test: `backend/tests/integration/test_file_persistence.py`

- [ ] **Step 1: Add failing ingest test for duplicate upload reuse**

Append to `backend/tests/integration/test_file_persistence.py`:

```python
from fastapi.testclient import TestClient

from db.supabase import SupabaseRepository
from main import app


def test_ingest_duplicate_file_reuses_existing_document() -> None:
    client = TestClient(app)
    response_1 = client.post('/ingest', files={'file': ('sample.txt', b'Reusable text for RAG chunks. ' * 80, 'text/plain')})
    response_2 = client.post('/ingest', files={'file': ('sample.txt', b'Reusable text for RAG chunks. ' * 80, 'text/plain')})

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_2.json()['document_id'] == response_1.json()['document_id']
    assert response_2.json()['reused_existing'] is True

    repository = SupabaseRepository()
    rows = repository.list_documents(user_id='00000000-0000-0000-0000-000000000001')
    assert len([row for row in rows if row['filename'] == 'sample.txt']) == 1
```

- [ ] **Step 2: Run test and confirm failure**

```bash
cd backend
ALLOW_INMEMORY_REPOSITORY=true pytest tests/integration/test_file_persistence.py::test_ingest_duplicate_file_reuses_existing_document -q
```

Expected: fails because response has no `reused_existing` and duplicate lookup is not used.

- [ ] **Step 3: Extend `IngestResponse`**

In `backend/routers/ingest.py`, update response model:

```python
class IngestResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    chunks_created: int
    reused_existing: bool = False
```

- [ ] **Step 4: Add hash helpers**

At top of `backend/routers/ingest.py`, add:

```python
import hashlib
from uuid import uuid4
```

Add helper:

```python
def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
```

- [ ] **Step 5: Compute hash and check duplicate before temp parsing**

After payload validation, add:

```python
file_sha256 = _sha256_hex(payload)
chunking_config = {"chunk_size": 1000, "chunk_overlap": 150}
embedding_model_version = settings.embedding_model_version
embedding_bge_model_version = "BAAI/bge-base-en-v1.5"
index_version = settings.index_version

existing_document = repository.find_document_by_fingerprint(
    user_id=auth_user.user_id,
    file_sha256=file_sha256,
    chunking_config=chunking_config,
    embedding_model_version=embedding_model_version,
    embedding_bge_model_version=embedding_bge_model_version,
    index_version=index_version,
)
if existing_document:
    return IngestResponse(
        document_id=existing_document['id'],
        filename=existing_document.get('filename') or file.filename or 'untitled',
        file_type=existing_document.get('file_type') or extension,
        chunks_created=int(existing_document.get('chunk_count') or 0),
        reused_existing=True,
    )
```

This is the key step that avoids recomputing embeddings for an already-ingested file/config.

- [ ] **Step 6: Upload original file to Supabase Storage after successful parsing**

After `ingestion_result = ingest_document(...)` succeeds and before `insert_document()`, compute:

```python
extracted_text_hash = hashlib.sha256(ingestion_result.get('extracted_text', '').encode('utf-8')).hexdigest()
document_id = str(uuid4())
storage_filename = file.filename or f'upload.{extension}'
storage_path = f'{auth_user.user_id}/{document_id}/{storage_filename}'
repository.upload_document_file(
    storage_path=storage_path,
    payload=payload,
    content_type=file.content_type,
)
```

- [ ] **Step 7: Insert document with storage/hash metadata**

Update `repository.insert_document(...)` call:

```python
document_row = repository.insert_document(
    user_id=auth_user.user_id,
    filename=file.filename or 'untitled',
    file_type=extension,
    chunk_count=len(chunks),
    storage_path=storage_path,
    content_type=file.content_type,
    file_size_bytes=len(payload),
    file_sha256=file_sha256,
    extracted_text_sha256=extracted_text_hash,
    chunking_config=chunking_config,
    embedding_model_version=embedding_model_version,
    embedding_bge_model_version=embedding_bge_model_version,
    index_version=index_version,
)
```

If exact document id insertion is desired, extend `insert_document()` with `document_id: str | None = None`; otherwise allow DB-generated id and use that id for metadata while storage path uses a generated UUID path.

- [ ] **Step 8: Run ingest tests**

```bash
cd backend
ALLOW_INMEMORY_REPOSITORY=true pytest tests/integration/test_file_persistence.py -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit ingest changes**

```bash
git add backend/routers/ingest.py backend/tests/integration/test_file_persistence.py
git commit -m "feat: reuse vectors for duplicate uploads"
```

---

### Task 4: Add Download URL Endpoint

**Files:**
- Modify: `backend/routers/ingest.py`
- Test: `backend/tests/integration/test_file_persistence.py`

- [ ] **Step 1: Add response model**

In `backend/routers/ingest.py`:

```python
class DocumentDownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int
```

- [ ] **Step 2: Add failing endpoint test**

Append to `backend/tests/integration/test_file_persistence.py`:

```python
def test_document_download_endpoint_returns_signed_url() -> None:
    client = TestClient(app)
    upload = client.post('/ingest', files={'file': ('downloadable.txt', b'Downloadable text. ' * 80, 'text/plain')})
    assert upload.status_code == 200

    document_id = upload.json()['document_id']
    response = client.get(f'/ingest/documents/{document_id}/download')

    assert response.status_code == 200
    assert response.json()['url'].startswith('http')
    assert response.json()['expires_in_seconds'] == 300
```

- [ ] **Step 3: Implement endpoint**

Add to `backend/routers/ingest.py`:

```python
@router.get('/documents/{document_id}/download', response_model=DocumentDownloadResponse)
def get_document_download_url(
    document_id: str,
    request: Request,
    auth_user: AuthUser = Depends(get_current_user),
) -> DocumentDownloadResponse:
    request_id = getattr(request.state, 'request_id', 'unknown')
    try:
        repository = SupabaseRepository()
        url = repository.create_document_download_url(
            user_id=auth_user.user_id,
            document_id=document_id,
            expires_in_seconds=300,
        )
        return DocumentDownloadResponse(url=url, expires_in_seconds=300)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception('document_download_url_failed', extra={'request_id': request_id, 'user_id': auth_user.user_id, 'document_id': document_id})
        raise HTTPException(status_code=503, detail='Document download temporarily unavailable') from error
```

- [ ] **Step 4: Run endpoint test**

```bash
cd backend
ALLOW_INMEMORY_REPOSITORY=true pytest tests/integration/test_file_persistence.py::test_document_download_endpoint_returns_signed_url -q
```

Expected: pass.

- [ ] **Step 5: Commit endpoint**

```bash
git add backend/routers/ingest.py backend/tests/integration/test_file_persistence.py
git commit -m "feat: add document download signed URLs"
```

---

### Task 5: Surface File Permanence in Frontend Knowledge UI

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/knowledge/page.tsx`
- Test: `frontend/lib/api.test.ts`

- [ ] **Step 1: Add frontend API test**

In `frontend/lib/api.test.ts`, add test for download helper:

```ts
import { getDocumentDownloadUrl } from './api';

it('returns document download signed URL', async () => {
  mockSupabaseClient.auth.getSession.mockResolvedValue({
    data: { session: { access_token: 'test-token' } },
    error: null,
  });
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ url: 'https://example.supabase.co/signed-url', expires_in_seconds: 300 }),
  }));

  const result = await getDocumentDownloadUrl('doc-1');

  expect(result.url).toBe('https://example.supabase.co/signed-url');
  expect(fetch).toHaveBeenCalledWith(
    'http://localhost:8000/ingest/documents/doc-1/download',
    expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer test-token' }) }),
  );
});
```

- [ ] **Step 2: Run frontend test and confirm failure**

```bash
cd frontend
npm test
```

Expected: fails because `getDocumentDownloadUrl` does not exist.

- [ ] **Step 3: Add types**

In `frontend/lib/types.ts`:

```ts
export type DocumentDownloadResponse = {
  url: string;
  expires_in_seconds: number;
};
```

If document list types exist, add optional metadata:

```ts
storage_path?: string | null;
file_size_bytes?: number;
file_sha256?: string | null;
```

- [ ] **Step 4: Add API helper**

In `frontend/lib/api.ts`:

```ts
export async function getDocumentDownloadUrl(documentId: string): Promise<DocumentDownloadResponse> {
  const response = await fetchWithAuth(`${API_BASE_URL}/ingest/documents/${encodeURIComponent(documentId)}/download`);
  if (!response.ok) {
    throw new Error('Could not create document download URL');
  }
  return response.json();
}
```

- [ ] **Step 5: Add download action to Knowledge page**

In `frontend/app/knowledge/page.tsx`, import helper and add click handler:

```ts
import { getDocumentDownloadUrl, listKnowledgeDocuments } from '../../lib/api';

const handleDownload = async (documentId: string) => {
  try {
    const result = await getDocumentDownloadUrl(documentId);
    window.open(result.url, '_blank', 'noopener,noreferrer');
  } catch (error) {
    setMessage(error instanceof Error ? error.message : 'Could not open document.');
  }
};
```

Add a button in each document row:

```tsx
<button type="button" onClick={() => void handleDownload(document.id)}>
  Open file
</button>
```

- [ ] **Step 6: Run frontend tests**

```bash
cd frontend
npm test
```

Expected: all tests pass.

- [ ] **Step 7: Commit frontend changes**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts frontend/app/knowledge/page.tsx frontend/lib/api.test.ts
git commit -m "feat: add knowledge file downloads"
```

---

### Task 6: Update Docs and Full Verification

**Files:**
- Modify: `Readme2.md`

- [ ] **Step 1: Update current status docs**

In `Readme2.md`, update status to say:

```md
- Original uploaded files are stored permanently in the private Supabase Storage bucket `knowledge-files`.
- Document rows store `storage_path`, file size, content type, SHA-256 hash, chunking config, embedding model versions, and index version.
- Duplicate uploads with the same file hash and ingest config reuse the existing document/chunks/vectors instead of recomputing embeddings.
- Vectors remain in Supabase Postgres pgvector columns: `chunks.embedding` and `chunks.embedding_bge`.
```

- [ ] **Step 2: Run backend focused tests**

```bash
cd backend
ALLOW_INMEMORY_REPOSITORY=true pytest tests/integration/test_file_persistence.py tests/integration/test_placeholder.py tests/unit/test_retriever_contract.py -q
```

Expected: pass.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend
npm test
```

Expected: pass.

- [ ] **Step 4: Run Docker backend test profile if available**

```bash
docker compose --profile test run --rm test
```

Expected: pass. If it fails due missing local image/model cache, run:

```bash
docker compose --profile test build test
docker compose --profile test run --rm test
```

- [ ] **Step 5: Commit docs**

```bash
git add Readme2.md
git commit -m "docs: document storage and pgvector persistence"
```

---

## Implementation Decisions

- Use Supabase Storage only for original binaries; do not store binary payloads in Postgres.
- Keep vectors in `chunks` pgvector columns; do not add another vector database.
- Reuse vectors by detecting duplicate file hash + chunking config + embedding model versions + index version before parsing/embedding.
- Use private Storage bucket and backend-generated signed URLs, so no service role key is exposed to the frontend.
- Do not use Storage upsert for now. A duplicate file should reuse the existing document instead of overwriting it.
- Keep in-memory fallback behavior for tests; fallback signed URL can be a deterministic fake URL.

## Risks and Follow-Ups

- Existing documents will have null `storage_path` because their original files were not saved. They can still answer queries from chunks, but cannot be downloaded unless re-uploaded.
- Duplicate detection means the same user uploading the same file/config gets the existing `document_id`; if separate upload history is required later, add a `document_uploads` table.
- The Supabase Python client response shape for `create_signed_url()` may differ by version; implementation should defensively handle `signedURL`, `signedUrl`, and `signed_url`.
- If frontend direct uploads are added later, add explicit Storage RLS policies for authenticated users by folder prefix.

## Self-Review

- Spec coverage: file permanence is handled by Storage bucket + `storage_path`; pgvector reuse is handled by existing `chunks` vector columns plus duplicate fingerprint lookup.
- Placeholder scan: no implementation step depends on TBD behavior.
- Type consistency: `file_sha256`, `storage_path`, `chunking_config`, `embedding_model_version`, `embedding_bge_model_version`, and `index_version` are used consistently across migration, repository, route, and tests.
