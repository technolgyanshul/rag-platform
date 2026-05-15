# Multi-Agent RAG Platform

Multi-Agent RAG Platform is a document-grounded chat application with team-scoped agent orchestration. Users authenticate with Supabase, upload documents, create teams and agents, run retrieval-backed queries, and inspect answers with sources, per-agent traces, and deterministic scorecards.

## What It Includes

- Next.js frontend for auth, dashboard, knowledge upload, team/agent setup, chat, history, and profile pages.
- FastAPI backend for ingest, retrieval, session/history persistence, team/agent CRUD, query orchestration, and observability.
- Supabase Auth, Postgres, and Storage for identity, application data, query history, traces, scorecards, and source files.
- Qdrant vector storage for user-scoped document chunks embedded through EmbedAnything.
- Multi-provider LLM routing through Groq, Sarvam, and LM Studio.
- Optional ClickHouse observability for backend traces, UI events, and infrastructure checks.

## System Architecture

```mermaid
flowchart LR
  Browser["Browser\nNext.js app"] -->|Supabase session| SupabaseAuth["Supabase Auth"]
  Browser -->|/api proxy or NEXT_PUBLIC_API_BASE_URL| Backend["FastAPI backend"]

  Backend --> Auth["core.auth\nBearer token validation"]
  Auth --> SupabaseAuth

  Backend --> Ingest["routers.ingest\nfile upload + indexing"]
  Backend --> Query["routers.query\nretrieval + orchestration"]
  Backend --> Teams["routers.teams\nteam/agent CRUD"]
  Backend --> Sessions["routers.sessions\nhistory + export"]

  Ingest --> EmbedAnything["EmbedAnything\nsemantic chunks + embeddings"]
  Ingest --> Storage["Supabase Storage\nsource files"]
  Ingest --> SupabaseDb["Supabase Postgres\nmetadata, sessions, queries"]
  Ingest --> Qdrant["Qdrant\nvector collection"]

  Query --> Retriever["rag.retriever\nembed query + vector search"]
  Retriever --> EmbedAnything
  Retriever --> Qdrant
  Query --> Orchestrator["rag.orchestrator\nsequential, debate, hierarchical"]
  Orchestrator --> LLMRouter["llms.router"]
  LLMRouter --> Groq["Groq"]
  LLMRouter --> Sarvam["Sarvam"]
  LLMRouter --> LMStudio["LM Studio"]
  Orchestrator --> SupabaseDb
  Query --> SupabaseDb

  Backend --> Observability["observability.py"]
  Observability --> ClickHouse["ClickHouse optional"]
```

## Query Data Flow

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant F as Next.js Chat Page
  participant B as FastAPI /query
  participant S as SupabaseRepository
  participant R as Retriever
  participant Q as Qdrant
  participant O as Orchestrator
  participant L as LLMRouter
  participant P as LLM Provider

  U->>F: Select team and submit query
  F->>B: POST /query {query, session_id, team_id, top_k}
  B->>S: Validate team and session ownership
  S-->>B: Team, session, agents
  B->>R: retrieve_chunks(query, user_id, top_k)
  R->>Q: Vector search filtered by user_id
  Q-->>R: Retrieved chunks
  R-->>B: Formatted source previews

  alt No retrieved sources
    B->>S: Persist query, messages, scorecard
    B-->>F: Insufficient-context answer
  else Sources found
    B->>S: Create query row and user message
    B->>O: Run team collaboration rule
    loop For each agent step
      O->>L: chat(provider, model, messages, metadata)
      L->>P: Provider chat completion
      P-->>L: Agent output
      L-->>O: Normalized output
      O->>S: Persist agent trace
    end
    O->>S: Save scorecard
    O-->>B: Final answer, citations, traces, scorecard
    B->>S: Update query and create assistant message
    B-->>F: QueryResponse
  end

  F->>U: Render answer, sources, traces, scorecard
```

## Ingest Data Flow

```mermaid
flowchart TD
  Upload["Knowledge page upload"] --> Api["POST /ingest"]
  Api --> Validate["Validate auth, file type, size, payload"]
  Validate --> SourceFile["Upload original file to Supabase Storage"]
  SourceFile --> DocumentRow["Insert document row in Supabase"]
  DocumentRow --> Pipeline["rag.ingest + EmbedAnything"]
  Pipeline --> Chunks["Semantic chunks with embeddings"]
  Chunks --> VectorPoints["VectorPoint payloads"]
  VectorPoints --> Qdrant["Qdrant upsert"]
  Qdrant --> Finalize["Update document chunk_count and index_status"]
  Finalize --> UI["Return document_id, filename, file_type, chunks_created"]
```

## Core Class Diagram

```mermaid
classDiagram
  class FastAPIApp {
    +include_router()
    +add_middleware()
  }

  class RequestIdObservabilityMiddleware {
    +__call__(scope, receive, send)
    -_header(scope, name)
    -_headers_dict(scope)
  }

  class AuthUser {
    +string user_id
    +string email
  }

  class SupabaseRepository {
    -client _client
    +create_session(user_id, title, session_id, team_id)
    +list_sessions(user_id)
    +get_team(user_id, team_id)
    +list_agents(user_id, team_id)
    +insert_document()
    +upload_document_file()
    +create_query()
    +update_query_result()
    +create_agent_trace()
    +save_scorecard()
  }

  class QdrantVectorBackend {
    +upsert_points(points)
    +search(query_vector, user_id, top_k)
    +delete_document_points(user_id, document_id)
    -_ensure_collection(vector_size)
  }

  class Orchestrator {
    +run(query_context, team, agents, retrieved_context)
    -_run_sequential(context, team, agents, retrieved_context)
    -_run_debate(context, team, agents, retrieved_context)
    -_run_hierarchical(context, team, agents, retrieved_context)
    -_execute_agent_step()
    -_persist_trace()
  }

  class QueryContext {
    +string user_id
    +string session_id
    +string query_id
    +string query
    +string request_id
  }

  class AgentStepTrace {
    +string id
    +string agent_id
    +string agent_name
    +string agent_role
    +string model_provider
    +string model_name
    +string status
    +int latency_ms
    +string output
    +string error
  }

  class OrchestrationResult {
    +string final_answer
    +list traces
    +list citations
    +dict scorecard
    +string collaboration_rule
  }

  class LLMRouter {
    +chat(provider, model_name, messages, metadata)
    -_chat_lmstudio(client, model_name, messages, metadata)
  }

  class GroqClient
  class SarvamClient
  class LMStudioClient
  class ClickHouseObservability {
    +initialize()
    +record_trace_event()
    +record_ui_event()
    +record_infra_check()
  }

  FastAPIApp --> RequestIdObservabilityMiddleware
  FastAPIApp --> SupabaseRepository
  SupabaseRepository --> AuthUser
  SupabaseRepository --> QdrantVectorBackend
  Orchestrator --> QueryContext
  Orchestrator --> AgentStepTrace
  Orchestrator --> OrchestrationResult
  Orchestrator --> SupabaseRepository
  Orchestrator --> LLMRouter
  LLMRouter --> GroqClient
  LLMRouter --> SarvamClient
  LLMRouter --> LMStudioClient
  RequestIdObservabilityMiddleware --> ClickHouseObservability
```

## Main Runtime Paths

- `/ingest`: uploads source files, stores them in Supabase Storage, chunks and embeds them through EmbedAnything, and indexes vectors into Qdrant.
- `/query`: validates team/session ownership, retrieves user-scoped chunks, runs the selected team collaboration rule, and persists answer artifacts.
- `/sessions`: creates sessions, lists sessions, returns session detail, and exports session history as JSON.
- `/teams`: manages teams and agents, exposes provider model catalogs, default agent templates, and LM Studio probe endpoints.
- `/dashboard`: aggregates user metrics and query trends.
- `/observability`: accepts UI events and exposes infrastructure checks.

## Local Development

Create `.env` from the example and fill Supabase plus provider credentials:

```bash
cp .env.example .env
```

Run the core services with Docker:

```bash
docker compose up --build backend qdrant frontend
```

Then open:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Qdrant: `http://localhost:6333`

Run backend tests:

```bash
cd backend
pytest
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run test
npm run build
```

## Environment Notes

Required Supabase values:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`

LLM provider values depend on the agents you configure:

- Groq agents need `GROQ_API_KEY`.
- Sarvam agents need `SARVAM_API_KEY`.
- LM Studio agents need a reachable provider base URL configured on the agent.

Qdrant defaults to `http://qdrant:6333` in Docker. ClickHouse is optional and disabled by default with `CLICKHOUSE_ENABLED=false`.

## Repository Layout

```text
backend/                 FastAPI app, routers, RAG pipeline, LLM clients, tests
frontend/                Next.js app, API client, UI components, tests
supabase/migrations/     Supabase schema and RLS migrations
docs/                    Supporting project docs
docker-compose.yml       Local backend, frontend, Qdrant, Cloudflare tunnel, test profile
```

## Demo

See [demo.md](demo.md) for a step-by-step demo script.
