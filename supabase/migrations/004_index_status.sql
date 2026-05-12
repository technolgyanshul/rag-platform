-- Migration 004: Document index status metadata

alter table documents
  add column if not exists index_backend text not null default 'legacy_supabase_pgvector',
  add column if not exists index_status text not null default 'legacy_unindexed',
  add column if not exists indexed_at timestamptz,
  add column if not exists index_error text;
