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
  on documents(
    team_id,
    file_sha256,
    coalesce(embedding_model_version, ''),
    coalesce(embedding_bge_model_version, ''),
    coalesce(index_version, ''),
    chunking_config
  )
  where file_sha256 is not null;

create index if not exists documents_storage_path_idx
  on documents(storage_bucket, storage_path)
  where storage_path is not null;
