# Testing Strategy

## Commands

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
npm run build
```

## Coverage Focus

- Unit tests for chunking, embeddings, retrieval, and orchestration
- Integration tests for ingest, query, history, and dashboard metrics routes
- Failure-path tests for unsupported file type, empty uploads, and invalid session inputs
- Evaluation script scaffold in `backend/tests/evaluation/`

## Demo Verification

Use `docs/DEMO.md` to validate upload -> query -> trace -> history -> dashboard flow manually.
