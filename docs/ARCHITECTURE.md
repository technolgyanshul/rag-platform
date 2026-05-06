# Architecture

## 1. System Overview

This project is a full-stack multi-agent RAG platform with:

- Frontend: Next.js (TypeScript) operator UI
- Backend: FastAPI API service
- Data layer: Supabase Postgres + pgvector
- Inference layer: Groq (Researcher/Critic/Synthesizer) + Sarvam (Judge)

Primary user flow:

1. Operator authenticates with Supabase Auth in frontend.
2. Frontend sends bearer token to backend APIs.
3. Backend validates token and resolves current user.
4. Backend enforces team/session ownership at repository boundary.
5. Retrieval and orchestration run, then results are persisted and returned.

## 2. Runtime Components

### Frontend (`frontend/`)

- Route pages (`frontend/app/*`) for login/register, knowledge ingest, chat, history, dashboard, team, and profile.
- Shared API client (`frontend/lib/api.ts`) injects bearer auth headers from Supabase session.
- Route protection (`frontend/components/auth/ProtectedPage.tsx`) gates non-auth pages.

### Backend (`backend/`)

- App bootstrap (`backend/main.py`) configures logging, CORS middleware, and routers.
- Auth module (`backend/core/auth.py`) validates bearer token against Supabase Auth `/auth/v1/user`.
- CORS config (`backend/core/cors.py`) parses explicit allowed origins.
- Routers:
  - `backend/routers/ingest.py`
  - `backend/routers/query.py`
  - `backend/routers/dashboard.py`
  - `backend/routers/health.py`

### RAG Pipeline

- Ingest:
  - Parse document (`backend/rag/ingest.py`)
  - Chunk text (`backend/rag/chunking.py`)
  - Embed chunks (`backend/rag/embeddings.py`)
  - Persist document/chunks (`backend/db/supabase.py`)
- Query:
  - Embed query + vector search (`backend/rag/retriever.py`)
  - Agent graph (`backend/orchestration/graph.py`):
    - Researcher -> Critic -> Synthesizer -> Judge
  - Persist query and agent traces (`backend/db/supabase.py`)

### Persistence

- Supabase schema and RLS policies are defined in `supabase/migrations/001_initial_schema.sql`.
- Repository abstraction lives in `backend/db/supabase.py`.
- Ownership checks:
  - Team-scoped checks for ingest/search/document listing
  - Session-scoped checks for query/history/dashboard metrics

## 3. API Surface

- `GET /health`
- `POST /ingest`
- `GET /ingest/documents`
- `POST /sessions`
- `POST /query`
- `GET /query/history`
- `GET /dashboard/metrics`

Auth model:

- Protected endpoints require `Authorization: Bearer <access_token>`.
- Token is validated by backend against Supabase Auth.
- Backend resolves `user_id` and enforces ownership on team/session resources.

## 4. Data Flow

### Ingest Flow

1. Frontend uploads file + `team_id` to `POST /ingest`.
2. Backend validates token and checks team ownership.
3. Backend validates extension/size and writes temp file.
4. Text extraction + chunking + embedding run.
5. Document/chunks are inserted in Supabase.
6. Response returns `document_id`, type, and chunk count.

### Query Flow

1. Frontend posts `query`, `team_id`, `session_id`, `top_k` to `POST /query`.
2. Backend validates token, team ownership, and session ownership.
3. Retrieval executes vector similarity search by `team_id`.
4. Agent orchestration runs and produces final answer + scorecard + trace.
5. Query/traces are persisted.
6. API returns answer, sources, metrics metadata, and trace.

### History/Metrics Flow

1. Frontend requests history or dashboard with `session_id`.
2. Backend validates token and session ownership.
3. Repository reads query rows and computes aggregates.
4. API returns structured history/telemetry payloads.

## 5. Security Model

- Frontend does not call backend unauthenticated for protected routes.
- Backend enforces auth independently (does not trust frontend-only guards).
- CORS is explicit (`CORS_ALLOWED_ORIGINS`), no wildcard credentials policy.
- Ownership checks are centralized in repository methods.
- Service-role DB access is constrained by explicit ownership queries.

Known limitations:

- In-memory fallback cannot fully emulate production ownership semantics; intended for tests/local only.
- Ingest idempotency cache is process-local (not distributed).

## 6. Reliability and Observability

- Request IDs are propagated via middleware (`x-request-id`).
- LLM clients include timeout/retry behavior.
- Groq fallback response is non-echoing to avoid prompt/source leakage.
- Query responses include retrieval metadata (`model_version`, embedding/index versions, top-k).

## 7. Configuration

Primary env keys (see `.env.example`):

- Backend auth/data:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_ANON_KEY`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (local fallback only)
- Backend behavior:
  - `TOP_K`, `MAX_QUERY_LENGTH`, `MAX_FILE_SIZE_MB`
  - `QUERY_HISTORY_LIMIT_DEFAULT`, `QUERY_HISTORY_LIMIT_MAX`
  - `DASHBOARD_DAYS_DEFAULT`, `DASHBOARD_DAYS_MAX`
  - `ALLOWED_FILE_TYPES`
- LLM/runtime:
  - `GROQ_API_KEY`, `SARVAM_API_KEY`
  - `GROQ_TIMEOUT_SECONDS`, `GROQ_MAX_RETRIES`
  - `SARVAM_TIMEOUT_SECONDS`, `SARVAM_MAX_RETRIES`
  - `EMBEDDING_MODEL`, `EMBEDDING_DISABLE_MODEL`
- Security/runtime toggles:
  - `CORS_ALLOWED_ORIGINS`
  - `ALLOW_INMEMORY_REPOSITORY`

## 8. CI/CD Enforcement

GitHub Actions workflow: `.github/workflows/ci.yml`

Enforced on push/PR:

- Backend job:
  - `ruff check backend`
  - `pytest -q`
- Frontend job:
  - `npm run lint`
  - `npm test`
  - `npm run build`

This establishes baseline quality gates for style, correctness, and build integrity.

## 9. Tradeoffs and Next Steps

Current tradeoffs:

- Hosted inference providers simplify MVP delivery but add external dependency risk.
- Fallback repository mode accelerates local iteration but should not be enabled in production.

Recommended next steps:

1. Move ingest idempotency cache to Redis/Postgres for multi-instance correctness.
2. Add explicit backend authz negative integration tests (401/403 matrix).
3. Add deployment-time guard to fail startup if fallback repository is enabled outside non-dev contexts.
4. Optionally replace token introspection call with JWT validation + key rotation support.
