Audit Scope

  I did not find a separate attached MVP spec file in the repo. I audited against your checklist and the repo docs. The implemented
  product is closer to a single-user/team document RAG app than a multi-agent, multi-model RAG platform.

  Command Results

  | Command | Result |
  |---|---|
  | npm test in frontend | Pass: 8 tests |
  | npm run build in frontend | Pass |
  | npm run lint in frontend | Fail: next lint is invalid under current Next 16 setup |
  | npx tsc --noEmit in frontend | Fail: TS5101 on deprecated baseUrl in frontend/tsconfig.json:3 |
  | pytest tests/unit in backend | Pass: 35 tests |
  | pytest in backend | Broken/hangs at integration tests |
  | timeout 10s pytest tests/integration/test_sessions.py -vv | Timeout at first test |
  | docker build --check ... | Fail: Docker daemon socket unavailable |

  Implementation Matrix

  | Area | Status | Evidence | Works | Does Not Work / Blocks | Next Action |
  |---|---|---|---|---|---|
  | 1. Setup/build | Partial/Broken | frontend/package.json:4, backend/requirements.txt:1 | Frontend tests/build; backend unit tests |
  Lint, typecheck, integration tests, Docker check fail/hang. Blocks MVP confidence. | Fix lint script, TS config, integration hang. |
  | 2. Supabase auth | Partial | frontend/app/login/page.tsx:22, frontend/app/register/page.tsx:99, frontend/app/profile/page.tsx:193,
  backend/core/auth.py:29 | Register/login/logout/profile/protected frontend routes exist. Backend validates bearer token. | No backend
  profile route, no auth E2E proof, protected route is client-side only with middleware refresh. Partial MVP blocker. | Add auth E2E and
  backend profile/me endpoint if spec requires. |
  | 3. DB schema | Partial | supabase/migrations/001_initial_schema.sql:3 | teams, documents, chunks, sessions, queries, session_logs
  exist. | Missing agents, agent config, messages, traces table in Supabase, scorecards table, analytics tables. Blocks multi-agent MVP. |
  Add complete MVP schema migrations. |
  | 4. RLS/storage security | Partial | supabase/migrations/001_initial_schema.sql:75, supabase/
  migrations/003_file_storage_and_document_hashes.sql:3 | RLS exists for core tables; private storage bucket exists. | No storage object
  policies found; backend uses service role and app-level checks. Security blocker for real Supabase storage. | Add storage RLS policies
  and service-role audit. |
  | 5. Agent team CRUD | Missing | Routes only include ingest/query/sessions/dashboard/observability in backend/main.py:50 | None. | No
  team UI/API beyond auto-created “Demo Workspace” in backend/db/supabase.py:55. Blocks MVP. | Build teams + agents CRUD. |
  | 6. Per-agent config | Missing | Search found no agents schema/routes/components. | None. | No role, system prompt, model selector,
  response style. Blocks MVP. | Add agents table, API, UI editor. |
  | 7. Ollama/local model | Missing | LLM clients are Groq/Sarvam: backend/rag/generator.py:334, backend/llms/groq_client.py:13 | Hosted
  Groq/Sarvam path plus extractive fallback. | No Ollama client/config. Blocks local-model MVP. | Add Ollama adapter and health check. |
  | 8. Per-agent routing | Missing | backend/rag/generator.py:334 accepts optional model but route never passes agent config. | Single
  global RAG_MODEL. | No per-agent model mapping. Blocks MVP. | Route model choice through agent execution. |
  | 9. Multi-agent orchestration | Missing | No active orchestration routes/modules found. | None. | No sequential/debate/hierarchical
  runtime. Blocks MVP. | Implement minimal sequential orchestrator first. |
  | 10. KB uploads PDF/image | Partial | backend/core/config.py:61, frontend/components/knowledge/UploadPanel.tsx:221, backend/rag/
  embedanything_pipeline.py:54 | PDF/image/text accepted and indexed through EmbedAnything/Qdrant path. | Upload does not persist original
  file to Supabase storage in current route; insert_document passes no storage_path and upload_document_file is unused. Demo source “Open
  file” likely fails. | Store file before indexing and save storage_path. |
  | 11. Chunking/embeddings/hybrid/citations | Partial | backend/rag/embedanything_pipeline.py:54, backend/rag/retriever.py:289, supabase/
  migrations/002_hybrid_search.sql:21 | Semantic chunks and Qdrant vector retrieval exist; source previews returned. | Hybrid SQL exists
  but runtime retriever uses Qdrant only. Citations are previews, not robust source spans/pages. Blocks high-quality MVP. | Choose Qdrant
  or Supabase hybrid and wire citations with metadata/page. |
  | 12. Browser chat/live trace | Partial | frontend/app/chat/page.tsx:20, backend/observability.py:143 | Chat calls backend and displays
  answer/sources. | No live trace UI or streaming trace feed. | Add trace endpoint and UI panel. |
  | 13. Research history/full traces | Partial | frontend/app/history/page.tsx:256, backend/routers/query.py:321 | Query history by
  session exists. | Requires manual session ID; no full trace retrieval UI/API. | List sessions and expose trace details. |
  | 14. JSON/PDF export | Missing | No export routes/components found. | None. | Blocks export requirement. | Add JSON export first; PDF
  later. |
  | 15. Analytics dashboard | Partial | backend/routers/dashboard.py:118, frontend/app/dashboard/page.tsx:361 | Session-scoped query
  count/latency/average score chart. | Manual session ID; no platform/team/agent analytics. | Add scoped analytics queries and session
  picker. |
  | 16. Research scorecard | Partial/Missing | Score fields in supabase/migrations/001_initial_schema.sql:43; query saves scorecard=None
  in backend/routers/query.py:250 | DB columns can store scores. | No scorecard calculation/UI. Blocks scorecard requirement. | Add
  evaluator and scorecard display. |
  | 17. MVP demo readiness | Broken | docs/DEMO.md:189 | Basic intended flow documented. | Integration tests hang; file-open likely
  broken; no agents/Ollama/export. Blocks MVP demo. | Stabilize single RAG demo, then add agents. |
  | 18. Security/privacy | Partial/Risky | backend/main.py:65, backend/observability.py:29 | Redacts sensitive keys; CORS explicit. |
  Observability can log raw payloads if enabled; storage policy missing; service-role app checks must be exhaustive. | Lock raw payload
  logging off, add policies/tests. |
  | 19. Non-MVP distractions | Present | backend/observability.py:69, frontend/components/layout/Header.tsx:119, Cloudflare in compose |
  Observability foundation exists. | Distracts from missing agent MVP; read-only UI suggests unavailable traces/teams search. | De-scope
  or hide until core MVP works. |

  P0 Issues

  1. Missing core multi-agent product: no agents schema/API/UI, no team CRUD, no per-agent config, no orchestration.
  2. Ollama/local model integration is absent.
  3. Backend integration tests hang; full backend test suite does not complete.
  4. File storage flow is incomplete: uploaded original files are not stored, so signed source-file download is not reliable.
  5. Supabase schema is missing MVP tables for agents, messages, traces, scorecards, and analytics.

  P1 Issues

  1. Frontend lint and standalone typecheck fail.
  2. Hybrid retrieval is defined in SQL but not used by runtime retrieval.
  3. History/dashboard require manual session IDs and do not expose full trace history.
  4. Research scorecard fields exist but scorecards are never produced.
  5. Storage object policies are not present.

  P2 Issues

  1. Header has read-only search for “traces, teams, or documents.”
  2. ClickHouse observability is ahead of the core MVP surface.
  3. Docs overclaim current architecture in places, including team upload flow and CI workflow references.
  4. Docker build checks could not run because Docker daemon is unavailable.

  Shortest Path To MVP Demo

  1. Stabilize current single-agent RAG baseline: fix integration test hang, lint script, TS config, and file storage.
  2. Add minimal agents table/API/UI: name, role, system prompt, model provider/model, response style.
  3. Add Ollama client and model registry; keep Groq/Sarvam as optional hosted providers.
  4. Implement sequential orchestration only: run selected agents in order, persist each step as trace/message rows.
  5. Add chat UI agent-team selector plus live trace panel.
  6. Add history detail page with full trace and JSON export.
  7. Add simple scorecard evaluator and dashboard cards by session/team/agent.

  Current repo can demo document upload/query/history/dashboard if the environment is configured and integration issues are fixed, but it
  is not yet a Multi-Agent Multi-Model RAG Platform MVP.





intern audit
• I audited the repo against the MVP checklist. Short verdict: this is a partial single-user RAG demo, not yet the requested multi-agent
  MVP.

  The biggest missing pieces are agent/team management, Ollama/local model routing, multi-agent orchestration, live traces, scorecards,
  exports, and real Supabase file storage wiring.

  Project Setup Status
  Status: Partial / Broken

  Findings:

  - Frontend is Next.js App Router + React + TypeScript.
  - Backend is FastAPI, not Next.js API routes.
  - No Tailwind config or Tailwind dependency found.
  - Frontend has scripts for dev, build, lint, test, but lint is broken with Next 16.
  - Frontend build and tests pass.
  - Backend unit tests pass, but integration/full backend pytest hangs.

  Evidence:

  - Scripts: frontend/package.json:5
  - Backend deps: backend/requirements.txt:1
  - Next rewrite exists: frontend/next.config.mjs:6
  - Commands run:
      - npm test passed: 8 tests
      - npm run build passed
      - npm run lint failed: Invalid project directory ... /frontend/lint
      - pytest tests/unit -q passed: 35 tests
      - pytest / integration tests hung at test_dashboard_history.py

  Implemented

  - Supabase browser/server client setup exists.
  - Login/register/logout/profile pages exist.
  - Protected frontend pages exist, but protection is client-side.
  - Backend API auth validates Supabase bearer tokens.
  - Basic schema exists for teams, documents, chunks, sessions, queries.
  - Upload UI exists for PDF/image/TXT.
  - Query API retrieves from Qdrant and generates one final answer.
  - History and dashboard pages exist, but require manual session IDs.
  - Basic analytics exist: total queries, average latency, average score, queries over time.

  Partially Implemented / Broken

  - Upload indexing writes to Qdrant, but not to Supabase Storage. upload_document_file() exists in backend/db/supabase.py:278, but /
    ingest never calls it and inserts documents with no storage_path backend/routers/ingest.py:171. Download later fails if storage_path
    is missing backend/db/supabase.py:302.
  - Hybrid search SQL exists, but active retrieval uses only Qdrant vector search backend/rag/retriever.py:20.
  - Score columns exist, but chat saves scorecard=None backend/routers/query.py:250.
  - Dashboard/history are session-scoped and require users to paste a UUID frontend/app/history/page.tsx:10, frontend/app/dashboard/
    page.tsx:12.
  - RLS exists for core tables, but session_logs has no RLS enable/policies, and storage policies are missing.

  Missing

  - Team creation/edit/delete UI and backend routes.
  - Agent table, agent config, role, model, system prompt, response style.
  - Collaboration rule storage: sequential/debate/hierarchical.
  - Ollama integration and local model registry.
  - Per-agent model routing.
  - Multi-agent orchestration.
  - Agent traces and live trace UI.
  - Messages table or complete chat transcript model.
  - Scorecard generation, persistence table, chat display, history display.
  - JSON/PDF exports.
  - Image OCR flow is not wired through image_text.py; image support depends on embed-anything behavior.
  - Profile table, if app-specific profile metadata is needed.
  - Storage RLS/policies for uploaded files.

  Critical Wiring Issues

  - The app auto-creates a fake “Demo Workspace” per user instead of real team management backend/db/supabase.py:65.
  - Chat request only accepts query, session_id, and top_k; no team_id, no agent config, no collaboration mode backend/routers/
    query.py:24.
  - Query execution is single-pass retrieval plus generate_answer() backend/routers/query.py:135, backend/routers/query.py:223.
  - LLM path is Groq/Sarvam or extractive fallback, not Ollama backend/rag/generator.py:8.
  - QDRANT_URL defaults to https://qdrant:6333, while the Docker Qdrant service is plain HTTP, likely breaking runtime connectivity.

  Final Implementation Matrix

  | Area | Status | Evidence | Blocking? | Next Action |
  |---|---|---|---|---|
  | Project setup | Partial/Broken | build passes, lint fails, backend integration hangs | Yes | Fix lint script and hanging tests |
  | Auth | Partial | login/register/profile exist | No | Add server-side redirects and better signup states |
  | Database schema | Partial | core tables only | Yes | Add agents, traces, messages, scorecards |
  | Team creation | Missing | only auto Demo Workspace | Yes | Build CRUD routes/UI |
  | Agent config | Missing | no agents table/routes/UI | Yes | Add agent schema + forms |
  | Ollama/model routing | Missing | Groq/Sarvam only | Yes | Add Ollama provider + model registry |
  | Multi-agent orchestration | Missing | single generate_answer() | Yes | Implement sequential MVP first |
  | Uploads | Partial/Broken | indexes, but no file storage | Yes | Store files in Supabase Storage |
  | RAG/chunking/embeddings | Partial | Qdrant embed-anything | No | Persist chunk/source metadata and use hybrid if claimed |
  | Chat | Partial | no team/agent selection | Yes | Connect chat to team + orchestrator |
  | Live trace | Missing | no trace schema/UI | Yes | Persist per-agent runs |
  | History | Partial | manual session list only | No | Add session list/detail |
  | Exports | Missing | no routes/UI | No | Add JSON first, PDF later |
  | Analytics | Partial | basic session metrics | No | Add real model/trace breakdown |
  | Scorecard | Missing | scorecard=None | No | Generate and persist scores |
  | Security/RLS | Partial | core RLS, no storage policies | Yes | Add storage policies and RLS for all exposed tables |

  Priority Ranking

  P0 MVP blockers:

  - Add real team + agent schema and CRUD.
  - Add Ollama/local model provider and per-agent model routing.
  - Implement sequential multi-agent orchestration and trace persistence.
  - Fix upload storage wiring so source files can be reopened.
  - Fix backend integration test hang.
  - Add storage policies and close RLS gaps.

  P1 major MVP gaps:

  - Scorecard generation and display.
  - History detail with full answer, citations, agent traces.
  - JSON export.
  - Remove manual session-ID workflow from history/dashboard.
  - Wire hybrid retrieval or stop claiming it.

  P2 polish/post-MVP:

  - Debate and hierarchical modes.
  - Advanced analytics.
  - ClickHouse/cloudflared observability hardening.
  - PDF export.
  - Template marketplace / external integrations.

  E2E MVP Demo Result
  Status: Fail

  First blocking failure: users cannot create the required Research Demo Team or define Researcher/Critic/Synthesizer agents. Even after
  that, Ollama routing and multi-agent orchestration are absent.