# RAG Research Platform

Production-style MVP for a document-grounded RAG assistant with uploads, retrieval, citations, query history, and dashboard metrics.

## Current Status

Phase 8 baseline is complete:
- Upload and ingest PDF/image/text
- Query with retrieval + answer generation
- Query history and dashboard metrics
- Unit and integration tests

## Stack

- Frontend: Next.js + TypeScript
- Backend: FastAPI
- DB/Vector: Supabase + pgvector
- LLMs: Groq with Sarvam fallback

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

```

## API Routes

- `GET /health`
- `POST /ingest`
- `GET /ingest/documents`
- `POST /sessions`
- `POST /query`
- `GET /query/history`
- `GET /dashboard/metrics`

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/TESTING.md`
- `docs/PRD-SOW-HANDOFF.md`

## Demo Flow

Follow `docs/DEMO.md` for a complete upload -> query -> dashboard walkthrough.

## Completed Deliverables

- [x] Full frontend MVP pages
- [x] Query generation and persistence
- [x] Dashboard and query history endpoints
- [x] Unit/integration/failure-path tests
- [x] Evaluation scaffold and generated report

## Next Iteration

1. Add live `/query` benchmarking
2. Add richer auth and workspace-scoped authorization tests
3. Add CI workflow for backend and frontend checks
