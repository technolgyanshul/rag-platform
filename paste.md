# Code Review

## Findings

### [P0] Local/offline requirement is not met by the LLM path

`backend/llms/groq_client.py:13` and `backend/llms/groq_client.py:56`

The agent pipeline depends on `GROQ_API_KEY` for actual model output. When that key is absent, every agent returns the generic provider-unavailable message instead of running a local OSS model. This conflicts with the stated requirement that no external paid API keys are required and that the system should run locally on CPU. In a clean local setup without Groq credentials, `/query` still completes but produces a non-answer, and the rest of the pipeline treats that fallback as if it were model output. Replace this path with a local provider such as Ollama/llama.cpp, or make the local provider the default and keep Groq only as an optional remote adapter.

Related code:

```python
class GroqClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
```

```python
return (
    "Model provider is temporarily unavailable. "
    "Please retry your query in a few moments."
)
```

The judge has the same external-service pattern through Sarvam:

`backend/llms/sarvam_client.py:20` and `backend/llms/sarvam_client.py:28`

```python
if self.api_key:
    response = requests.post(
        "https://api.sarvam.ai/v1/judge",
```

Impact: the core user path cannot satisfy the assignment constraints in a no-key local environment.

---

### [P1] Image ingestion indexes placeholder text instead of image content

`backend/rag/image_text.py:4`

The image extraction function returns only the filename plus fixed placeholder text. As a result, uploaded PNG/JPG/JPEG files are accepted and chunked, but retrieval never has OCR text, captions, table contents, or any semantic content from the image. Any question whose answer is inside an uploaded image will not be answerable, even though the UI and backend advertise image support.

Current implementation:

```python
def extract_image_text(file_path: str) -> str:
    path = Path(file_path)
    return f"Image upload: {path.name}. OCR/caption extraction placeholder text for MVP retrieval."
```

Expected behavior: run OCR/caption extraction locally, persist extracted text with provenance, and surface failure explicitly when extraction cannot be performed.

Impact: the required PDF + image ingestion support is only nominal for images.

---

### [P1] Query orchestration ignores user/team-configured agents and models

`backend/orchestration/graph.py:27`

`run_graph` accepts only `query` and `sources`, then always executes the same hardcoded Researcher, Critic, Synthesizer, and Judge sequence using default model constants. There is no team, workspace, or agent configuration passed into the graph, so users cannot create or manage an agent team with different roles or model assignments for a query.

Relevant code:

```python
def run_graph(query: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
```

`backend/orchestration/graph.py:34`

```python
state["researcher_output"] = _run_step(
    state,
    "Researcher",
    DEFAULT_RESEARCHER_MODEL,
```

`backend/orchestration/graph.py:41`

```python
state["critic_output"] = _run_step(
    state,
    "Critic",
    DEFAULT_CRITIC_MODEL,
```

`backend/orchestration/graph.py:53`

```python
state["synthesizer_output"] = _run_step(
    state,
    "Synthesizer",
    DEFAULT_SYNTHESIZER_MODEL,
```

Impact: any team management UI or API would be misleading, because runtime behavior is fixed regardless of user choices. To satisfy the multi-agent requirement, the graph should load the selected team configuration, validate ownership, and route each role to its configured local model/provider.

---

### [P1] Retrieval is single-vector search, not hybrid or multi-model retrieval

`backend/rag/embeddings.py:8`

The embedding pipeline uses a single default embedding model and falls back to hash embeddings when the model cannot load. There is no second embedding model, no sparse/BM25 component, and no reranker.

```python
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```

`backend/rag/retriever.py:18`

```python
query_embedding = embed_text(query)
repository = SupabaseRepository()
rows = repository.search_chunks(user_id=user_id, query_embedding=query_embedding, top_k=top_k)
```

Impact: this does not meet the required multi-model embeddings / hybrid retrieval behavior. It also creates poor failure behavior: if `sentence-transformers` is missing or model initialization fails, retrieval silently uses deterministic hash embeddings, which are not semantically meaningful.

Suggested fix: make embedding provider initialization fail loudly in production, add a sparse lexical retriever, merge/rerank candidate sets, and include retrieval metadata that identifies all participating embedding/index versions.

---

### [P2] Dashboard aggregate metrics ignore the requested `days` window

`backend/db/supabase.py:287`

`list_dashboard_metrics` accepts a `days` parameter and correctly builds the per-day chart buckets for that window, but `total_queries`, `average_response_time_ms`, and `average_overall_score` are computed from the last 500 queries regardless of age.

Relevant code:

```python
def list_dashboard_metrics(self, user_id: str, session_id: str, days: int = 7) -> dict[str, Any]:
    rows = self.list_queries(user_id=user_id, session_id=session_id, limit=500)
    total_queries = len(rows)
```

Later, only `queries_over_time` applies the date buckets:

```python
if day_key in per_day:
    per_day[day_key] += 1
```

Impact: a dashboard request for `days=7` can show a 7-day chart but totals/averages that include older activity. Users will see inconsistent metrics when sessions contain older queries. Filter `rows` to the requested date window before computing all aggregate values, or query the database with the date predicate directly.

---

### [P2] Frontend API tests are stale and no longer exercise the exported functions correctly

`frontend/lib/api.test.ts:5`

The tests mock `./supabase`, but the production API module imports Supabase through `@/utils/supabase/client`. The mock therefore does not replace the dependency used by `frontend/lib/api.ts`.

```ts
vi.mock("./supabase", () => ({
```

`frontend/lib/api.test.ts:40`

The tests also call `uploadKnowledgeFile` and `listKnowledgeDocuments` with a `team-1` argument, but the current exported functions do not accept that parameter.

```ts
const result = await uploadKnowledgeFile("team-1", new File(["hello"], "sample.txt"));
```

Production signature:

`frontend/lib/api.ts:35`

```ts
export async function uploadKnowledgeFile(file: File): Promise<IngestResponse> {
```

Production signature:

`frontend/lib/api.ts:54`

```ts
export async function listKnowledgeDocuments(): Promise<DocumentRow[]> {
```

Impact: the test suite will fail type checking or runtime behavior once run under the current API shape, and it cannot catch regressions in auth header construction because it mocks the wrong module path. Update the mock target and function calls, then assert the fetch URL/body/headers for the current API contract.

---

## Additional Notes

- `backend/db/supabase.py` has reasonable ownership checks for sessions and workspace creation, but the workspace/team model is currently collapsed to `workspace_id == user_id`. That may be acceptable for a single-user MVP, but it is not a real team-management implementation.
- Query history includes session-scoped data and agent trace persistence, which matches the traceability goal for successful queries.
- The current evaluation script is stubbed, so it does not yet provide a meaningful baseline-vs-multi-agent quality comparison.

## Review Summary

The largest gaps are architectural rather than small syntax defects: the code advertises a local, configurable, multi-agent RAG system, but the runtime path depends on external model APIs, hardcodes agent/model routing, and indexes image uploads without extracting image content. The dashboard and frontend test issues are narrower and should be straightforward fixes after the core requirements are clarified.
