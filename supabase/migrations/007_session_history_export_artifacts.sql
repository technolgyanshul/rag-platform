alter table public.queries
  add column if not exists sources jsonb not null default '[]'::jsonb,
  add column if not exists citations jsonb not null default '[]'::jsonb,
  add column if not exists retrieval_metadata jsonb not null default '{}'::jsonb,
  add column if not exists model_version text,
  add column if not exists insufficient_context boolean not null default false;
