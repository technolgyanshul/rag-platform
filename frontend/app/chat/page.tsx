"use client";

import { useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AgentTrace } from "../../components/chat/AgentTrace";
import { ChatWindow } from "../../components/chat/ChatWindow";
import { QueryInput } from "../../components/chat/QueryInput";
import { ScoreCard } from "../../components/chat/ScoreCard";
import { SourceList } from "../../components/chat/SourceList";
import { AppShell } from "../../components/layout/AppShell";
import { createSession, runQuery } from "../../lib/api";
import { QueryResponse, QueryUiState } from "../../lib/types";

export default function ChatPage() {
  const [queryState, setQueryState] = useState<QueryUiState>({ status: "idle" });

  const handleSubmit = async (payload: { sessionId: string; query: string; topK: number }) => {
    setQueryState({ status: "loading" });
    try {
      const result = await runQuery({
        query: payload.query,
        session_id: payload.sessionId,
        top_k: payload.topK,
      });
      setQueryState({ status: "success", data: result });
    } catch (error) {
      setQueryState({
        status: "error",
        message: error instanceof Error ? error.message : "Query failed unexpectedly",
      });
    }
  };

  const handleCreateSession = async () => {
    const row = await createSession("Chat session");
    return row.id;
  };

  const response: QueryResponse | null = queryState.status === "success" ? queryState.data : null;

  return (
    <ProtectedPage>
      <AppShell
        title="Chat Workspace"
        subtitle="Run multi-agent retrieval flows and inspect the execution details"
      >
        <div className="chat-layout">
          <div className="stack">
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Run Query</h3>
              <QueryInput
                onSubmit={handleSubmit}
                onCreateSession={handleCreateSession}
                disabled={queryState.status === "loading"}
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
              <AgentTrace traces={response?.agent_trace ?? []} />
            </div>
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Scorecard</h3>
              <ScoreCard scorecard={response?.scorecard ?? null} />
            </div>
          </div>
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
