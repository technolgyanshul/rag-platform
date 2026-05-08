# Multi-Agent Multi-Model RAG Research Platform

Production-style MVP for a traceable multi-agent RAG assistant with uploads, citations, agent traces, scorecards, query history, and dashboard metrics.

## Current Status

The platform is runnable locally with Docker Compose and has the core RAG workflow in place. The latest code includes the fixes from the review pass for dynamic agent configuration, OCR-backed image ingestion, hybrid retrieval, dashboard time-window metrics, and frontend API tests.

What currently works:

- Supabase Auth backed sign-up/sign-in with SSR session refresh in the Next.js app.
- Authenticated knowledge uploads for `pdf`, `png`, `jpg`, `jpeg`, and `txt` files.
- PDF text extraction, image OCR through Tesseract, text chunking, and embedding persistence.
- Dual embedding retrieval using `all-MiniLM-L6-v2` and `bge-base-en-v1.5`.
- Supabase hybrid search through `hybrid_match_chunks` when the database migration is applied.
- In-memory repository fallback for local tests and Docker test runs.
- Multi-agent query flow with Researcher, Critic, Synthesizer, and Judge stages.
- Agent model and prompt configuration loaded from the `agents` table when team rows exist, with safe defaults otherwise.
- Query persistence, query history, agent trace persistence, and dashboard metrics scoped to the signed-in user/session.
- Frontend pages for auth, chat, knowledge uploads, history, dashboard, profile, and demo team status.
- Frontend Vitest coverage for API helpers.
- Backend unit/integration tests plus a Docker test profile that pre-downloads embedding models during image build.

Known current gaps:

- LLM generation still depends on hosted Groq and Sarvam APIs. Local Ollama/free OSS inference is not implemented yet.
- Team management UI is intentionally disabled in the demo; the app scopes workspace data to the signed-in user automatically.
- Export flows for history/analytics are not implemented yet.
- Evaluation is still a scaffold/stub, not a live benchmark against `/query`.
- GitHub Actions CI was removed; local and Docker test commands are the current verification path.
- Supabase email confirmation is still enabled. New users must confirm email before sign-in unless confirmation is disabled in Supabase Auth settings.

## Stack

- Frontend: Next.js 16, React 19, TypeScript, Vitest
- Backend: FastAPI, Python 3.11, LangGraph-style orchestration
- Auth/DB/Vector: Supabase, Postgres, pgvector
- Retrieval: SentenceTransformers `all-MiniLM-L6-v2`, BAAI `bge-base-en-v1.5`, Supabase hybrid RPC
- Image OCR: Tesseract OCR through `pytesseract` and Pillow
- LLMs: Groq for agents, Sarvam for judge/fallback
- Local runtime: Docker Compose or manual backend/frontend processes

## Environment

Copy the root template and fill in the required values:

```bash
cp .env.example .env
```

Required for the normal app runtime:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_ANON_KEY=
GROQ_API_KEY=
SARVAM_API_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Useful local/test settings:

```bash
ALLOW_INMEMORY_REPOSITORY=true
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
```

Important Supabase Auth notes:

- Supabase may reject placeholder/test domains such as `client1@test.com`; use a real email-style domain.
- If email confirmation is enabled, sign-in returns `Email not confirmed` until the user confirms the email.
- To avoid that during demos, disable email confirmation in Supabase Auth settings, or confirm the user manually from the Supabase dashboard.

## Database Setup

Apply the migrations in order:

```bash
supabase/migrations/001_initial_schema.sql
supabase/migrations/002_hybrid_search.sql
```

The second migration adds the hybrid search support used by `backend/rag/retriever.py` and `SupabaseRepository.hybrid_search_chunks()`.

## Run With Docker Compose

Start backend and frontend:

```bash
docker compose up --build
```

Open:

```text
http://localhost:3000
```

Backend health check:

```bash
curl http://localhost:8000/health
```

A `GET /` request to the backend returns `404`; that is expected because the backend only exposes API routes.

## Run Manually

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

For image OCR outside Docker, install the system Tesseract binary too:

```bash
sudo apt install tesseract-ocr
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Test Commands

Frontend tests:

```bash
cd frontend
npm test
```

Backend tests with Docker test profile:

```bash
docker compose --profile test build test
docker compose --profile test run --rm test
```

The Docker test image pre-downloads both embedding models and runs with offline transformer settings, so later test runs do not need HuggingFace network access.

Backend tests manually:

```bash
cd backend
ALLOW_INMEMORY_REPOSITORY=true pytest -q --tb=short
```

Manual backend tests can still fail if model weights are not cached locally. Prefer the Docker test profile for reproducible backend testing.

Evaluation scaffold:

```bash
python backend/tests/evaluation/run_eval.py
```

## API Routes

- `GET /health`
- `POST /ingest`
- `GET /ingest/documents`
- `POST /sessions`
- `POST /query`
- `GET /query/history`
- `GET /dashboard/metrics`

## Frontend Routes

- `/login`
- `/signup`
- `/chat`
- `/knowledge`
- `/history`
- `/dashboard`
- `/profile`
- `/team`

## Implementation Notes

- Workspace/team data is currently mapped to the authenticated user id for the demo path.
- `ALLOW_INMEMORY_REPOSITORY=true` forces the backend repository to avoid Supabase and use the in-memory fallback.
- Dashboard aggregates now honor the requested `days` window for totals, averages, and chart buckets.
- Retrieval calls the hybrid Supabase RPC when Supabase is active; in-memory mode falls back to cosine-only search for tests/dev.
- Agent configs are loaded from Supabase `agents` rows by role when available; otherwise default model names are used.
- The backend injects an `x-request-id` response header and propagates request IDs through route-level error logging.

## Documentation

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/TESTING.md`
- `docs/EVALUATION.md`
- `docs/PRD-SOW-HANDOFF.md`
- `docs/DEMO.md`
- `docs/GUIDELINES-IMPLEMENTATION.md`
- `paste.md`

## Latest Local Commit

The latest local commit at the time of this update is:

```text
4cf9d49 Update RAG platform fixes and test setup
```

That commit is local unless GitHub authentication has been fixed and `git push origin main` has completed successfully.

## Next Iteration

1. Implement local free/open-source LLM inference with Ollama or another local runtime, replacing hosted Groq/Sarvam dependency.
2. Add full team CRUD and bind user-selected team configuration into frontend flows.
3. Replace the evaluation stub with live `/query` benchmarking.
4. Add export support for history and analytics in JSON, CSV, and/or PDF.
5. Restore CI once the backend test strategy is fully offline and secret-safe.
