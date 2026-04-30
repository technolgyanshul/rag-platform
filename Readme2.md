# Multi-Agent Multi-Model RAG Research Platform

Production-style MVP for a traceable multi-agent RAG assistant with citations, agent traces, and scorecards.

## Current Status

Phase 8 baseline is complete and guideline hardening is in progress:
- Upload and ingest PDF/image/text
- Query with retrieval + multi-agent orchestration
- Query history and dashboard metrics
- Unit and integration tests
- Evaluation script scaffold and report output
- Added stricter input validation, request-id propagation, prompt templating, and LLM timeout/retry handling

## Stack

- Frontend: Next.js + TypeScript
- Backend: FastAPI
- DB/Vector: Supabase + pgvector
- Orchestration: LangGraph
- LLMs: Groq (agents), Sarvam (judge)

## Setup From Clean Clone

Copy environment templates and fill values:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend health check:

```bash
curl http://localhost:8000/health
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Test Commands

```bash
# backend
cd backend
pytest

# frontend
cd frontend
npm test
npm run build

# evaluation scaffold
cd ..
python backend/tests/evaluation/run_eval.py
```

## API Routes

- `GET /health`
- `POST /ingest`
- `GET /ingest/documents`
- `POST /query`
- `GET /query/history`
- `GET /dashboard/metrics`

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/TESTING.md`
- `docs/EVALUATION.md`
- `docs/PRD-SOW-HANDOFF.md`
- `docs/DEMO.md`
- `docs/GUIDELINES-IMPLEMENTATION.md`

## Demo Flow

Follow `docs/DEMO.md` for a complete upload -> query -> trace -> dashboard walkthrough.

## Completed Deliverables

- [x] Full frontend MVP pages
- [x] Multi-agent query orchestration and persistence
- [x] Dashboard and query history endpoints
- [x] Unit/integration/failure-path tests
- [x] Evaluation scaffold and generated report
- [x] Runtime config hardening and stricter API boundary validation
- [x] Request-id middleware and structured failure logging at route boundaries
- [x] Prompt templates under `backend/prompts/` and LLM timeout/retry wrappers

## Next Iteration

1. Migrate to local free/open-source inference stack (Ollama + local model routing) to remove hosted LLM dependency.
2. Implement full team CRUD (create/list/edit/delete) and bind chat/history/knowledge flows to selected team.
3. Add chat controls and UX parity (`new session`, `regenerate`, source toggle, richer stage-by-stage progress updates).
4. Implement hybrid multi-model retrieval (multi-embedding + reranking) and stronger retrieval diagnostics.
5. Add export capabilities for history and analytics (JSON/PDF/CSV) plus CI workflow for backend/frontend checks.
