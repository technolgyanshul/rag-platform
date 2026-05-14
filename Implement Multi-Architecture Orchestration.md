# Implement Multi-Architecture Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the current single-generator query path with runtime orchestration for `sequential`, `debate`, and `hierarchical` team collaboration rules.

**Architecture:** Add a rule-aware orchestration layer under `backend/rag/` and a strict model router under `backend/llms/`. Keep `POST /query` as the single chat endpoint, but make it load the selected session team, retrieve context once, dispatch the correct strategy, persist every agent step to `agent_traces`, save a baseline `scorecard`, and return a Phase 8-safe response contract with final answer, sources, traces, and scorecard.

**Tech Stack:** FastAPI, Pydantic, Supabase, in-memory repository fallback for tests, existing ClickHouse `record_trace_event`, pytest, httpx `ASGITransport`.

---

## Current State

- `teams.collaboration_rule` already supports `sequential`, `debate`, and `hierarchical`.
- `backend/routers/query.py` currently retrieves chunks and calls `generate_answer()` directly.
- `QueryResponse` currently returns `final_answer` and `sources`, but not `traces` or `scorecard`.
- `queries.final_answer` is nullable in the database, so a query row can be created before orchestration and updated after completion.
- `agent_traces.query_id` is nullable by migration, but Phase 7 should create the query row first so traces normally have a `query_id`.
- `agent_traces` and `scorecards` tables exist, but `SupabaseRepository` needs trace and scorecard methods.
- `backend/rag/generator.py` currently routes through `GroqClient` and fallback behavior, which does not enforce each agent row's assigned provider/model.

## Scope

Included:

- Runtime execution for `sequential`, `debate`, and `hierarchical`.
- Strict provider/model dispatch per agent row.
- Per-step trace persistence.
- Baseline scorecard persistence.
- ClickHouse orchestration lifecycle events.
- Query endpoint response contract for Phase 8 trace UI.
- Unit and integration tests for success and failure paths.

Not included:

- Streaming trace UI.
- Cost optimization or token-budget planning.
- Advanced scorecard scoring beyond deterministic MVP baseline.
- Frontend trace panel implementation.
- New database tables beyond using existing `queries`, `agent_traces`, and `scorecards`.

## Runtime Contract

`POST /query` keeps the same endpoint and request body shape:

```json
{
  "query": "What does the uploaded policy say?",
  "session_id": "12121212-1212-1212-1212-121212121212",
  "top_k": 5
}
```

The backend resolves the selected team from the session. Phase 8 can add explicit team selection by creating or updating the session before the query call.

Response shape:

```json
{
  "query_id": "query-uuid",
  "query": "What does the uploaded policy say?",
  "final_answer": "Final answer returned by the selected orchestration strategy.",
  "reasoning": null,
  "sources": [
    {
      "document_id": "doc-uuid",
      "filename": "policy.pdf",
      "chunk_index": 0,
      "content_preview": "Relevant source text",
      "score": 0.91
    }
  ],
  "citations": [
    {
      "document_id": "doc-uuid",
      "filename": "policy.pdf",
      "chunk_index": 0,
      "source_index": 1
    }
  ],
  "traces": [
    {
      "id": "trace-uuid",
      "agent_id": "agent-uuid",
      "agent_name": "Researcher",
      "agent_role": "researcher",
      "model_provider": "groq",
      "model_name": "llama-3.1-8b-instant",
      "status": "completed",
      "latency_ms": 1200,
      "output": "Agent output",
      "error": null,
      "citations": []
    }
  ],
  "scorecard": {
    "overall_quality": 7,
    "citation_accuracy": 7,
    "insight_depth": 7,
    "model_contribution_breakdown": {
      "Researcher": "completed"
    },
    "notes": "MVP deterministic scorecard."
  },
  "retrieval_count": 1,
  "insufficient_context": false,
  "model_version": "configured-model-version",
  "retrieval_metadata": {
    "embedding_model_version": "configured-embedding-model",
    "index_version": "configured-index-version",
    "top_k": 5
  }
}
```

Failure response behavior:

- Invalid query payload: `400`.
- Session/team access failure: `403`.
- Team has no agents: `409`.
- Unsupported `collaboration_rule` from persisted data: `400` with team and rule context.
- Unsupported provider/model at runtime: `400` if configuration is invalid.
- Provider execution failure: `503` with agent name, provider, and model in the detail.
- Every orchestration failure after query creation persists at least one failed `agent_traces` row.

## Strategy Semantics

### Sequential

- Load agents ordered by `execution_order`, then `created_at`.
- Run every agent once.
- Each step receives the user query, retrieved context, and all previous agent outputs.
- Final answer is the last `synthesizer` output if any synthesizer ran; otherwise the last agent output.
- If any agent fails, stop the strategy, persist the failed trace, emit failure events, and return a clear `503`.

### Debate

- Requires at least two agents.
- Resolver priority: first agent with role `critic`, `reviewer`, or `judge`; otherwise the highest ordered agent.
- Phase A independent responders: all agents except the resolver.
- If Phase A has only one responder and there are at least two agents, include the resolver in Phase A as an opening position, then run the resolver again in Phase B.
- Phase B resolver receives the user query, retrieved context, and all Phase A outputs.
- Optional final synthesizer pass: use a separate `synthesizer` agent only if it was not already used as a Phase A responder or resolver.
- Final answer is the synthesizer output when present; otherwise the resolver output.

### Hierarchical

- Requires at least two agents.
- Planner priority: first role `planner`, `controller`, or `manager`; otherwise first ordered agent.
- Worker set: all agents except planner and final synthesizer/manager when a separate final agent exists.
- If no worker remains after role selection, use all non-planner agents as workers.
- Final merger priority: first separate role `synthesizer`, `manager`, or `controller`; otherwise the planner performs the merge.
- Planner decomposes the query into deterministic subtasks. For MVP, workers can receive the full query plus their assigned role-specific subtask text; no complex task graph is needed.
- Final answer is the merger output.

## Files

Create:

- `backend/llms/router.py` - strict provider/model dispatch for agent steps.
- `backend/rag/orchestrator.py` - orchestration types, prompt builder, strategy router, and three strategy implementations.
- `backend/tests/unit/test_llm_router.py` - provider/model enforcement tests.
- `backend/tests/unit/test_orchestrator_sequential.py` - sequential ordering, trace, final-answer, and failure tests.
- `backend/tests/unit/test_orchestrator_debate.py` - debate phase routing and resolver tests.
- `backend/tests/unit/test_orchestrator_hierarchical.py` - planner/worker/merger routing tests.
- `backend/tests/integration/test_query_orchestration_modes.py` - end-to-end query response and persisted trace checks for all three rules.
- `backend/tests/integration/test_query_orchestration_failures.py` - model failure surfaces clearly and persists failed traces.

Modify:

- `backend/db/supabase.py` - add fallback storage plus Supabase methods for query pre-creation, query update, agent traces, scorecards.
- `backend/routers/query.py` - use orchestrator, expand response model, preserve auth/session/team checks.
- `backend/rag/generator.py` - keep as legacy/simple RAG helper or refactor to call `LLMRouter` only where compatible.
- `backend/routers/teams.py` - keep rule validation aligned with runtime guardrails.
- `supabase/migrations/005_mvp_agent_schema.sql` and `supabase/migrations/006_schema_normalization_and_session_logs_rls.sql` - inspect only; add a new migration only if live schema is missing fields required by this plan.
- `Plan.md` - optional follow-up edit to replace the old sequential-only Phase 7 wording with a pointer to this file.

## Task 1: Repository Persistence Contract

**Files:**

- Modify: `backend/db/supabase.py`
- Test: `backend/tests/unit/test_query_persistence.py`

- [x] **Step 1: Add failing tests for pre-created queries**

Add tests that prove a query can be created before final answer generation and updated after orchestration:

```python
def test_create_and_update_query_in_memory() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session = repository.create_session(user_id=user_id, session_id="12121212-1212-1212-1212-121212121212")

    query = repository.create_query(
        user_id=user_id,
        session_id=str(session["id"]),
        query_text="What changed?",
        response_time_ms=None,
    )
    assert query["final_answer"] is None

    updated = repository.update_query_result(
        user_id=user_id,
        query_id=str(query["id"]),
        final_answer="Final answer",
        scorecard={"overall": 7, "citation_accuracy": 7, "insight_depth": 7},
        response_time_ms=123,
    )
    assert updated["final_answer"] == "Final answer"
    assert updated["overall_score"] == 7
```

- [x] **Step 2: Run the test and verify it fails**

Run:

```bash
cd backend && pytest tests/unit/test_query_persistence.py::test_create_and_update_query_in_memory -v
```

Expected: fail because `create_query` and `update_query_result` do not exist.

- [x] **Step 3: Implement repository query creation/update**

Add methods to `SupabaseRepository`:

```python
def create_query(
    self,
    user_id: str,
    session_id: str,
    query_text: str,
    response_time_ms: int | None = None,
) -> dict[str, Any]:
    self._ensure_session_owned(session_id=session_id, user_id=user_id)
    payload = {
        "id": str(uuid4()),
        "session_id": session_id,
        "query_text": query_text,
        "final_answer": None,
        "overall_score": None,
        "citation_accuracy": None,
        "insight_depth": None,
        "response_time_ms": response_time_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if self._client:
        result = self._client.table("queries").insert(payload).execute()
        if result.data:
            return result.data[0]
        raise RuntimeError("Failed to create query")
    _FALLBACK.queries.append(payload)
    return payload

def update_query_result(
    self,
    user_id: str,
    query_id: str,
    final_answer: str,
    scorecard: dict[str, Any] | None,
    response_time_ms: int,
) -> dict[str, Any]:
    scorecard = scorecard or {}
    payload = {
        "final_answer": final_answer,
        "overall_score": scorecard.get("overall") or scorecard.get("overall_quality"),
        "citation_accuracy": scorecard.get("citation_accuracy"),
        "insight_depth": scorecard.get("insight_depth"),
        "response_time_ms": response_time_ms,
    }
    if self._client:
        result = self._client.table("queries").update(payload).eq("id", query_id).execute()
        if not result.data:
            raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)
        row = result.data[0]
        self._ensure_session_owned(session_id=str(row["session_id"]), user_id=user_id)
        return row
    for row in _FALLBACK.queries:
        if row.get("id") == query_id:
            self._ensure_session_owned(session_id=str(row["session_id"]), user_id=user_id)
            row.update(payload)
            return row
    raise PermissionError(SESSION_ACCESS_ERROR_MESSAGE)
```

- [x] **Step 4: Add trace and scorecard tests**

Add tests:

```python
def test_agent_traces_and_scorecard_in_memory() -> None:
    repository = SupabaseRepository()
    user_id = "00000000-0000-0000-0000-000000000001"
    session = repository.create_session(user_id=user_id, session_id="12121212-1212-1212-1212-121212121212")
    query = repository.create_query(user_id=user_id, session_id=str(session["id"]), query_text="Question")

    trace = repository.create_agent_trace(
        user_id=user_id,
        session_id=str(session["id"]),
        query_id=str(query["id"]),
        agent_id=None,
        agent_name="Researcher",
        agent_role="researcher",
        model_provider="groq",
        model_name="llama-3.1-8b-instant",
        input_payload={"query": "Question"},
        output="Answer",
        citations=[],
        latency_ms=10,
        status="completed",
        error=None,
    )
    scorecard = repository.save_scorecard(
        user_id=user_id,
        session_id=str(session["id"]),
        query_id=str(query["id"]),
        overall_quality=7,
        citation_accuracy=7,
        insight_depth=7,
        model_contribution_breakdown={"Researcher": "completed"},
        notes="MVP deterministic scorecard.",
    )

    assert trace["status"] == "completed"
    assert repository.list_agent_traces(user_id=user_id, session_id=str(session["id"]), query_id=str(query["id"])) == [trace]
    assert scorecard["overall_quality"] == 7
```

- [x] **Step 5: Implement trace and scorecard methods**

Add `_FALLBACK.agent_traces` and `_FALLBACK.scorecards`, then add:

```python
def create_agent_trace(...)
def list_agent_traces(...)
def save_scorecard(...)
```

The Supabase implementation writes to `agent_traces` and `scorecards`. The fallback implementation appends dictionaries and sorts traces by `created_at`.

- [x] **Step 6: Verify repository tests**

Run:

```bash
cd backend && pytest tests/unit/test_query_persistence.py -v
```

Expected: all tests in the file pass.

## Task 2: Strict LLM Router

**Files:**

- Create: `backend/llms/router.py`
- Test: `backend/tests/unit/test_llm_router.py`

- [x] **Step 1: Write failing router tests**

Test required behavior:

```python
def test_router_dispatches_to_agent_provider_and_model() -> None:
    calls = []

    class FakeClient:
        def chat(self, messages, model, metadata=None):
            calls.append({"messages": messages, "model": model, "metadata": metadata})
            return "agent output"

    router = LLMRouter(provider_clients={"groq": FakeClient()})
    output = router.chat(
        provider="groq",
        model_name="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": "question"}],
        metadata={"agent_id": "a1"},
    )

    assert output == "agent output"
    assert calls[0]["model"] == "llama-3.1-8b-instant"
    assert calls[0]["metadata"]["agent_id"] == "a1"
```

Also test:

```python
def test_router_rejects_unknown_provider() -> None:
    router = LLMRouter(provider_clients={})
    with pytest.raises(LLMRouterError, match="Unsupported model provider"):
        router.chat(provider="unknown", model_name="model", messages=[], metadata={})
```

- [x] **Step 2: Run tests and verify failure**

Run:

```bash
cd backend && pytest tests/unit/test_llm_router.py -v
```

Expected: fail because `backend/llms/router.py` does not exist.

- [x] **Step 3: Implement `LLMRouter`**

Minimum public API:

```python
class LLMRouterError(RuntimeError):
    pass

class LLMRouter:
    def __init__(self, provider_clients: dict[str, Any] | None = None) -> None:
        self._provider_clients = provider_clients

    def chat(
        self,
        provider: str,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        ...
```

Provider behavior:

- `groq`: call `GroqClient().chat(messages=messages, model=model_name, metadata=metadata)`.
- `sarvam`: call `SarvamClient().chat(messages=messages, model=model_name, metadata=metadata)`.
- `lmstudio`: call an OpenAI-compatible local endpoint using `provider_base_url` and optional passcode from metadata.
- Unknown provider: raise `LLMRouterError("Unsupported model provider: <provider>")`.
- Any provider failure: raise `LLMRouterError` with provider, model, and agent identity in the message.

- [x] **Step 4: Verify router tests**

Run:

```bash
cd backend && pytest tests/unit/test_llm_router.py -v
```

Expected: all router tests pass.

## Task 3: Orchestration Core Types and Shared Primitives

**Files:**

- Create: `backend/rag/orchestrator.py`
- Test: `backend/tests/unit/test_orchestrator_sequential.py`

- [x] **Step 1: Add failing dispatch test**

```python
def test_orchestrator_dispatches_by_collaboration_rule() -> None:
    orchestrator = Orchestrator(
        repository=FakeTraceRepository(),
        llm_router=FakeLLMRouter(outputs=["seq output"]),
        observer=FakeObserver(),
    )

    result = orchestrator.run(
        QueryContext(user_id="u1", session_id="s1", query_id="q1", query="Question", request_id="req-1"),
        team={"id": "t1", "domain": "Policy", "collaboration_rule": "sequential"},
        agents=[agent("Researcher", "researcher", 0)],
        retrieved_context=[source("doc1")],
    )

    assert result.final_answer == "seq output"
    assert result.collaboration_rule == "sequential"
```

- [x] **Step 2: Implement core types**

Define these in `backend/rag/orchestrator.py`:

```python
@dataclass(frozen=True)
class QueryContext:
    user_id: str
    session_id: str
    query_id: str
    query: str
    request_id: str

@dataclass(frozen=True)
class AgentStepTrace:
    id: str | None
    agent_id: str | None
    agent_name: str
    agent_role: str
    model_provider: str
    model_name: str
    status: str
    latency_ms: int | None
    output: str
    error: str | None
    citations: list[dict[str, Any]]

@dataclass(frozen=True)
class OrchestrationResult:
    final_answer: str
    traces: list[AgentStepTrace]
    citations: list[dict[str, Any]]
    scorecard: dict[str, Any]
    collaboration_rule: str
```

Implement shared helpers:

- `build_agent_messages(...)`
- `package_citations(sources)`
- `build_scorecard(traces)`
- `normalize_agent_error(agent, provider, model, error)`
- `record_orchestration_event(observer, ...)`

- [x] **Step 3: Implement strategy router**

`Orchestrator.run(...)` maps:

- `sequential` -> `SequentialStrategy`
- `debate` -> `DebateStrategy`
- `hierarchical` -> `HierarchicalStrategy`

Unsupported values raise `OrchestrationConfigError`.

- [x] **Step 4: Verify initial orchestration test**

Run:

```bash
cd backend && pytest tests/unit/test_orchestrator_sequential.py::test_orchestrator_dispatches_by_collaboration_rule -v
```

Expected: pass.

## Task 4: Sequential Strategy

**Files:**

- Modify: `backend/rag/orchestrator.py`
- Test: `backend/tests/unit/test_orchestrator_sequential.py`

- [x] **Step 1: Test ordering and final answer selection**

```python
def test_sequential_runs_agents_by_execution_order_and_uses_synthesizer_final() -> None:
    llm = FakeLLMRouter(outputs=["research", "critique", "synthesis"])
    repository = FakeTraceRepository()
    result = Orchestrator(repository=repository, llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("sequential"),
        agents=[
            agent("Synthesizer", "synthesizer", 2),
            agent("Researcher", "researcher", 0),
            agent("Critic", "critic", 1),
        ],
        retrieved_context=[source("doc1")],
    )

    assert [call["agent_name"] for call in llm.calls] == ["Researcher", "Critic", "Synthesizer"]
    assert result.final_answer == "synthesis"
    assert [trace.status for trace in result.traces] == ["completed", "completed", "completed"]
    assert len(repository.traces) == 3
```

- [x] **Step 2: Test failed step persistence**

```python
def test_sequential_persists_failed_trace_and_stops() -> None:
    llm = FakeLLMRouter(outputs=["research"], error_on_call=2)
    repository = FakeTraceRepository()

    with pytest.raises(OrchestrationExecutionError, match="Critic"):
        Orchestrator(repository=repository, llm_router=llm, observer=FakeObserver()).run(
            query_context(),
            team("sequential"),
            agents=[agent("Researcher", "researcher", 0), agent("Critic", "critic", 1)],
            retrieved_context=[source("doc1")],
        )

    assert repository.traces[-1]["agent_name"] == "Critic"
    assert repository.traces[-1]["status"] == "failed"
    assert "model_provider" in repository.traces[-1]
```

- [x] **Step 3: Implement sequential behavior**

Implementation rules:

- Sort agents by `execution_order`, then `created_at`.
- Build messages from query, team domain, retrieved context, and prior outputs.
- Call `LLMRouter.chat()` with the agent's exact `model_provider` and `model_name`.
- Persist a trace immediately after each completed or failed step.
- Emit `agent_step_started`, `agent_step_completed`, and `agent_step_failed`.
- Return final synthesizer output if present, else last output.

- [x] **Step 4: Verify sequential unit tests**

Run:

```bash
cd backend && pytest tests/unit/test_orchestrator_sequential.py -v
```

Expected: all sequential tests pass.

## Task 5: Debate Strategy

**Files:**

- Modify: `backend/rag/orchestrator.py`
- Test: `backend/tests/unit/test_orchestrator_debate.py`

- [x] **Step 1: Test default three-agent debate**

```python
def test_debate_uses_independent_phase_then_critic_resolver() -> None:
    llm = FakeLLMRouter(outputs=["research position", "synthesis position", "resolved answer"])
    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("debate"),
        agents=[
            agent("Researcher", "researcher", 0),
            agent("Critic", "critic", 1),
            agent("Synthesizer", "synthesizer", 2),
        ],
        retrieved_context=[source("doc1")],
    )

    assert [call["agent_name"] for call in llm.calls] == ["Researcher", "Synthesizer", "Critic"]
    assert result.final_answer == "resolved answer"
    assert len(result.traces) == 3
```

- [x] **Step 2: Test debate guardrail**

```python
def test_debate_requires_at_least_two_agents() -> None:
    with pytest.raises(OrchestrationConfigError, match="debate requires at least two agents"):
        Orchestrator(repository=FakeTraceRepository(), llm_router=FakeLLMRouter(), observer=FakeObserver()).run(
            query_context(),
            team("debate"),
            agents=[agent("Solo", "researcher", 0)],
            retrieved_context=[],
        )
```

- [x] **Step 3: Implement debate behavior**

Implementation rules:

- Resolver is first `critic`, `reviewer`, or `judge`; otherwise highest ordered agent.
- Phase A responders are all agents except resolver.
- If Phase A has one responder, include resolver in Phase A and run resolver again in Phase B.
- Resolver prompt must include every Phase A output and ask for conflict resolution.
- Separate synthesizer final pass is allowed only when that synthesizer was not used earlier.
- Persist every Phase A, resolver, and finalizer step.

- [x] **Step 4: Verify debate unit tests**

Run:

```bash
cd backend && pytest tests/unit/test_orchestrator_debate.py -v
```

Expected: all debate tests pass.

## Task 6: Hierarchical Strategy

**Files:**

- Modify: `backend/rag/orchestrator.py`
- Test: `backend/tests/unit/test_orchestrator_hierarchical.py`

- [x] **Step 1: Test planner, workers, merger flow**

```python
def test_hierarchical_runs_planner_workers_then_merger() -> None:
    llm = FakeLLMRouter(outputs=["plan", "worker research", "worker critique", "merged answer"])
    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("hierarchical"),
        agents=[
            agent("Planner", "planner", 0),
            agent("Researcher", "researcher", 1),
            agent("Critic", "critic", 2),
            agent("Synthesizer", "synthesizer", 3),
        ],
        retrieved_context=[source("doc1")],
    )

    assert [call["agent_name"] for call in llm.calls] == ["Planner", "Researcher", "Critic", "Synthesizer"]
    assert result.final_answer == "merged answer"
```

- [x] **Step 2: Test role fallback**

```python
def test_hierarchical_falls_back_to_first_agent_as_planner_and_last_as_merger() -> None:
    llm = FakeLLMRouter(outputs=["plan", "worker output", "merged answer"])
    result = Orchestrator(repository=FakeTraceRepository(), llm_router=llm, observer=FakeObserver()).run(
        query_context(),
        team("hierarchical"),
        agents=[agent("A", "assistant", 0), agent("B", "assistant", 1)],
        retrieved_context=[],
    )

    assert [call["agent_name"] for call in llm.calls] == ["A", "B", "A"]
    assert result.final_answer == "merged answer"
```

- [x] **Step 3: Implement hierarchical behavior**

Implementation rules:

- Planner: role `planner`, `controller`, or `manager`; fallback first ordered agent.
- Merger: separate role `synthesizer`, `manager`, or `controller`; fallback planner.
- Workers: all agents not selected as planner or separate merger.
- Planner output is passed to all workers.
- Worker outputs are passed to merger.
- Persist planner, worker, and merger traces.

- [x] **Step 4: Verify hierarchical unit tests**

Run:

```bash
cd backend && pytest tests/unit/test_orchestrator_hierarchical.py -v
```

Expected: all hierarchical tests pass.

## Task 7: Query Endpoint Integration

**Files:**

- Modify: `backend/routers/query.py`
- Test: `backend/tests/integration/test_query_orchestration_modes.py`

- [x] **Step 1: Write integration tests for all three rules**

Each test should:

- Create a team with the target `collaboration_rule`.
- Create a session for that team.
- Create agents with provider/model values.
- Monkeypatch retrieval to return one formatted source.
- Monkeypatch `LLMRouter` to return deterministic outputs.
- Call `POST /query`.
- Assert `200`.
- Assert `final_answer`.
- Assert `traces`.
- Assert `scorecard`.
- Assert persisted traces can be listed from `SupabaseRepository`.

Use this command:

```bash
cd backend && pytest tests/integration/test_query_orchestration_modes.py -v
```

Expected before implementation: fail because `/query` does not return traces or scorecard.

- [x] **Step 2: Refactor `QueryResponse`**

Add Pydantic models:

```python
class CitationItem(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    source_index: int

class AgentTraceItem(BaseModel):
    id: str | None = None
    agent_id: str | None = None
    agent_name: str
    agent_role: str
    model_provider: str
    model_name: str
    status: str
    latency_ms: int | None = None
    output: str
    error: str | None = None
    citations: list[dict[str, Any]]

class ScorecardResponse(BaseModel):
    overall_quality: int | None = None
    citation_accuracy: int | None = None
    insight_depth: int | None = None
    model_contribution_breakdown: dict[str, Any]
    notes: str | None = None
```

Extend `QueryResponse` with:

```python
citations: list[CitationItem] = []
traces: list[AgentTraceItem] = []
scorecard: ScorecardResponse | None = None
```

- [x] **Step 3: Replace generation path with orchestrator call**

Flow inside `run_query`:

1. Validate auth.
2. Load or create session.
3. Load team from `session.team_id`.
4. Load agents with `repository.list_agents(...)`.
5. Reject no-agent team with existing `409`.
6. Retrieve and format sources.
7. Create query row with `repository.create_query(...)`.
8. Call `Orchestrator.run(...)`.
9. Save scorecard with `repository.save_scorecard(...)`.
10. Update query row with `repository.update_query_result(...)`.
11. Return final answer, sources, citations, traces, and scorecard.

- [x] **Step 4: Preserve insufficient-context behavior**

When retrieval returns no sources:

- Create and update a query row with the existing insufficient-context answer.
- Return `traces=[]`.
- Return a baseline scorecard with low or null scores.
- Do not call agents, because they have no retrieved evidence.

- [x] **Step 5: Verify integration mode tests**

Run:

```bash
cd backend && pytest tests/integration/test_query_orchestration_modes.py -v
```

Expected: sequential, debate, and hierarchical tests pass.

## Task 8: Failure and Observability Coverage

**Files:**

- Modify: `backend/rag/orchestrator.py`
- Modify: `backend/routers/query.py`
- Test: `backend/tests/integration/test_query_orchestration_failures.py`
- Test: `backend/tests/unit/test_observability.py`

- [x] **Step 1: Write model failure integration tests**

One test per rule:

```python
@pytest.mark.parametrize("rule", ["sequential", "debate", "hierarchical"])
async def test_query_model_failure_persists_failed_trace(rule: str) -> None:
    ...
    response = await client.post("/query", json={"query": "Question", "session_id": session_id, "top_k": 1})
    assert response.status_code == 503
    assert "agent" in response.json()["detail"].lower()
    traces = repository.list_agent_traces(user_id=user_id, session_id=session_id, query_id=query_id)
    assert any(trace["status"] == "failed" for trace in traces)
```

- [x] **Step 2: Emit required ClickHouse events**

Use existing `observer.record_trace_event(...)` with:

- `orchestration_started`
- `orchestration_finished`
- `orchestration_failed`
- `agent_step_started`
- `agent_step_completed`
- `agent_step_failed`

Metadata for every event:

```python
{
    "team_id": team_id,
    "session_id": session_id,
    "query_id": query_id,
    "collaboration_rule": rule,
    "agent_id": agent_id,
    "role": agent_role,
    "model_provider": model_provider,
    "model_name": model_name,
    "latency_ms": latency_ms,
}
```

- [x] **Step 3: Verify failure tests**

Run:

```bash
cd backend && pytest tests/integration/test_query_orchestration_failures.py -v
```

Expected: all failure tests pass and every failed run has a persisted failed trace.

## Task 9: Rule-Aware Guardrails

**Files:**

- Modify: `backend/routers/query.py`
- Modify: `backend/rag/orchestrator.py`
- Test: `backend/tests/integration/test_query_requires_agents.py`

- [x] **Step 1: Extend existing no-agent test**

Keep the current `409` behavior for every rule:

```python
@pytest.mark.parametrize("rule", ["sequential", "debate", "hierarchical"])
async def test_query_requires_at_least_one_agent_for_team(rule: str) -> None:
    ...
    assert response.status_code == 409
```

- [x] **Step 2: Add rule-specific guardrail tests**

```python
async def test_debate_requires_two_agents() -> None:
    ...
    assert response.status_code == 400
    assert "debate requires at least two agents" in response.json()["detail"]

async def test_hierarchical_requires_two_agents() -> None:
    ...
    assert response.status_code == 400
    assert "hierarchical requires at least two agents" in response.json()["detail"]
```

- [x] **Step 3: Implement guardrails**

Rules:

- `sequential`: at least one agent.
- `debate`: at least two agents.
- `hierarchical`: at least two agents.
- Unknown rule: `400` with `Unsupported collaboration_rule '<rule>' for team '<team_id>'`.

- [x] **Step 4: Verify guardrail tests**

Run:

```bash
cd backend && pytest tests/integration/test_query_requires_agents.py -v
```

Expected: all guardrail tests pass.

## Task 10: Final Verification and Plan.md Alignment

**Files:**

- Optional modify: `Plan.md`
- Generated update: `graphify-out/*`

- [x] **Step 1: Run unit orchestration suite**

```bash
cd backend && pytest \
  tests/unit/test_llm_router.py \
  tests/unit/test_orchestrator_sequential.py \
  tests/unit/test_orchestrator_debate.py \
  tests/unit/test_orchestrator_hierarchical.py \
  tests/unit/test_query_persistence.py \
  -v
```

Expected: all selected unit tests pass.

- [x] **Step 2: Run integration orchestration suite**

```bash
cd backend && pytest \
  tests/integration/test_query_requires_agents.py \
  tests/integration/test_query_orchestration_modes.py \
  tests/integration/test_query_orchestration_failures.py \
  -v
```

Expected: all selected integration tests pass.

- [x] **Step 3: Run existing query/history regression tests**

```bash
cd backend && pytest \
  tests/unit/test_query_response_format.py \
  tests/integration/test_dashboard_history.py \
  -v
```

Expected: existing query response parsing and dashboard history behavior remain compatible.

- [x] **Step 4: Update graphify after implementation**

```bash
graphify update .
```

Expected: graph updates successfully with no API-cost AST update path.

- [x] **Step 5: Optional Plan.md edit**

Replace the old Phase 7 heading with:

```markdown
# Phase 7 - Implement Multi-Architecture Orchestration

Runtime scope: sequential, debate, and hierarchical orchestration are implemented together.

Detailed implementation plan: `Implement Multi-Architecture Orchestration.md`.
```

Do not edit unrelated Plan.md sections in the same commit.

## Acceptance Criteria

- `sequential`, `debate`, and `hierarchical` execute at runtime based on `team.collaboration_rule`.
- Every agent step uses the assigned `model_provider` and `model_name`.
- Every completed or failed step is persisted in `agent_traces`.
- Final answer is returned from `POST /query`.
- `POST /query` returns `traces[]`, `citations[]`, and `scorecard`.
- Baseline scorecard is saved in `scorecards`.
- Provider failures include agent identity, provider, and model.
- ClickHouse trace events cover orchestration lifecycle and agent-step lifecycle.
- Fallback repository supports queries, traces, and scorecards so integration tests remain deterministic without live Supabase.
- Existing auth/session/team ownership checks remain intact.

## Parallel Workstream Split

- Worker A: repository persistence and query pre-create/update methods.
- Worker B: `LLMRouter` and provider-specific error handling.
- Worker C: orchestration strategies and unit tests.
- Worker D: query endpoint integration and response contract.
- Worker E: integration/failure tests and observability assertions.

Workstreams A and B can start immediately. Workstream C depends on the public interfaces from A and B. Workstream D depends on A and C. Workstream E can start by writing failing tests once D defines response models.

## Commit Plan

1. `feat: add orchestration persistence contracts`
2. `feat: add strict llm router`
3. `feat: add multi-architecture orchestrator`
4. `feat: route query endpoint through orchestrator`
5. `test: cover orchestration modes and failures`
6. `docs: align phase 7 orchestration plan`
