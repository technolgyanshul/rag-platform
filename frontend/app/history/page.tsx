"use client";

import { FormEvent, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
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
      <main className="container page-stack">
        <h1>Query History</h1>
        <div className="card auth-card">
          <form className="auth-form" onSubmit={handleLoad}>
            <label htmlFor="history-session-id">Session ID</label>
            <input
              id="history-session-id"
              value={sessionId}
              onChange={(event) => setSessionId(event.target.value)}
              placeholder="Session UUID"
            />
            <button type="submit">Load History</button>
          </form>
        </div>
        <div className="card">
          <h2>Past Queries</h2>
          {!rows.length ? (
            <p className="status-message">{message}</p>
          ) : (
            <ul className="history-list">
              {rows.map((row) => (
                <li key={row.id} className="history-item">
                  <p>
                    <strong>{row.query_text}</strong>
                  </p>
                  <p>{row.final_answer}</p>
                  <p className="status-message">
                    Score: {row.overall_score ?? "N/A"} | Response: {row.response_time_ms ?? "N/A"} ms | {row.created_at}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </ProtectedPage>
  );
}
