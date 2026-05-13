create table if not exists public.agents (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null references public.teams(id) on delete cascade,
  name text not null,
  role text not null,
  system_prompt text not null default '',
  model_provider text not null default 'ollama',
  model_name text not null,
  response_style text,
  execution_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.agents
  add column if not exists team_id uuid references public.teams(id) on delete cascade,
  add column if not exists name text,
  add column if not exists role text,
  add column if not exists system_prompt text not null default '',
  add column if not exists model_provider text not null default 'ollama',
  add column if not exists model_name text,
  add column if not exists response_style text,
  add column if not exists execution_order integer not null default 0,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

update public.agents
set
  name = coalesce(name, 'Agent'),
  role = coalesce(role, 'assistant'),
  model_name = coalesce(model_name, 'unknown')
where name is null or role is null or model_name is null;

alter table public.agents
  alter column team_id set not null,
  alter column name set not null,
  alter column role set not null,
  alter column model_name set not null;

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  role text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.messages
  add column if not exists session_id uuid references public.sessions(id) on delete cascade,
  add column if not exists role text,
  add column if not exists content text,
  add column if not exists metadata jsonb not null default '{}'::jsonb,
  add column if not exists created_at timestamptz not null default now();

update public.messages
set
  role = coalesce(role, 'assistant'),
  content = coalesce(content, '')
where role is null or content is null;

alter table public.messages
  alter column session_id set not null,
  alter column role set not null,
  alter column content set not null;

create table if not exists public.agent_traces (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  query_id uuid references public.queries(id) on delete set null,
  agent_id uuid references public.agents(id) on delete set null,
  agent_name text not null,
  agent_role text not null,
  model_provider text not null,
  model_name text not null,
  input jsonb not null default '{}'::jsonb,
  output text not null default '',
  citations jsonb not null default '[]'::jsonb,
  latency_ms integer,
  status text not null default 'completed',
  error text,
  created_at timestamptz not null default now()
);

alter table public.agent_traces
  add column if not exists session_id uuid references public.sessions(id) on delete cascade,
  add column if not exists query_id uuid references public.queries(id) on delete set null,
  add column if not exists agent_id uuid references public.agents(id) on delete set null,
  add column if not exists agent_name text,
  add column if not exists agent_role text,
  add column if not exists model_provider text,
  add column if not exists model_name text,
  add column if not exists input jsonb not null default '{}'::jsonb,
  add column if not exists output text not null default '',
  add column if not exists citations jsonb not null default '[]'::jsonb,
  add column if not exists latency_ms integer,
  add column if not exists status text not null default 'completed',
  add column if not exists error text,
  add column if not exists created_at timestamptz not null default now();

update public.agent_traces
set
  agent_name = coalesce(agent_name, 'agent'),
  agent_role = coalesce(agent_role, 'assistant'),
  model_provider = coalesce(model_provider, 'ollama'),
  model_name = coalesce(model_name, 'unknown'),
  output = coalesce(output, ''),
  status = coalesce(status, 'completed')
where
  agent_name is null
  or agent_role is null
  or model_provider is null
  or model_name is null
  or output is null
  or status is null;

alter table public.agent_traces
  alter column session_id set not null,
  alter column agent_name set not null,
  alter column agent_role set not null,
  alter column model_provider set not null,
  alter column model_name set not null,
  alter column output set not null,
  alter column status set not null;

create table if not exists public.scorecards (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  query_id uuid references public.queries(id) on delete set null,
  overall_quality integer check (overall_quality between 1 and 10),
  citation_accuracy integer check (citation_accuracy between 1 and 10),
  insight_depth integer check (insight_depth between 1 and 10),
  model_contribution_breakdown jsonb not null default '{}'::jsonb,
  notes text,
  created_at timestamptz not null default now()
);

alter table public.scorecards
  add column if not exists session_id uuid references public.sessions(id) on delete cascade,
  add column if not exists query_id uuid references public.queries(id) on delete set null,
  add column if not exists overall_quality integer check (overall_quality between 1 and 10),
  add column if not exists citation_accuracy integer check (citation_accuracy between 1 and 10),
  add column if not exists insight_depth integer check (insight_depth between 1 and 10),
  add column if not exists model_contribution_breakdown jsonb not null default '{}'::jsonb,
  add column if not exists notes text,
  add column if not exists created_at timestamptz not null default now();

alter table public.scorecards
  alter column session_id set not null;

create index if not exists agents_team_order_idx
on public.agents(team_id, execution_order, created_at desc);

create index if not exists messages_session_created_idx
on public.messages(session_id, created_at desc);

create index if not exists agent_traces_session_created_idx
on public.agent_traces(session_id, created_at desc);
create index if not exists agent_traces_query_id_idx
on public.agent_traces(query_id);
create index if not exists agent_traces_agent_id_idx
on public.agent_traces(agent_id);

create index if not exists scorecards_session_created_idx
on public.scorecards(session_id, created_at desc);
create index if not exists scorecards_query_id_idx
on public.scorecards(query_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_agents_updated_at on public.agents;
create trigger set_agents_updated_at
before update on public.agents
for each row
execute function public.set_updated_at();

alter table public.agents enable row level security;
alter table public.messages enable row level security;
alter table public.agent_traces enable row level security;
alter table public.scorecards enable row level security;

drop policy if exists "agents_all_via_team_owner" on public.agents;
create policy "agents_all_via_team_owner" on public.agents
for all
using (
  exists (
    select 1 from public.teams
    where teams.id = agents.team_id
      and teams.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.teams
    where teams.id = agents.team_id
      and teams.user_id = auth.uid()
  )
);

drop policy if exists "messages_all_via_session_owner" on public.messages;
create policy "messages_all_via_session_owner" on public.messages
for all
using (
  exists (
    select 1 from public.sessions
    where sessions.id = messages.session_id
      and sessions.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.sessions
    where sessions.id = messages.session_id
      and sessions.user_id = auth.uid()
  )
);

drop policy if exists "agent_traces_all_via_session_owner" on public.agent_traces;
create policy "agent_traces_all_via_session_owner" on public.agent_traces
for all
using (
  exists (
    select 1 from public.sessions
    where sessions.id = agent_traces.session_id
      and sessions.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.sessions
    where sessions.id = agent_traces.session_id
      and sessions.user_id = auth.uid()
  )
);

drop policy if exists "scorecards_all_via_session_owner" on public.scorecards;
create policy "scorecards_all_via_session_owner" on public.scorecards
for all
using (
  exists (
    select 1 from public.sessions
    where sessions.id = scorecards.session_id
      and sessions.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.sessions
    where sessions.id = scorecards.session_id
      and sessions.user_id = auth.uid()
  )
);
