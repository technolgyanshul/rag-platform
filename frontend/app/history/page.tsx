"use client";

import { FormEvent, useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";
import { listQueryHistory, listRecentQueryHistory, logUiEvent } from "../../lib/api";
import { QueryHistoryItem } from "../../lib/types";

export default function HistoryPage() {
  const [sessionId, setSessionId] = useState("");
  const [rows, setRows] = useState<QueryHistoryItem[]>([]);
  const [message, setMessage] = useState("Loading recent query history...");
  const [mode, setMode] = useState<"recent" | "session">("recent");

  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/history", component: "HistoryPage", action: "load" }).catch(() => undefined);
    void loadRecentHistory();
  }, []);

  const loadRecentHistory = async () => {
    try {
      const result = await listRecentQueryHistory();
      await logUiEvent({
        event_name: "query_history_recent_success",
        page: "/history",
        component: "HistoryPage",
        action: "load_recent_history",
        payload: { row_count: result.length, rows: result },
      }).catch(() => undefined);
      setRows(result);
      setMode("recent");
      setMessage(result.length ? "" : "No recent queries found.");
    } catch (error) {
      await logUiEvent({
        event_name: "query_history_recent_failure",
        page: "/history",
        component: "HistoryPage",
        action: "load_recent_history",
        payload: { error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
      setRows([]);
      setMessage(error instanceof Error ? error.message : "Could not load recent history.");
    }
  };

  const handleLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionId.trim()) {
      void loadRecentHistory();
      return;
    }
    try {
      const result = await listQueryHistory(sessionId.trim());
      await logUiEvent({
        event_name: "query_history_success",
        page: "/history",
        component: "HistoryPage",
        action: "load_history",
        payload: { session_id: sessionId.trim(), row_count: result.length, rows: result },
      }).catch(() => undefined);
      setRows(result);
      setMode("session");
      setMessage(result.length ? "" : "No history found for this session.");
    } catch (error) {
      await logUiEvent({
        event_name: "query_history_failure",
        page: "/history",
        component: "HistoryPage",
        action: "load_history",
        payload: { session_id: sessionId.trim(), error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
      setRows([]);
      setMessage(error instanceof Error ? error.message : "Could not load history.");
    }
  };

  return (
    <ProtectedPage>
      <AppShell title="Query Logs" subtitle="Audit previous prompts, answers, scores, and latency">
        <div className="card">
          <form className="split-2" onSubmit={handleLoad}>
            <label htmlFor="history-session-id">
              Session ID
              <input
                id="history-session-id"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                placeholder="Session UUID (optional)"
              />
            </label>
            <div style={{ display: "grid", alignItems: "end" }}>
              <button type="submit">{sessionId.trim() ? "Load Session History" : "Load Recent History"}</button>
            </div>
          </form>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 12 }}>
            {mode === "recent" ? "Past Queries (Recent Across Sessions)" : "Past Queries (Session Filtered)"}
          </h3>
          {!rows.length ? (
            <p className="status-message">{message}</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Session ID</th>
                    <th>Query</th>
                    <th>Answer Preview</th>
                    <th>Score</th>
                    <th>Latency</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row: QueryHistoryItem) => (
                    <tr key={row.id}>
                      <td>{row.session_id}</td>
                      <td>{row.query_text}</td>
                      <td>{row.final_answer.slice(0, 140)}...</td>
                      <td>{row.overall_score ?? "N/A"}</td>
                      <td>{row.response_time_ms != null ? `${row.response_time_ms} ms` : "N/A"}</td>
                      <td>{new Date(row.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
