# Multi-Agent Multi-Model RAG Research Platform

Production-style MVP for a traceable multi-agent RAG assistant with citations, agent traces, and scorecards.

## Current Status

Phase 1 scaffold is in place:
- Monorepo structure
- FastAPI backend foundation
- Next.js frontend foundation
- Health endpoint
- Environment template

## Planned Stack

- Frontend: Next.js + TypeScript
- Backend: FastAPI
- DB/Vector: Supabase + pgvector
- Orchestration: LangGraph
- LLMs: Groq (agents), Sarvam (judge)

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Health check: `GET http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Phase 1 Deliverables

- [x] Running frontend scaffold
- [x] Running backend scaffold
- [x] Health endpoint scaffold
- [x] Initial README

## Next Implementation Focus

1. Supabase schema + RLS
2. Auth pages with Supabase
3. Ingestion pipeline (`/ingest`)
4. Retrieval + multi-agent query flow (`/query`)
