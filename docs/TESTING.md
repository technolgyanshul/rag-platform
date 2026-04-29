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
- Failure-path tests for fallback behavior and invalid input handling
- Evaluation script scaffold in `backend/tests/evaluation/`
