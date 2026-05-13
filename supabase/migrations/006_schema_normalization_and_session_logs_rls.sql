-- Normalize Phase 3 schema to MVP contract and fix public security lints.

-- agents.system_prompt should be non-null with default ''
update public.agents
set system_prompt = ''
where system_prompt is null;

alter table public.agents
  alter column system_prompt set default '',
  alter column system_prompt set not null;

-- Remove legacy ordering column to avoid ambiguity with execution_order.
alter table public.agents
  drop column if exists position;

-- agent_traces.query_id should be nullable for pre-persistence traces.
alter table public.agent_traces
  alter column query_id drop not null;

-- Ensure FK behavior is on delete set null for query_id.
alter table public.agent_traces
  drop constraint if exists agent_traces_query_id_fkey;
alter table public.agent_traces
  add constraint agent_traces_query_id_fkey
  foreign key (query_id) references public.queries(id) on delete set null;

alter table public.scorecards
  drop constraint if exists scorecards_query_id_fkey;
alter table public.scorecards
  add constraint scorecards_query_id_fkey
  foreign key (query_id) references public.queries(id) on delete set null;

-- Supabase linter: RLS must be enabled for public.session_logs.
alter table public.session_logs enable row level security;

drop policy if exists "session_logs_all_via_team_owner" on public.session_logs;
create policy "session_logs_all_via_team_owner" on public.session_logs
for all
using (
  exists (
    select 1 from public.teams
    where teams.id::text = session_logs.team_id
      and teams.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.teams
    where teams.id::text = session_logs.team_id
      and teams.user_id = auth.uid()
  )
);
