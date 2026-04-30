create table if not exists session_logs (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  team_id text not null,
  event_type text not null,
  request_id text,
  payload jsonb default '{}',
  created_at timestamptz default now()
);

create index if not exists session_logs_session_id_idx on session_logs(session_id);
create index if not exists session_logs_team_id_idx on session_logs(team_id);
create index if not exists session_logs_created_at_idx on session_logs(created_at desc);
