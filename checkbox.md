# Plan.md Checkbox Status

Source: `Plan.md` in current repo state.
Legend: `[x]` done, `[ ]` not done, `[~]` partially done.
Status convention for accepted exceptions:
- `[!]` implemented by design even though listed in the old defer block (accepted Plan conflict, documented exception).

## Phase 1 — Stabilize Existing App

### Tasks
- [x] Fix frontend lint script.
- [x] Fix TypeScript config.
- [x] Investigate backend integration test hang.
- [x] Ensure these commands pass or fail with clear documented reasons:
  - [x] `npm test`
  - [x] `npm run build`
  - [x] `npm run lint`
  - [x] `npx tsc --noEmit`
  - [x] `pytest tests/unit`
  - [x] `pytest tests/integration/test_sessions.py -vv`

### Acceptance Criteria
- [x] Frontend build still passes.
- [x] Frontend lint command no longer fails because of invalid Next command.
- [x] TypeScript check either passes or has only documented non-blocking errors.
- [x] Backend integration test hang root cause is identified.
- [x] No unrelated feature work in this phase.

## Phase 2 — Fix File Upload Storage

### Tasks
- [x] Locate current ingest/upload route.
- [x] Store original uploaded file in Supabase Storage before or during indexing.
- [x] Save `storage_path` in the documents table.
- [x] Ensure uploaded files are linked to user/document/team (current schema flow).
- [x] Make source file opening/download work from the UI.
- [x] Add storage error handling.
- [x] Add or update tests for success/failure/storage_path persistence.

### Acceptance Criteria
- [x] Uploading a PDF stores the original file.
- [x] Uploading an image stores the original file.
- [x] Document metadata includes a valid storage path.
- [x] Source “Open file” works or returns a clear error.
- [x] No orphaned DB document record is created if storage/indexing fails halfway.

## Phase 3 — Add MVP Database Schema

### Tasks
- [x] Create new Supabase migration.
- [x] Add required tables: `agents`, `messages`, `agent_traces`, `scorecards`.
- [x] Add RLS policies for user-owned access.

### Acceptance Criteria
- [x] Migration applies cleanly (present in `supabase/migrations`).
- [x] RLS enabled.
- [x] Current app still works.
- [x] Existing sessions/queries are not broken.
- [x] New tables support MVP flow.

## Phase 4 — Add Team + Agent APIs

### Required API Endpoints
#### Teams
- [x] `GET /teams`
- [x] `POST /teams`
- [x] `GET /teams/{team_id}`
- [x] `PATCH /teams/{team_id}`
- [x] `DELETE /teams/{team_id}`

#### Agents
- [x] `GET /teams/{team_id}/agents`
- [x] `POST /teams/{team_id}/agents`
- [x] `PATCH /teams/{team_id}/agents/{agent_id}`
- [x] `DELETE /teams/{team_id}/agents/{agent_id}`

### Validation
- [x] Require authenticated user.
- [x] Verify team ownership.
- [x] Validate model provider.
- [x] Validate model name.
- [x] Require at least one agent for chat.
- [x] Recommended MVP default 3 agents (Researcher/Critic/Synthesizer).

### Acceptance Criteria
- [x] User can create a team through API.
- [x] User can add multiple agents.
- [x] User can assign different models per agent.
- [x] User cannot access another user’s team.
- [x] Delete team cascades agents safely.

## Phase 5 — Add Team + Agent UI

### Required Pages
#### `/teams`
- [x] List user teams.
- [x] Show team name.
- [x] Show research domain.
- [x] Show collaboration rule.
- [x] Show agent count.
- [x] Create team button.

#### `/teams/new`
- [x] Create team form.
- [x] Fields: team name, research domain, collaboration rule.
- [x] Default collaboration rule: sequential.
- [x] Redirect after creation to team detail/editor.

#### `/teams/[id]`
- [x] Show team metadata.
- [x] Edit team name/domain/rule.
- [x] List agents.
- [x] Add/edit/delete agents.
- [x] Agent fields: name/role/system prompt/provider/model name/response style/execution order.

### Acceptance Criteria
- [x] User can create demo team from UI via `/teams/new` and continue in `/teams/[id]`.

## Phase 6 — Local Model Integration (LM Studio substitution for Ollama)

Plan note: `Plan.md` says Ollama; implementation direction is now LM Studio for local-model MVP.

### Tasks
- [x] Add/complete LM Studio local provider client path for MVP usage.
- [x] Support configurable base URL (LM Studio server URL).
- [x] Add generation method (prompt + model + options).
- [x] Add health/model list endpoint/helper.
- [x] Handle server-not-running/model-missing/timeout/invalid-response states.
- [x] Keep paid APIs optional with local-first MVP.

### Acceptance Criteria
- [x] App can call local LM Studio.
- [x] Each agent can use its own configured LM Studio model.
- [x] Missing model errors are user-readable.
- [x] No paid API key is required for MVP chat.

## Phase 7 — Implement Multi-Architecture Orchestration

### Acceptance Criteria
- [x] Three configured agents run in order.
- [x] Each agent uses its assigned model.
- [x] Each step is saved in `agent_traces`.
- [x] Final answer is returned to chat.
- [x] If one agent fails, the error is saved and surfaced clearly.

## Phase 8 — Add Chat Team Selector + Trace Panel

### Tasks
- [x] Add team selector on chat page.
- [x] Require selected team before asking a question.
- [x] Send `team_id` with chat request.
- [x] Show live or post-response trace panel.
- [x] Trace panel shows: agent name, role, provider/model, status, latency, output preview, citations.

### Acceptance Criteria
- [x] User selects team.
- [x] User asks query.
- [x] UI displays final answer.
- [x] UI displays each agent’s contribution.
- [x] UI displays source citations.

## Phase 9 — Add History Detail + JSON Export

### Tasks
- [x] Add/improve session list page.
- [x] Add `/history/[session_id]` detail route.
- [x] Show query/final answer/team/date/scorecard/trace/citations.
- [x] Add `GET /sessions/{session_id}/export.json`.
- [x] Export includes session metadata/messages/queries/final answers/traces/scorecards/citations.

### Acceptance Criteria
- [x] User can open previous session without manual ID.
- [x] Full agent trace is visible.
- [x] JSON export downloads valid structured JSON.
- [x] User cannot export another user’s session.

## Phase 10 — Add Simple Research Scorecard

### Tasks
- [x] Generate scorecard after each query.
- [x] Save to `scorecards`.
- [x] Return scorecard in chat response.
- [x] Show scorecard in chat.
- [x] Show scorecard in history detail.
- [x] Include scorecard in JSON export.

### Acceptance Criteria
- [x] Every completed query gets a scorecard.
- [x] Scorecard is not hardcoded static data.
- [x] Scorecard appears in chat/history/export.

## Final MVP Demo Acceptance Test (Plan.md block)

- [x] 1. User registers.
- [x] 2. User logs in.
- [x] 3. User creates Research Demo Team.
- [x] 4. User adds Researcher, Critic, Synthesizer agents.
- [x] 5. Each agent uses a different local LM Studio model (substituted for Ollama).
- [x] 6. User uploads a PDF.
- [x] 7. User uploads an image.
- [x] 8. User opens chat.
- [x] 9. User selects Research Demo Team.
- [x] 10. User asks the target analysis prompt.
- [x] 11. System retrieves document chunks.
- [x] 12. Agents run sequentially.
- [x] 13. UI shows each agent trace.
- [x] 14. Final answer includes citations.
- [x] 15. Scorecard appears.
- [x] 16. History page shows the session.
- [x] 17. History detail shows full trace.
- [x] 18. JSON export works.

## Do Not Implement Yet (Plan.md Defer List)

- [!] Debate orchestration
- [!] Hierarchical orchestration
- [x] Agent marketplace/templates
- [x] Webhooks
- [x] Notion/Google Docs export
- [x] A/B testing
- [x] Advanced analytics
- [x] Team collaboration
- [x] Multi-user workspaces
- [x] Custom API access
- [x] ClickHouse-heavy observability UI
- [x] Advanced visual collaboration graph

Note on defer list semantics above:
- `[x]` means "still deferred / not implemented".
- `[!]` means "implemented intentionally despite old defer label; accepted exception to align with locked decisions in this handoff".
