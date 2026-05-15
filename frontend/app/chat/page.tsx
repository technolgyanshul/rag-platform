"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { ChatWindow } from "../../components/chat/ChatWindow";
import { QueryInput } from "../../components/chat/QueryInput";
import { SourceList } from "../../components/chat/SourceList";
import { TracePanel } from "../../components/chat/TracePanel";
import { AppShell } from "../../components/layout/AppShell";
import { createSession, listTeamAgents, listTeams, logUiEvent, runQuery } from "../../lib/api";
import { Agent, QueryResponse, QueryUiState, Team } from "../../lib/types";

/** Chat workspace for team-scoped multi-agent query execution. */
export default function ChatPage() {
  const [queryState, setQueryState] = useState<QueryUiState>({ status: "idle" });
  const [teams, setTeams] = useState<Team[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [teamMessage, setTeamMessage] = useState("");

  const selectedTeam = useMemo(
    () => teams.find((team) => team.id === selectedTeamId) ?? null,
    [selectedTeamId, teams],
  );

  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/chat", component: "ChatPage", action: "load" }).catch(() => undefined);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadTeams = async () => {
      setTeamsLoading(true);
      setTeamMessage("");
      try {
        const rows = await listTeams();
        if (cancelled) {
          return;
        }
        setTeams(rows);
        setSelectedTeamId((current) => (current && rows.some((team) => team.id === current) ? current : ""));
        if (rows.length === 0) {
          setTeamMessage("Create a team with at least one agent before running chat.");
        }
      } catch (error) {
        if (!cancelled) {
          setTeamMessage(error instanceof Error ? error.message : "Could not load teams.");
        }
      } finally {
        if (!cancelled) {
          setTeamsLoading(false);
        }
      }
    };

    void loadTeams();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedTeamId) {
      return;
    }

    let cancelled = false;
    const loadAgents = async () => {
      setAgentsLoading(true);
      setTeamMessage("");
      try {
        const rows = await listTeamAgents(selectedTeamId);
        if (cancelled) {
          return;
        }
        setAgents(rows);
        if (rows.length === 0) {
          setTeamMessage("Selected team has no agents. Add an agent before running chat.");
        }
      } catch (error) {
        if (!cancelled) {
          setTeamMessage(error instanceof Error ? error.message : "Could not load team agents.");
        }
      } finally {
        if (!cancelled) {
          setAgentsLoading(false);
        }
      }
    };

    void loadAgents();
    return () => {
      cancelled = true;
    };
  }, [selectedTeamId]);

  const handleTeamSelection = (teamId: string) => {
    setSelectedTeamId(teamId);
    setQueryState({ status: "idle" });
    setAgents([]);
    setTeamMessage("");
  };

  const handleSubmit = async (payload: { sessionId: string; query: string; topK: number }) => {
    if (!selectedTeamId || agents.length === 0) {
      return;
    }
    setQueryState({ status: "loading" });
    await logUiEvent({
      event_name: "query_submit",
      page: "/chat",
      component: "QueryInput",
      action: "submit",
      payload,
    }).catch(() => undefined);
    try {
      const result = await runQuery({
        query: payload.query,
        session_id: payload.sessionId,
        team_id: selectedTeamId,
        top_k: payload.topK,
      });
      await logUiEvent({
        event_name: "query_success",
        page: "/chat",
        component: "ChatPage",
        action: "query_complete",
        payload: { request: payload, response: result },
      }).catch(() => undefined);
      setQueryState({ status: "success", data: result });
    } catch (error) {
      await logUiEvent({
        event_name: "query_failure",
        page: "/chat",
        component: "ChatPage",
        action: "query_error",
        payload: { request: payload, error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
      setQueryState({
        status: "error",
        message: error instanceof Error ? error.message : "Query failed unexpectedly",
      });
    }
  };

  const handleCreateSession = async () => {
    if (!selectedTeamId) {
      throw new Error("Select a team before creating a session.");
    }
    const row = await createSession({ title: "Chat session", team_id: selectedTeamId });
    await logUiEvent({
      event_name: "session_create_success",
      page: "/chat",
      component: "QueryInput",
      action: "create_session",
      payload: row,
    }).catch(() => undefined);
    return row.id;
  };

  const response: QueryResponse | null = queryState.status === "success" ? queryState.data : null;
  const inputDisabledReason = !selectedTeamId
    ? "Select a team before running chat."
    : agentsLoading
      ? "Loading team agents..."
      : agents.length === 0
        ? "Selected team has no agents. Add an agent before running chat."
        : undefined;
  const inputDisabled = queryState.status === "loading" || teamsLoading || agentsLoading || !selectedTeamId || agents.length === 0;

  return (
    <ProtectedPage>
      <AppShell
        title="Chat Workspace"
        subtitle="Run document-grounded retrieval and inspect the supporting sources"
      >
        <div className="chat-layout">
          <div className="stack">
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Run Query</h3>
              <div className="form-field chat-team-selector">
                <label htmlFor="chat-team-id">Team</label>
                <select
                  id="chat-team-id"
                  value={selectedTeamId}
                  onChange={(event) => handleTeamSelection(event.target.value)}
                  disabled={teamsLoading}
                >
                  <option value="">{teamsLoading ? "Loading teams..." : "Select a team"}</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>
                {selectedTeam ? (
                  <p className="status-message">
                    {selectedTeam.domain || "No domain"} | {selectedTeam.collaboration_rule} | {agents.length} agent{agents.length === 1 ? "" : "s"}
                  </p>
                ) : null}
                {teamMessage ? <p className="status-message">{teamMessage}</p> : null}
              </div>
              <QueryInput
                key={selectedTeamId || "no-team"}
                onSubmit={handleSubmit}
                onCreateSession={handleCreateSession}
                disabled={inputDisabled}
                disabledReason={inputDisabledReason}
              />
            </div>
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Answer</h3>
              <ChatWindow queryState={queryState} />
            </div>
          </div>

          <div className="stack">
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Sources</h3>
              <SourceList sources={response?.sources ?? []} />
            </div>
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Agent Trace</h3>
              <div className="chat-trace-scroll">
                <TracePanel
                  traces={response?.traces ?? []}
                  sources={response?.sources ?? []}
                  retrievalCount={response?.retrieval_count}
                  insufficientContext={response?.insufficient_context}
                  fullOutput
                />
              </div>
            </div>
          </div>
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
