create extension if not exists vector;

create table if not exists teams (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  domain text,
  collaboration_mode text default 'sequential',
  created_at timestamptz default now()
);

create table if not exists agents (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references teams(id) on delete cascade,
  role text not null,
  model_provider text not null,
  model_name text not null,
  system_prompt text,
  response_style text,
  position int default 0,
  created_at timestamptz default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references teams(id) on delete cascade,
  filename text not null,
  file_type text default 'pdf',
  chunk_count int default 0,
  uploaded_at timestamptz default now()
);

create table if not exists chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  embedding vector(384),
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  team_id uuid not null references teams(id) on delete cascade,
  title text,
  created_at timestamptz default now()
);

create table if not exists queries (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions(id) on delete cascade,
  query_text text not null,
  final_answer text,
  overall_score float,
  citation_accuracy float,
  insight_depth float,
  response_time_ms int,
  created_at timestamptz default now()
);

create table if not exists agent_traces (
  id uuid primary key default gen_random_uuid(),
  query_id uuid not null references queries(id) on delete cascade,
  agent_name text not null,
  model_name text,
  input_summary text,
  output text,
  response_time_ms int,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

create table if not exists session_logs (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  team_id text not null,
  event_type text not null,
  request_id text,
  payload jsonb default '{}',
  created_at timestamptz default now()
);

create index if not exists chunks_embedding_idx
on chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create index if not exists teams_user_id_idx on teams(user_id);
create index if not exists agents_team_id_idx on agents(team_id);
create index if not exists documents_team_id_idx on documents(team_id);
create index if not exists chunks_document_id_idx on chunks(document_id);
create index if not exists sessions_user_id_idx on sessions(user_id);
create index if not exists sessions_team_id_idx on sessions(team_id);
create index if not exists queries_session_id_idx on queries(session_id);
create index if not exists agent_traces_query_id_idx on agent_traces(query_id);
create index if not exists session_logs_session_id_idx on session_logs(session_id);
create index if not exists session_logs_team_id_idx on session_logs(team_id);
create index if not exists session_logs_created_at_idx on session_logs(created_at desc);

alter table teams enable row level security;
alter table agents enable row level security;
alter table documents enable row level security;
alter table chunks enable row level security;
alter table sessions enable row level security;
alter table queries enable row level security;
alter table agent_traces enable row level security;

create policy "teams_select_own" on teams
for select using (auth.uid() = user_id);

create policy "teams_insert_own" on teams
for insert with check (auth.uid() = user_id);

create policy "teams_update_own" on teams
for update using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "teams_delete_own" on teams
for delete using (auth.uid() = user_id);

create policy "agents_all_via_team_owner" on agents
for all
using (
  exists (
    select 1 from teams
    where teams.id = agents.team_id
      and teams.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from teams
    where teams.id = agents.team_id
      and teams.user_id = auth.uid()
  )
);

create policy "documents_all_via_team_owner" on documents
for all
using (
  exists (
    select 1 from teams
    where teams.id = documents.team_id
      and teams.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from teams
    where teams.id = documents.team_id
      and teams.user_id = auth.uid()
  )
);

create policy "chunks_all_via_document_owner" on chunks
for all
using (
  exists (
    select 1
    from documents
    join teams on teams.id = documents.team_id
    where documents.id = chunks.document_id
      and teams.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from documents
    join teams on teams.id = documents.team_id
    where documents.id = chunks.document_id
      and teams.user_id = auth.uid()
  )
);

create policy "sessions_all_own" on sessions
for all
using (auth.uid() = user_id)
with check (
  auth.uid() = user_id
  and exists (
    select 1 from teams
    where teams.id = sessions.team_id
      and teams.user_id = auth.uid()
  )
);

create policy "queries_all_via_session_owner" on queries
for all
using (
  exists (
    select 1 from sessions
    where sessions.id = queries.session_id
      and sessions.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from sessions
    where sessions.id = queries.session_id
      and sessions.user_id = auth.uid()
  )
);

create policy "agent_traces_all_via_query_owner" on agent_traces
for all
using (
  exists (
    select 1
    from queries
    join sessions on sessions.id = queries.session_id
    where queries.id = agent_traces.query_id
      and sessions.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from queries
    join sessions on sessions.id = queries.session_id
    where queries.id = agent_traces.query_id
      and sessions.user_id = auth.uid()
  )
);

create or replace function match_chunks(
  query_embedding vector(384),
  filter_team_id uuid,
  match_count int default 5
)
returns table (
  id uuid,
  document_id uuid,
  filename text,
  chunk_index int,
  content text,
  metadata jsonb,
  similarity float
)
language sql
stable
as $$
  select
    chunks.id,
    chunks.document_id,
    documents.filename,
    chunks.chunk_index,
    chunks.content,
    chunks.metadata,
    1 - (chunks.embedding <=> query_embedding) as similarity
  from chunks
  join documents on documents.id = chunks.document_id
  where documents.team_id = filter_team_id
  order by chunks.embedding <=> query_embedding
  limit match_count;
$$;
