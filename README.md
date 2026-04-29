# Multi-Agent Multi-Model RAG Research Platform

Production-style MVP for a traceable multi-agent RAG assistant with citations, agent traces, and scorecards.

## Current Status

Phase 8 baseline is complete:
- Upload and ingest PDF/image/text
- Query with retrieval + multi-agent orchestration
- Query history and dashboard metrics
- Unit and integration tests
- Evaluation script scaffold and report output

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

## Demo Flow

Follow `docs/DEMO.md` for a complete upload -> query -> trace -> dashboard walkthrough.

## Completed Deliverables

- [x] Full frontend MVP pages
- [x] Multi-agent query orchestration and persistence
- [x] Dashboard and query history endpoints
- [x] Unit/integration/failure-path tests
- [x] Evaluation scaffold and generated report

## Next Iteration

1. Replace evaluation stubs with live `/query` benchmarking
2. Add richer auth and team-scoped authorization tests
3. Add CI workflow for backend and frontend checks
