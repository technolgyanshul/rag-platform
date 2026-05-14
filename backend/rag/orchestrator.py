from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol


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


class OrchestrationConfigError(ValueError):
    pass


class OrchestrationExecutionError(RuntimeError):
    pass


class _Repository(Protocol):
    def create_agent_trace(self, **kwargs: Any) -> dict[str, Any]: ...

    def save_scorecard(self, **kwargs: Any) -> dict[str, Any]: ...


class _LLMRouter(Protocol):
    def chat(
        self,
        provider: str,
        model_name: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> str: ...


class _Observer(Protocol):
    def record_trace_event(self, **kwargs: Any) -> None: ...


def build_agent_messages(
    *,
    query: str,
    team_domain: str,
    agent: dict[str, Any],
    retrieved_context: list[dict[str, Any]],
    previous_outputs: list[dict[str, str]] | None = None,
    instruction: str | None = None,
) -> list[dict[str, str]]:
    role = str(agent.get("role") or "agent")
    name = str(agent.get("name") or role)
    system_prompt = str(agent.get("system_prompt") or f"You are {name}, acting as {role}.")
    context_lines = _format_context(retrieved_context)
    previous_lines = _format_previous_outputs(previous_outputs or [])
    user_parts = [
        f"User query: {query}",
        f"Team domain: {team_domain or 'General'}",
        "Retrieved context:",
        context_lines or "No retrieved context was provided.",
    ]
    if previous_lines:
        user_parts.extend(["Previous agent outputs:", previous_lines])
    if instruction:
        user_parts.extend(["Task instruction:", instruction])

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def package_citations(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        citations.append(
            {
                "document_id": str(source.get("document_id", "")),
                "filename": str(source.get("filename", "unknown")),
                "chunk_index": int(source.get("chunk_index", -1)),
                "source_index": index,
            }
        )
    return citations


def build_scorecard(traces: list[AgentStepTrace]) -> dict[str, Any]:
    failed = any(trace.status == "failed" for trace in traces)
    baseline = 3 if failed else 7
    return {
        "overall_quality": baseline,
        "citation_accuracy": baseline,
        "insight_depth": baseline,
        "model_contribution_breakdown": {trace.agent_name: trace.status for trace in traces},
        "notes": "MVP deterministic scorecard.",
    }


def normalize_agent_error(agent: dict[str, Any], provider: str, model: str, error: BaseException) -> str:
    name = str(agent.get("name") or "Agent")
    return f"{name} failed using provider {provider} and model {model}: {error}"


def record_orchestration_event(
    observer: _Observer | None,
    *,
    event_name: str,
    context: QueryContext,
    level: str = "INFO",
    status: str = "",
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
    error: BaseException | None = None,
) -> None:
    if observer is None:
        return
    observer.record_trace_event(
        event_name=event_name,
        request_id=context.request_id,
        trace_id=context.query_id,
        user_id=context.user_id,
        route="/query",
        component="orchestrator",
        level=level,
        status=status,
        duration_ms=duration_ms,
        metadata=metadata or {},
        error=error,
    )


class Orchestrator:
    def __init__(self, repository: _Repository, llm_router: _LLMRouter, observer: _Observer | None = None) -> None:
        self.repository = repository
        self.llm_router = llm_router
        self.observer = observer

    def run(
        self,
        query_context: QueryContext,
        team: dict[str, Any],
        agents: list[dict[str, Any]],
        retrieved_context: list[dict[str, Any]],
    ) -> OrchestrationResult:
        rule = str(team.get("collaboration_rule") or "sequential").lower()
        ordered_agents = _sort_agents(agents)
        record_orchestration_event(
            self.observer,
            event_name="orchestration_started",
            context=query_context,
            status="started",
            metadata={"team_id": team.get("id"), "collaboration_rule": rule, "agent_count": len(ordered_agents)},
        )

        try:
            if rule == "sequential":
                traces, final_answer = self._run_sequential(query_context, team, ordered_agents, retrieved_context)
            elif rule == "debate":
                traces, final_answer = self._run_debate(query_context, team, ordered_agents, retrieved_context)
            elif rule == "hierarchical":
                traces, final_answer = self._run_hierarchical(query_context, team, ordered_agents, retrieved_context)
            else:
                raise OrchestrationConfigError(f"Unsupported collaboration rule '{rule}' for team {team.get('id')}")
        except (OrchestrationConfigError, OrchestrationExecutionError) as error:
            record_orchestration_event(
                self.observer,
                event_name="orchestration_failed",
                context=query_context,
                level="ERROR",
                status="failed",
                metadata={"team_id": team.get("id"), "collaboration_rule": rule},
                error=error,
            )
            raise

        scorecard = build_scorecard(traces)
        self.repository.save_scorecard(
            user_id=query_context.user_id,
            session_id=query_context.session_id,
            query_id=query_context.query_id,
            **scorecard,
        )
        record_orchestration_event(
            self.observer,
            event_name="orchestration_finished",
            context=query_context,
            status="completed",
            metadata={"team_id": team.get("id"), "collaboration_rule": rule, "trace_count": len(traces)},
        )
        return OrchestrationResult(
            final_answer=final_answer,
            traces=traces,
            citations=package_citations(retrieved_context),
            scorecard=scorecard,
            collaboration_rule=rule,
        )

    def _run_sequential(
        self,
        context: QueryContext,
        team: dict[str, Any],
        agents: list[dict[str, Any]],
        retrieved_context: list[dict[str, Any]],
    ) -> tuple[list[AgentStepTrace], str]:
        if not agents:
            raise OrchestrationConfigError("sequential requires at least one agent")
        traces: list[AgentStepTrace] = []
        previous_outputs: list[dict[str, str]] = []
        synthesizer_output: str | None = None

        for current_agent in agents:
            trace = self._execute_agent_step(
                context=context,
                team=team,
                agent=current_agent,
                retrieved_context=retrieved_context,
                previous_outputs=previous_outputs,
            )
            traces.append(trace)
            previous_outputs.append({"agent_name": trace.agent_name, "agent_role": trace.agent_role, "output": trace.output})
            if trace.agent_role.lower() == "synthesizer":
                synthesizer_output = trace.output

        return traces, synthesizer_output if synthesizer_output is not None else traces[-1].output

    def _run_debate(
        self,
        context: QueryContext,
        team: dict[str, Any],
        agents: list[dict[str, Any]],
        retrieved_context: list[dict[str, Any]],
    ) -> tuple[list[AgentStepTrace], str]:
        if len(agents) < 2:
            raise OrchestrationConfigError("debate requires at least two agents")

        resolver = _first_agent_with_role(agents, {"critic", "reviewer", "judge"}) or agents[-1]
        finalizer = _debate_finalizer(agents, resolver)
        phase_a_agents = [agent for agent in agents if agent is not resolver and agent is not finalizer]
        if len(phase_a_agents) == 1:
            phase_a_agents.append(resolver)
        if not phase_a_agents:
            phase_a_agents = [agent for agent in agents if agent is not finalizer]

        traces: list[AgentStepTrace] = []
        phase_outputs: list[dict[str, str]] = []
        used_ids: set[int] = set()
        for current_agent in phase_a_agents:
            trace = self._execute_agent_step(
                context=context,
                team=team,
                agent=current_agent,
                retrieved_context=retrieved_context,
                previous_outputs=[],
                instruction="State your independent debate position using the retrieved evidence.",
            )
            traces.append(trace)
            phase_outputs.append({"agent_name": trace.agent_name, "agent_role": trace.agent_role, "output": trace.output})
            used_ids.add(id(current_agent))

        resolver_trace = self._execute_agent_step(
            context=context,
            team=team,
            agent=resolver,
            retrieved_context=retrieved_context,
            previous_outputs=phase_outputs,
            instruction="Resolve the debate. Compare the positions, handle conflicts, and produce the best supported answer.",
        )
        traces.append(resolver_trace)
        used_ids.add(id(resolver))
        final_answer = resolver_trace.output

        if finalizer is not None and id(finalizer) not in used_ids:
            finalizer_trace = self._execute_agent_step(
                context=context,
                team=team,
                agent=finalizer,
                retrieved_context=retrieved_context,
                previous_outputs=[*phase_outputs, {"agent_name": resolver_trace.agent_name, "agent_role": resolver_trace.agent_role, "output": resolver_trace.output}],
                instruction="Produce a final synthesis from the debate positions and resolver decision.",
            )
            traces.append(finalizer_trace)
            final_answer = finalizer_trace.output

        return traces, final_answer

    def _run_hierarchical(
        self,
        context: QueryContext,
        team: dict[str, Any],
        agents: list[dict[str, Any]],
        retrieved_context: list[dict[str, Any]],
    ) -> tuple[list[AgentStepTrace], str]:
        if len(agents) < 2:
            raise OrchestrationConfigError("hierarchical requires at least two agents")

        planner = _first_agent_with_role(agents, {"planner", "controller", "manager"}) or agents[0]
        merger = _first_separate_agent_with_role(agents, planner, {"synthesizer", "manager", "controller"}) or planner
        workers = [agent for agent in agents if agent is not planner and agent is not merger]
        if not workers:
            workers = [agent for agent in agents if agent is not planner]

        traces: list[AgentStepTrace] = []
        planner_trace = self._execute_agent_step(
            context=context,
            team=team,
            agent=planner,
            retrieved_context=retrieved_context,
            previous_outputs=[],
            instruction="Create a concise execution plan and deterministic subtasks for the worker agents.",
        )
        traces.append(planner_trace)

        worker_outputs: list[dict[str, str]] = []
        planner_output = {"agent_name": planner_trace.agent_name, "agent_role": planner_trace.agent_role, "output": planner_trace.output}
        for worker in workers:
            trace = self._execute_agent_step(
                context=context,
                team=team,
                agent=worker,
                retrieved_context=retrieved_context,
                previous_outputs=[planner_output],
                instruction=f"Execute the subtask relevant to your role ({worker.get('role', 'agent')}) using the planner output.",
            )
            traces.append(trace)
            worker_outputs.append({"agent_name": trace.agent_name, "agent_role": trace.agent_role, "output": trace.output})

        merger_trace = self._execute_agent_step(
            context=context,
            team=team,
            agent=merger,
            retrieved_context=retrieved_context,
            previous_outputs=[planner_output, *worker_outputs],
            instruction="Merge the planner and worker outputs into the final answer.",
        )
        traces.append(merger_trace)
        return traces, merger_trace.output

    def _execute_agent_step(
        self,
        *,
        context: QueryContext,
        team: dict[str, Any],
        agent: dict[str, Any],
        retrieved_context: list[dict[str, Any]],
        previous_outputs: list[dict[str, str]],
        instruction: str | None = None,
    ) -> AgentStepTrace:
        provider = str(agent.get("model_provider") or "").strip()
        model = str(agent.get("model_name") or "").strip()
        name = str(agent.get("name") or "Agent")
        role = str(agent.get("role") or "agent")
        if not provider or not model:
            raise OrchestrationConfigError(f"Agent {name} is missing model provider or model name")

        record_orchestration_event(
            self.observer,
            event_name="agent_step_started",
            context=context,
            status="started",
            metadata={
                "team_id": team.get("id"),
                "session_id": context.session_id,
                "query_id": context.query_id,
                "collaboration_rule": team.get("collaboration_rule"),
                "agent_id": agent.get("id"),
                "agent_name": name,
                "role": role,
                "model_provider": provider,
                "model_name": model,
            },
        )
        messages = build_agent_messages(
            query=context.query,
            team_domain=str(team.get("domain") or ""),
            agent=agent,
            retrieved_context=retrieved_context,
            previous_outputs=previous_outputs,
            instruction=instruction,
        )
        start = time.perf_counter()
        try:
            output = self.llm_router.chat(
                provider,
                model,
                messages,
                metadata={
                    "request_id": context.request_id,
                    "query_id": context.query_id,
                    "team_id": team.get("id"),
                    "agent_id": agent.get("id"),
                    "agent_name": name,
                    "agent_role": role,
                    "provider_base_url": agent.get("provider_base_url"),
                    "provider_passcode": agent.get("provider_passcode"),
                },
            )
        except Exception as error:
            latency_ms = int((time.perf_counter() - start) * 1000)
            normalized = normalize_agent_error(agent, provider, model, error)
            trace = self._persist_trace(
                context=context,
                agent=agent,
                provider=provider,
                model=model,
                messages=messages,
                output="",
                citations=[],
                latency_ms=latency_ms,
                status="failed",
                error=normalized,
            )
            record_orchestration_event(
                self.observer,
                event_name="agent_step_failed",
                context=context,
                level="ERROR",
                status="failed",
                duration_ms=latency_ms,
                metadata={
                    "team_id": team.get("id"),
                    "session_id": context.session_id,
                    "query_id": context.query_id,
                    "collaboration_rule": team.get("collaboration_rule"),
                    "agent_id": agent.get("id"),
                    "agent_name": name,
                    "role": role,
                    "model_provider": provider,
                    "model_name": model,
                    "latency_ms": latency_ms,
                },
                error=error,
            )
            raise OrchestrationExecutionError(normalized) from error

        latency_ms = int((time.perf_counter() - start) * 1000)
        trace = self._persist_trace(
            context=context,
            agent=agent,
            provider=provider,
            model=model,
            messages=messages,
            output=output,
            citations=[],
            latency_ms=latency_ms,
            status="completed",
            error=None,
        )
        record_orchestration_event(
            self.observer,
            event_name="agent_step_completed",
            context=context,
            status="completed",
            duration_ms=latency_ms,
            metadata={
                "team_id": team.get("id"),
                "session_id": context.session_id,
                "query_id": context.query_id,
                "collaboration_rule": team.get("collaboration_rule"),
                "agent_id": agent.get("id"),
                "agent_name": name,
                "role": role,
                "model_provider": provider,
                "model_name": model,
                "latency_ms": latency_ms,
            },
        )
        return trace

    def _persist_trace(
        self,
        *,
        context: QueryContext,
        agent: dict[str, Any],
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        output: str,
        citations: list[dict[str, Any]],
        latency_ms: int,
        status: str,
        error: str | None,
    ) -> AgentStepTrace:
        row = self.repository.create_agent_trace(
            user_id=context.user_id,
            session_id=context.session_id,
            query_id=context.query_id,
            agent_id=agent.get("id"),
            agent_name=str(agent.get("name") or "Agent"),
            agent_role=str(agent.get("role") or "agent"),
            model_provider=provider,
            model_name=model,
            input_payload={"query": context.query, "messages": messages},
            output=output,
            citations=citations,
            latency_ms=latency_ms,
            status=status,
            error=error,
        )
        return AgentStepTrace(
            id=str(row.get("id")) if row.get("id") is not None else None,
            agent_id=str(row.get("agent_id")) if row.get("agent_id") is not None else None,
            agent_name=str(row.get("agent_name") or agent.get("name") or "Agent"),
            agent_role=str(row.get("agent_role") or agent.get("role") or "agent"),
            model_provider=str(row.get("model_provider") or provider),
            model_name=str(row.get("model_name") or model),
            status=str(row.get("status") or status),
            latency_ms=int(row["latency_ms"]) if row.get("latency_ms") is not None else None,
            output=str(row.get("output") or ""),
            error=str(row.get("error")) if row.get("error") is not None else None,
            citations=list(row.get("citations") or []),
        )


def _sort_agents(agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(agents, key=lambda agent: (int(agent.get("execution_order") or 0), str(agent.get("created_at") or "")))


def _agent_role(agent: dict[str, Any]) -> str:
    return str(agent.get("role") or "").strip().lower()


def _first_agent_with_role(agents: list[dict[str, Any]], roles: set[str]) -> dict[str, Any] | None:
    return next((agent for agent in agents if _agent_role(agent) in roles), None)


def _first_separate_agent_with_role(agents: list[dict[str, Any]], selected: dict[str, Any], roles: set[str]) -> dict[str, Any] | None:
    return next((agent for agent in agents if agent is not selected and _agent_role(agent) in roles), None)


def _debate_finalizer(agents: list[dict[str, Any]], resolver: dict[str, Any]) -> dict[str, Any] | None:
    # Keep the default critic debate as responder -> critic. Review/judge flows can reserve a synthesizer for a true final pass.
    if _agent_role(resolver) == "critic":
        return None
    return _first_separate_agent_with_role(agents, resolver, {"synthesizer"})


def _format_context(sources: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        preview = source.get("content_preview", source.get("content", ""))
        lines.append(
            f"[{index}] {source.get('filename', 'unknown')} chunk {source.get('chunk_index', -1)} "
            f"score {source.get('score', source.get('similarity', 0.0))}: {preview}"
        )
    return "\n".join(lines)


def _format_previous_outputs(previous_outputs: list[dict[str, str]]) -> str:
    return "\n".join(
        f"- {item.get('agent_name', 'Agent')} ({item.get('agent_role', 'agent')}): {item.get('output', '')}"
        for item in previous_outputs
    )
