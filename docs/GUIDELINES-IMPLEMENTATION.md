# Guidelines Implementation Notes

This project now applies the core engineering rules from `guidelines.md` with concrete backend and frontend changes.

## Backend

- Added typed runtime settings in `backend/core/config.py`.
- Added stricter boundary validation for `/query`, `/query/history`, `/ingest`, `/ingest/documents`, and `/dashboard/metrics`.
- Added explicit API failure mapping (`400` for invalid input, `503` for temporary retrieval/orchestration/persistence failures).
- Added structured logging for request failures and completion paths.
- Added retrieval observability fields in query responses:
  - `model_version`
  - `retrieval_metadata.embedding_model_version`
  - `retrieval_metadata.index_version`
  - `retrieval_metadata.top_k`
- Added request-id middleware in `backend/main.py` to propagate `x-request-id` and tie logs across routes.
- Added prompt template versioning and separation in `backend/prompts/` with `render_prompt(...)` usage in agent modules.
- Added timeout/retry resilience wrappers for external LLM calls in:
  - `backend/llms/groq_client.py`
  - `backend/llms/sarvam_client.py`
- Added ingest idempotency behavior via `Idempotency-Key` header replay cache in `backend/routers/ingest.py`.

## Frontend

- Added explicit chat query UI state union (`idle`, `loading`, `success`, `error`) in `frontend/lib/types.ts`.
- Updated chat page and answer panel to consume typed state and render observability metadata.

## Configuration

Expanded `.env.example` with explicit limits and reproducibility/version fields:

- `MAX_QUERY_LENGTH`
- `QUERY_HISTORY_LIMIT_DEFAULT`
- `QUERY_HISTORY_LIMIT_MAX`
- `DASHBOARD_DAYS_DEFAULT`
- `DASHBOARD_DAYS_MAX`
- `RAG_PROMPT_VERSION`
- `EMBEDDING_MODEL_VERSION`
- `INDEX_VERSION`
- `MODEL_VERSION`
