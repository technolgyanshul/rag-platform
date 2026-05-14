# Phase 8 Chat Team Selector + Trace Panel Handoff

## Goal

Make `/chat` team-aware and demo-ready: select a team, ask a question, receive a final answer, and inspect a post-response trace panel with each agent contribution and citations.

## Coordination Rules

- Backend and frontend work are split across separate subagents with disjoint write scopes.
- Retrieval remains user-scoped for this MVP; `team_id` selects orchestration only.
- The chat session must be tied to the selected team. Team changes reset the active session.
- The UI must block query submission until a team is selected and has at least one agent.
- This file is the parent handoff and process log.

## Subagents

### Einstein - Backend Contract + Validation

Status: completed

Ownership:
- `backend/routers/query.py`
- `backend/routers/sessions.py`
- `backend/db/supabase.py` if needed
- `backend/tests/**`

Expected output:
- `POST /sessions` accepts and returns `team_id`.
- `POST /query` requires `team_id`.
- Query validates team ownership.
- Query rejects existing session/team mismatch with HTTP 409.
- Query creates missing sessions with the selected team.
- Existing no-agent and orchestration trace/citation behavior remains intact.

Process:
- Read the graph report and wiki before source inspection.
- Used Graphify to locate query/session/team relationships.
- Added failing tests for missing `team_id`, session/team mismatch, and session response `team_id`.
- Implemented `team_id` on `/sessions` and `/query`, ownership validation, missing-session creation with team, and mismatch 409 handling.
- Updated existing integration tests to use the new payload contract.

Verification reported by subagent:
- `cd backend && pytest` -> `103 passed, 1 skipped`.
- Focused backend rerun -> `26 passed`.
- `graphify update .` -> passed.

### Planck - Frontend Team Selector + Trace Panel

Status: completed

Ownership:
- `frontend/app/chat/page.tsx`
- `frontend/components/chat/**`
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- frontend tests

Expected output:
- Chat loads teams and agents.
- Submit is disabled until a team with at least one agent is selected.
- Session creation and query submission include `team_id`.
- Team changes reset the active session.
- Trace panel renders agent name, role, provider, model, status, latency, output preview, and citations.

Process:
- Read the graph report and wiki before source inspection.
- Used Graphify to locate chat/API/type nodes.
- Added failing API tests for `team_id` in session creation and query submission.
- Added chat team selector, agent loading, disabled submit guardrails, session reset on team changes, and trace rendering.
- Numbered source list entries so trace citations map back to visible source numbers.

Verification reported by subagent:
- `cd frontend && npm test -- lib/api.test.ts components/chat/TracePanel.test.tsx` -> 10 tests passed.
- `cd frontend && npm run lint` -> passed.
- `cd frontend && npx tsc --noEmit --incremental false` -> passed.
- `cd frontend && npm test` -> 12 tests passed.
- `graphify update .` -> passed.

## Parent Process Log

- Read `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` first per repo instructions.
- Queried Graphify for chat/session/team/trace relationships.
- Found `new.md` already existed as an empty added file and adopted it as the handoff artifact.
- Dispatched backend and frontend worker subagents with separate write scopes.
- Reviewed both subagent outputs and local diffs before final verification.

## Verification Plan

- `cd backend && pytest tests/integration/test_sessions.py tests/integration/test_query_requires_agents.py tests/integration/test_query_orchestration_modes.py`
- `cd frontend && npm test && npm run build`
- `graphify update .`

## Commit Plan

1. Backend team-aware sessions/query contract and tests.
2. Frontend team selector, session/query wiring, trace panel, and tests.
3. Graphify refresh and handoff updates if they are not naturally included above.
