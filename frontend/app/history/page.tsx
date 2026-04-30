"use client";

import { FormEvent, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";
import { listQueryHistory } from "../../lib/api";
import { QueryHistoryItem } from "../../lib/types";

export default function HistoryPage() {
  const [sessionId, setSessionId] = useState("");
  const [rows, setRows] = useState<QueryHistoryItem[]>([]);
  const [message, setMessage] = useState("Enter a session ID to load history.");

  const handleLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionId.trim()) {
      setMessage("Please provide a session ID.");
      return;
    }
    try {
      const result = await listQueryHistory(sessionId.trim());
      setRows(result);
      setMessage(result.length ? "" : "No history found for this session.");
    } catch (error) {
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
                placeholder="Session UUID"
              />
            </label>
            <div style={{ display: "grid", alignItems: "end" }}>
              <button type="submit">Load History</button>
            </div>
          </form>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Past Queries</h3>
          {!rows.length ? (
            <p className="status-message">{message}</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
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
                      <td>{row.query_text}</td>
                      <td>{row.final_answer.slice(0, 140)}...</td>
                      <td>{row.overall_score ?? "N/A"}</td>
                      <td>{row.response_time_ms ? `${row.response_time_ms} ms` : "N/A"}</td>
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
