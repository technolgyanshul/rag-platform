# Demo Script

This demo walks through the current multi-agent RAG path: authenticate, upload knowledge, create a team, run a query, and inspect traces.

## Prerequisites

- Docker is running.
- `.env` exists at the repo root.
- Supabase project credentials are configured in `.env`.
- The migrations under `supabase/migrations/` have been applied to the Supabase project.
- At least one LLM provider is configured:
  - Groq with `GROQ_API_KEY`, or
  - Sarvam with `SARVAM_API_KEY`, or
  - LM Studio running at the URL configured on each LM Studio agent.

## Start The App

```bash
docker compose up --build backend qdrant frontend
```

Open the frontend:

```text
http://localhost:3000
```

The backend is available at:

```text
http://localhost:8000
```

## Demo Flow

1. Register or log in.
2. Open `Knowledge`.
3. Upload a small `.txt`, `.pdf`, `.png`, `.jpg`, or `.jpeg` file.
4. Wait for the document row to show an indexed status and a chunk count.
5. Open `Teams`.
6. Create a team with a name, optional domain, and collaboration rule:
   - `sequential` for researcher-to-critic-to-synthesizer style flow.
   - `debate` for independent positions plus resolver behavior.
   - `hierarchical` for planner, workers, and merger behavior.
7. Confirm the team has at least one agent. New teams can use the default Researcher, Critic, and Synthesizer templates.
8. Open `Chat`.
9. Select the team.
10. Ask a question that can be answered from the uploaded document.
11. Review the answer, source list, agent trace panel, and scorecard.
12. Open `History` and confirm the session, messages, query, sources, traces, and scorecard were persisted.

## Suggested Demo Query

Use a query that asks for something explicitly present in the uploaded file:

```text
Summarize the main decision points in this document and cite the supporting evidence.
```

## Expected Result

- The chat response includes a final answer.
- Sources are numbered and tied to retrieved chunks.
- The trace panel shows each agent step, provider, model, status, latency, and output.
- The scorecard shows deterministic quality fields.
- The history detail page shows the saved session timeline.

## Troubleshooting

- `Missing Authorization header` or `Invalid or expired access token`: log out and log back in, then retry.
- `Auth is not configured`: check `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
- `Document persistence temporarily unavailable`: check `SUPABASE_SERVICE_ROLE_KEY` and Supabase Storage configuration.
- `No retrieval results were returned`: re-upload or re-index the document and verify Qdrant is running.
- `Team must have at least one agent before chat`: add an agent to the selected team.
- LM Studio failures usually mean the agent is missing `provider_base_url`, the server is unreachable from the backend container, or the selected model is not loaded.

## Verification Commands

Backend tests:

```bash
cd backend
pytest
```

Frontend tests:

```bash
cd frontend
npm run lint
npm run test
```
