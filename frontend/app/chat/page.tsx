"use client";

import { useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AgentTrace } from "../../components/chat/AgentTrace";
import { ChatWindow } from "../../components/chat/ChatWindow";
import { QueryInput } from "../../components/chat/QueryInput";
import { ScoreCard } from "../../components/chat/ScoreCard";
import { SourceList } from "../../components/chat/SourceList";
import { runQuery } from "../../lib/api";
import { QueryResponse } from "../../lib/types";

export default function ChatPage() {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (payload: { teamId: string; sessionId: string; query: string; topK: number }) => {
    setStatus("loading");
    setErrorMessage("");
    try {
      const result = await runQuery({
        query: payload.query,
        team_id: payload.teamId,
        session_id: payload.sessionId,
        top_k: payload.topK,
      });
      setResponse(result);
      setStatus("success");
    } catch (error) {
      setResponse(null);
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "Query failed unexpectedly");
    }
  };

  return (
    <ProtectedPage>
      <main className="container page-stack">
        <h1>Research Chat</h1>
        <div className="card">
          <h2>Run Query</h2>
          <QueryInput onSubmit={handleSubmit} disabled={status === "loading"} />
        </div>
        <div className="card">
          <h2>Answer</h2>
          <ChatWindow status={status} response={response} errorMessage={errorMessage} />
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
