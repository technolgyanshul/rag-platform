-- Migration 002: Multi-model embeddings + hybrid full-text search

-- Second embedding column for BAAI/bge-base-en-v1.5 (768 dims)
alter table chunks
  add column if not exists embedding_bge vector(768);

create index if not exists chunks_embedding_bge_idx
  on chunks using ivfflat (embedding_bge vector_cosine_ops)
  with (lists = 100);

-- Generated tsvector column auto-synced with content (no app-level maintenance)
alter table chunks
  add column if not exists content_tsv tsvector
    generated always as (to_tsvector('english', coalesce(content, ''))) stored;

create index if not exists chunks_content_tsv_idx
  on chunks using gin(content_tsv);

-- Hybrid RPC: MiniLM vector + BGE vector + PostgreSQL FTS merged via RRF (k=60)
-- Returns same column shape as match_chunks so format_sources() needs no change.
create or replace function hybrid_match_chunks(
  query_embedding     vector(384),
  query_embedding_bge vector(768),
  query_text          text,
  filter_team_id      uuid,
  match_count         int  default 5,
  rrf_k               int  default 60
)
returns table (
  id           uuid,
  document_id  uuid,
  filename     text,
  chunk_index  int,
  content      text,
  metadata     jsonb,
  similarity   float
)
language sql
stable
as $$
  with minilm_ranked as (
    select chunks.id,
           row_number() over (order by chunks.embedding <=> query_embedding) as rank
    from chunks
    join documents on documents.id = chunks.document_id
    where documents.team_id = filter_team_id
    order by chunks.embedding <=> query_embedding
    limit match_count * 4
  ),
  bge_ranked as (
    select chunks.id,
           row_number() over (order by chunks.embedding_bge <=> query_embedding_bge) as rank
    from chunks
    join documents on documents.id = chunks.document_id
    where documents.team_id = filter_team_id
      and chunks.embedding_bge is not null
    order by chunks.embedding_bge <=> query_embedding_bge
    limit match_count * 4
  ),
  fts_ranked as (
    select chunks.id,
           row_number() over (
             order by ts_rank_cd(chunks.content_tsv, plainto_tsquery('english', query_text)) desc
           ) as rank
    from chunks
    join documents on documents.id = chunks.document_id
    where documents.team_id = filter_team_id
      and chunks.content_tsv @@ plainto_tsquery('english', query_text)
    limit match_count * 4
  ),
  rrf as (
    select
      coalesce(m.id, b.id, f.id) as chunk_id,
      coalesce(1.0 / (rrf_k + m.rank), 0.0)
        + coalesce(1.0 / (rrf_k + b.rank), 0.0)
        + coalesce(1.0 / (rrf_k + f.rank), 0.0) as rrf_score
    from minilm_ranked m
    full outer join bge_ranked  b on b.id = m.id
    full outer join fts_ranked  f on f.id = coalesce(m.id, b.id)
  )
  select
    chunks.id,
    chunks.document_id,
    documents.filename,
    chunks.chunk_index,
    chunks.content,
    chunks.metadata,
    rrf.rrf_score as similarity
  from rrf
  join chunks    on chunks.id    = rrf.chunk_id
  join documents on documents.id = chunks.document_id
  order by rrf.rrf_score desc
  limit match_count;
$$;
