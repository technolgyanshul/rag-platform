alter table public.teams
  add column if not exists collaboration_rule text not null default 'sequential';

alter table public.teams
  drop constraint if exists teams_collaboration_rule_check;

alter table public.teams
  add constraint teams_collaboration_rule_check
  check (collaboration_rule in ('sequential', 'debate', 'hierarchical'));

alter table public.agents
  add column if not exists provider_base_url text,
  add column if not exists provider_passcode text;
