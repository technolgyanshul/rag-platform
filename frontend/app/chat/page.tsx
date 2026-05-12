"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { ChatWindow } from "../../components/chat/ChatWindow";
import { QueryInput } from "../../components/chat/QueryInput";
import { SourceList } from "../../components/chat/SourceList";
import { AppShell } from "../../components/layout/AppShell";
import { createSession, logUiEvent, runQuery } from "../../lib/api";
import { QueryResponse, QueryUiState } from "../../lib/types";

export default function ChatPage() {
  const [queryState, setQueryState] = useState<QueryUiState>({ status: "idle" });

  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/chat", component: "ChatPage", action: "load" }).catch(() => undefined);
  }, []);

  const handleSubmit = async (payload: { sessionId: string; query: string; topK: number }) => {
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
    const row = await createSession("Chat session");
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
          </div>
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
