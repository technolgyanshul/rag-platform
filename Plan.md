This audit is solid. The key conclusion is:

**The repo is not yet a multi-agent multi-model RAG MVP. It is currently a single-user/single-team document RAG app with partial upload, query, history, and dashboard support.**

Here is the **next Codex handoff prompt** I would use to move from audit → implementation.

---

# Codex Implementation Handoff: Build the Shortest Path to MVP

You have already audited the repo. Now implement the shortest path to a working MVP demo for the Multi-Agent Multi-Model RAG Platform.

The current app has partial single-agent RAG functionality, but is missing the core product requirements: agent teams, per-agent model config, Ollama/local models, orchestration, trace persistence, scorecards, and usable history/export.

Do not implement advanced features. Focus only on the MVP demo path.

---

## Implementation Priority

Implement in this order:

1. Fix baseline stability.
2. Fix file storage.
3. Add agent/team schema.
4. Add team + agent CRUD APIs.
5. Add minimal UI for team + agent creation.
6. Add Ollama integration.
7. Add sequential multi-agent orchestration.
8. Persist traces.
9. Add chat team selector + trace panel.
10. Add history detail + JSON export.
11. Add simple scorecard.

---

# Phase 1 — Stabilize Existing App

## Tasks

* [ ] Fix frontend lint script.

  * Current issue: `next lint` is invalid under current Next 16 setup.
  * Replace with a valid lint command for the repo’s Next.js version.
* [ ] Fix TypeScript config.

  * Current issue: `TS5101` on deprecated `baseUrl` in `frontend/tsconfig.json`.
* [ ] Investigate backend integration test hang.

  * `pytest tests/integration/test_sessions.py -vv` times out at first test.
  * Identify whether this is due to:

    * external service dependency,
    * Supabase connection,
    * Qdrant connection,
    * async deadlock,
    * missing env var,
    * test fixture issue.
* [ ] Ensure these commands pass or fail with clear documented reasons:

  * `npm test`
  * `npm run build`
  * `npm run lint`
  * `npx tsc --noEmit`
  * `pytest tests/unit`
  * `pytest tests/integration/test_sessions.py -vv`

## Acceptance Criteria

* Frontend build still passes.
* Frontend lint command no longer fails because of invalid Next command.
* TypeScript check either passes or has only documented non-blocking errors.
* Backend integration test hang root cause is identified.
* No unrelated feature work in this phase.

---

# Phase 2 — Fix File Upload Storage

Current problem: uploads are indexed, but original files are not reliably persisted to Supabase Storage. `upload_document_file` appears unused, and `insert_document` does not receive `storage_path`.

## Tasks

* [ ] Locate current ingest/upload route.
* [ ] Store original uploaded file in Supabase Storage before or during indexing.
* [ ] Save `storage_path` in the documents table.
* [ ] Ensure uploaded files are linked to:

  * user,
  * document record,
  * team/workspace if applicable.
* [ ] Make source file opening/download work from the UI.
* [ ] Add storage error handling.
* [ ] Add or update tests for:

  * successful upload,
  * failed storage upload,
  * document DB record includes storage path.

## Acceptance Criteria

* Uploading a PDF stores the original file.
* Uploading an image stores the original file.
* Document metadata includes a valid storage path.
* Source “Open file” works or returns a clear error.
* No orphaned DB document record is created if storage/indexing fails halfway.

---

# Phase 3 — Add MVP Database Schema

Current missing schema: `agents`, full `messages`, `agent_traces`, `scorecards`, analytics support.

Create a new Supabase migration.

## Required Tables

### `agents`

```sql
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
```

### `messages`

Use if current `queries` table is insufficient.

```sql
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  role text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

### `agent_traces`

```sql
create table if not exists public.agent_traces (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  query_id uuid,
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
```

### `scorecards`

```sql
create table if not exists public.scorecards (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  query_id uuid,
  overall_quality integer check (overall_quality between 1 and 10),
  citation_accuracy integer check (citation_accuracy between 1 and 10),
  insight_depth integer check (insight_depth between 1 and 10),
  model_contribution_breakdown jsonb not null default '{}'::jsonb,
  notes text,
  created_at timestamptz not null default now()
);
```

## RLS

Add RLS policies so users can only access agents/traces/messages/scorecards belonging to their own teams/sessions.

## Acceptance Criteria

* Migration applies cleanly.
* RLS enabled.
* Current app still works.
* Existing sessions/queries are not broken.
* New tables support the MVP flow.

---

# Phase 4 — Add Team + Agent APIs

Current issue: no real team CRUD, no agent CRUD.

## Required API Endpoints

Add backend routes for:

### Teams

* [ ] `GET /teams`
* [ ] `POST /teams`
* [ ] `GET /teams/{team_id}`
* [ ] `PATCH /teams/{team_id}`
* [ ] `DELETE /teams/{team_id}`

### Agents

* [ ] `GET /teams/{team_id}/agents`
* [ ] `POST /teams/{team_id}/agents`
* [ ] `PATCH /teams/{team_id}/agents/{agent_id}`
* [ ] `DELETE /teams/{team_id}/agents/{agent_id}`

## Validation

* [ ] Require authenticated user.
* [ ] Verify team ownership.
* [ ] Validate model provider.
* [ ] Validate model name.
* [ ] Require at least one agent for chat.
* [ ] Recommended MVP default: 3 agents:

  * Researcher
  * Critic
  * Synthesizer

## Acceptance Criteria

* User can create a team through API.
* User can add multiple agents.
* User can assign different models per agent.
* User cannot access another user’s team.
* Delete team cascades agents safely.

Follow-up hardening:

1. Add a live-Supabase integration check for cascade behavior.
2. Add API contract assertions for delete response semantics if strict status code requirements are needed.

---

# Phase 5 — Add Team + Agent UI

Current issue: no frontend team creation/agent configuration flow.

## Required Pages

### `/teams`

* [ ] List user teams.
* [ ] Show team name.
* [ ] Show research domain.
* [ ] Show collaboration rule.
* [ ] Show agent count.
* [ ] Create team button.

### `/teams/new`

* [ ] Create team form.
* [ ] Fields:

  * team name,
  * research domain,
  * collaboration rule.
* [ ] Default collaboration rule: sequential.
* [ ] After team creation, redirect to team detail/editor.

### `/teams/[id]`

* [ ] Show team metadata.
* [ ] Edit team name/domain/rule.
* [ ] List agents.
* [ ] Add/edit/delete agents.
* [ ] Agent fields:

  * name,
  * role,
  * system prompt,
  * provider,
  * model name,
  * response style,
  * execution order.

## Acceptance Criteria

User can create this demo team from UI:

```txt
Team: Research Demo Team
Domain: Technical research
Rule: Sequential

Agent 1:
Name: Researcher
Role: Researcher
Provider: ollama
Model: llama3.1

Agent 2:
Name: Critic
Role: Critic
Provider: ollama
Model: gemma2

Agent 3:
Name: Synthesizer
Role: Synthesizer
Provider: ollama
Model: phi3
```

---

# Phase 6 — Add Ollama Integration

Current issue: LLM clients are Groq/Sarvam/extractive fallback. No Ollama adapter exists.

## Tasks

* [ ] Add `OllamaClient`.
* [ ] Support configurable base URL:

  * default: `http://localhost:11434`
* [ ] Add model generation method:

  * input: prompt, model name, options.
  * output: text.
* [ ] Add health/model list endpoint or helper.
* [ ] Handle:

  * Ollama not running,
  * model not pulled,
  * timeout,
  * invalid response.
* [ ] Keep Groq/Sarvam optional, but core MVP should work without paid APIs.

## Suggested API

```python
class OllamaClient:
    def __init__(self, base_url: str):
        ...

    async def generate(self, model: str, prompt: str, system_prompt: str | None = None) -> str:
        ...

    async def list_models(self) -> list[str]:
        ...
```

## Acceptance Criteria

* App can call local Ollama.
* Each agent can use its own configured Ollama model.
* Missing model errors are user-readable.
* No paid API key is required for MVP chat.

---

# Phase 7 - Implement Multi-Architecture Orchestration

Runtime scope: sequential, debate, and hierarchical orchestration are implemented together.

Detailed implementation plan: `Implement Multi-Architecture Orchestration.md`.

## Flow

For a user query:

1. Validate authenticated user.
2. Load selected team.
3. Load agents ordered by `execution_order`.
4. Retrieve RAG context.
5. Run each agent in sequence:

   * pass user query,
   * pass retrieved context,
   * pass previous agent outputs,
   * use the agent’s system prompt,
   * use the agent’s configured model.
6. Persist one `agent_traces` row per agent.
7. Generate final answer from the last agent or a final synthesis step.
8. Save assistant message/query result.
9. Generate scorecard.
10. Return final answer, citations, traces, scorecard.

## Agent Prompt Template

Use something like:

```txt
You are {agent_name}, acting as {agent_role}.

System instructions:
{system_prompt}

Research domain:
{team_domain}

User query:
{query}

Retrieved context:
{context}

Previous agent outputs:
{previous_outputs}

Your task:
Respond according to your role. Use only supported evidence from the retrieved context where possible.
```

## Acceptance Criteria

* Three configured agents run in order.
* Each agent uses its assigned model.
* Each step is saved in `agent_traces`.
* Final answer is returned to chat.
* If one agent fails, the error is saved and surfaced clearly.

---

# Phase 8 — Add Chat Team Selector + Trace Panel

Current chat works only as a basic RAG interface.

## Tasks

* [ ] Add team selector on chat page.
* [ ] Require selected team before asking a question.
* [ ] Send `team_id` with chat request.
* [ ] Show live or post-response trace panel.
* [ ] Trace panel should show:

  * agent name,
  * role,
  * model provider,
  * model name,
  * status,
  * latency,
  * output preview,
  * citations if available.

## MVP Version

Streaming live trace is not required yet. A post-response trace panel is acceptable for the first MVP demo.

## Acceptance Criteria

* User selects team.
* User asks query.
* UI displays final answer.
* UI displays each agent’s contribution.
* UI displays source citations.

---

# Phase 9 — Add History Detail + JSON Export

Current issue: history requires manual session ID and does not expose full trace.

## Tasks

* [ ] Add session list page or improve existing history page.
* [ ] Add history detail route:

  * `/history/[session_id]`
* [ ] Show:

  * query,
  * final answer,
  * team used,
  * date/time,
  * scorecard,
  * agent trace,
  * citations.
* [ ] Add JSON export endpoint:

  * `GET /sessions/{session_id}/export.json`
* [ ] Export should include:

  * session metadata,
  * messages/queries,
  * final answers,
  * agent traces,
  * scorecards,
  * citations.

## Acceptance Criteria

* User can open a previous session without manually entering ID.
* Full agent trace is visible.
* JSON export downloads valid structured JSON.
* User cannot export another user’s session.

---

# Phase 10 — Add Simple Research Scorecard

Current issue: score fields exist, but no scorecard is produced.

## MVP Scorecard Logic

Implement a simple deterministic evaluator first.

Example:

```txt
overall_quality:
- base 5
- +1 if answer has citations
- +1 if at least 2 agents contributed
- +1 if final answer is longer than a minimal threshold
- +1 if retrieved context was used
- cap at 10

citation_accuracy:
- 8 if citations exist and source chunks were retrieved
- 5 if sources exist but weak metadata
- 2 if no citations

insight_depth:
- based on answer length, agent diversity, and whether critic/synthesizer contributed
```

This can later be replaced by an LLM evaluator.

## Tasks

* [ ] Generate scorecard after each query.
* [ ] Save to `scorecards`.
* [ ] Return scorecard in chat response.
* [ ] Show scorecard in chat.
* [ ] Show scorecard in history detail.
* [ ] Include scorecard in JSON export.

## Acceptance Criteria

* Every completed query gets a scorecard.
* Scorecard is not hardcoded static data.
* Scorecard appears in chat/history/export.

---

# Final MVP Demo Acceptance Test

After implementation, verify this exact flow:

```txt
1. User registers.
2. User logs in.
3. User creates Research Demo Team.
4. User adds Researcher, Critic, Synthesizer agents.
5. Each agent uses a different Ollama model.
6. User uploads a PDF.
7. User uploads an image.
8. User opens chat.
9. User selects Research Demo Team.
10. User asks:
    “Summarize the uploaded documents and identify contradictions, missing assumptions, and the strongest evidence.”
11. System retrieves document chunks.
12. Agents run sequentially.
13. UI shows each agent trace.
14. Final answer includes citations.
15. Scorecard appears.
16. History page shows the session.
17. History detail shows full trace.
18. JSON export works.
```

---

# Do Not Implement Yet

Defer these until after MVP:

* Debate orchestration
* Hierarchical orchestration
* Agent marketplace/templates
* Webhooks
* Notion/Google Docs export
* A/B testing
* Advanced analytics
* Team collaboration
* Multi-user workspaces
* Custom API access
* ClickHouse-heavy observability UI
* Advanced visual collaboration graph

---

# Final Output Required From Codex

After implementation, report:

```md
## Changes Made
- ...

## Files Modified
- ...

## New Migrations
- ...

## Commands Run
| Command | Result |
|---|---|

## MVP Demo Status
| Step | Status | Notes |
|---|---|---|

## Remaining P0 Issues
- ...

## Remaining P1 Issues
- ...

## Manual Setup Required
- Ollama models to pull:
  - llama3.1
  - gemma2
  - phi3
- Env vars:
  - ...
```
