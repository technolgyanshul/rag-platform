"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";
import { listSessions, logUiEvent } from "../../lib/api";
import { SessionListItem } from "../../lib/types";

/** Session history list with quick navigation into detail views. */
export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [message, setMessage] = useState("Loading sessions...");
  const [loading, setLoading] = useState(true);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const result = await listSessions();
      await logUiEvent({
        event_name: "history_sessions_success",
        page: "/history",
        component: "HistoryPage",
        action: "load_sessions",
        payload: { session_count: result.length },
      }).catch(() => undefined);
      setSessions(result);
      setMessage(result.length ? "" : "No sessions found yet.");
    } catch (error) {
      await logUiEvent({
        event_name: "history_sessions_failure",
        page: "/history",
        component: "HistoryPage",
        action: "load_sessions",
        payload: { error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
      setSessions([]);
      setMessage(error instanceof Error ? error.message : "Could not load sessions.");
    } finally {
      setLoading(false);
    }
  };

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/history", component: "HistoryPage", action: "load" }).catch(() => undefined);
    void loadSessions();
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  return (
    <ProtectedPage>
      <AppShell title="Session History" subtitle="Open any previous session and inspect full outputs and traces">
        <div className="hero-card">
          <div className="page-header__actions">
            <button type="button" onClick={() => void loadSessions()} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="panel-title">
            <h3>Your Sessions</h3>
            <span>{sessions.length} listed</span>
          </div>
          {sessions.length === 0 ? (
            <p className="status-message">{message}</p>
          ) : (
            <ul className="history-list">
              {sessions.map((session) => (
                <li key={session.id} className="history-item">
                  <div style={{ display: "grid", gap: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                      <strong>{session.title || "Chat session"}</strong>
                      <span className="status-message">
                        {session.query_count} quer{session.query_count === 1 ? "y" : "ies"}
                      </span>
                    </div>
                    <p className="status-message">
                      Team: {session.team_name || "Unknown"} | Created: {new Date(session.created_at).toLocaleString()}
                    </p>
                    <p className="status-message">
                      Last Query: {session.last_query_at ? new Date(session.last_query_at).toLocaleString() : "No queries yet"}
                    </p>
                    <div>
                      <Link href={`/history/${session.id}`} className="history-link">
                        Open Session
                      </Link>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {!sessions.length && message ? (
            <div style={{ marginTop: 12 }}>
              <button type="button" onClick={() => void loadSessions()} disabled={loading}>
                Try Again
              </button>
            </div>
          ) : null}
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
