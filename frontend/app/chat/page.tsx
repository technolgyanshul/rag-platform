"use client";

import { useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AgentTrace } from "../../components/chat/AgentTrace";
import { ChatWindow } from "../../components/chat/ChatWindow";
import { QueryInput } from "../../components/chat/QueryInput";
import { ScoreCard } from "../../components/chat/ScoreCard";
import { SourceList } from "../../components/chat/SourceList";
import { runQuery } from "../../lib/api";
import { QueryResponse, QueryUiState } from "../../lib/types";

export default function ChatPage() {
  const [queryState, setQueryState] = useState<QueryUiState>({ status: "idle" });

  const handleSubmit = async (payload: { teamId: string; sessionId: string; query: string; topK: number }) => {
    setQueryState({ status: "loading" });
    try {
      const result = await runQuery({
        query: payload.query,
        team_id: payload.teamId,
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

  const response: QueryResponse | null = queryState.status === "success" ? queryState.data : null;

  return (
    <ProtectedPage>
      <main className="container page-stack">
        <h1>Research Chat</h1>
        <div className="card">
          <h2>Run Query</h2>
          <QueryInput onSubmit={handleSubmit} disabled={queryState.status === "loading"} />
        </div>
        <div className="card">
          <h2>Answer</h2>
          <ChatWindow queryState={queryState} />
        </div>
        <div className="card">
          <h2>Sources</h2>
          <SourceList sources={response?.sources ?? []} />
        </div>
        <div className="card">
          <h2>Agent Trace</h2>
          <AgentTrace traces={response?.agent_trace ?? []} />
        </div>
        <div className="card">
          <h2>Scorecard</h2>
          <ScoreCard scorecard={response?.scorecard ?? null} />
        </div>
      </main>
    </ProtectedPage>
  );
}
