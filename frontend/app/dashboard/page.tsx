"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { MetricsCards } from "../../components/dashboard/MetricsCards";
import { QueriesChart } from "../../components/dashboard/QueriesChart";
import { AppShell } from "../../components/layout/AppShell";
import { getDashboardMetrics, listSessions, logUiEvent } from "../../lib/api";
import { selectMostRecentRunnableSession } from "../../lib/session-selection";
import { DashboardMetrics } from "../../lib/types";

/** Dashboard page for session telemetry and trend exploration. */
export default function DashboardPage() {
  const [sessionId, setSessionId] = useState("");
  const [days, setDays] = useState(7);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [message, setMessage] = useState("Loading latest session metrics...");

  const loadMetricsForSession = async (
    targetSessionId: string,
    windowDays: number,
    action: "auto_load_latest_session" | "load_metrics",
    isCancelled: () => boolean = () => false,
  ) => {
    if (!targetSessionId.trim()) {
      setMessage("Please provide a session ID.");
      return;
    }
    try {
      const payload = await getDashboardMetrics(targetSessionId.trim(), windowDays);
      if (isCancelled()) {
        return;
      }
      await logUiEvent({
        event_name: "dashboard_metrics_success",
        page: "/dashboard",
        component: "DashboardPage",
        action,
        payload: { session_id: targetSessionId.trim(), days: windowDays, metrics: payload },
      }).catch(() => undefined);
      setMetrics(payload);
      setMessage("");
    } catch (error) {
      if (isCancelled()) {
        return;
      }
      await logUiEvent({
        event_name: "dashboard_metrics_failure",
        page: "/dashboard",
        component: "DashboardPage",
        action,
        payload: { session_id: targetSessionId.trim(), days: windowDays, error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
      setMetrics(null);
      setMessage(error instanceof Error ? error.message : "Could not load dashboard metrics.");
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadLatestSession = async () => {
      await logUiEvent({ event_name: "page_view", page: "/dashboard", component: "DashboardPage", action: "load" }).catch(() => undefined);

      try {
        const sessions = await listSessions();
        if (cancelled) {
          return;
        }

        const latestSession = selectMostRecentRunnableSession(sessions);
        if (!latestSession) {
          setMessage("No sessions found. Run a chat query first or enter a session ID.");
          return;
        }

        setSessionId(latestSession.id);
        await loadMetricsForSession(latestSession.id, days, "auto_load_latest_session", () => cancelled);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setMetrics(null);
        setMessage(error instanceof Error ? error.message : "Could not load latest session.");
      }
    };

    void loadLatestSession();
    return () => {
      cancelled = true;
    };
    // Run once on mount so manual time-window edits do not unexpectedly reload metrics.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await loadMetricsForSession(sessionId, days, "load_metrics");
  };

  return (
    <ProtectedPage>
      <AppShell
        title="Platform Telemetry"
        subtitle="Track query volume and retrieval latency"
        actions={
          <button type="button" onClick={() => setMetrics(null)} disabled={!metrics}>
            Clear View
          </button>
        }
      >
        <div className="hero-card">
          <form className="split-3" onSubmit={handleLoad}>
            <label>
              Session ID{" "}
              <input
                id="dashboard-session-id"
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                placeholder="Session UUID"
              />
            </label>
            <label>
              Time Window (days){" "}
              <input
                id="dashboard-days"
                type="number"
                min={1}
                max={30}
                value={days}
                onChange={(event) => setDays(Number(event.target.value) || 7)}
              />
            </label>
            <div style={{ display: "grid", alignItems: "end" }}>
              <button type="submit">Load Metrics</button>
            </div>
          </form>
          {message ? <p className="status-message" style={{ marginTop: 12 }}>{message}</p> : null}
        </div>

        <div className="split-2">
          <div className="card">
            <div className="panel-title">
              <h3>Metrics</h3>
              <span>{metrics ? `${days} day window` : "No session loaded"}</span>
            </div>
            <MetricsCards metrics={metrics} />
          </div>

          <div className="card">
            <div className="panel-title">
              <h3>Quick Actions</h3>
              <span>Workspace</span>
            </div>
            <div className="action-list">
              <Link className="action-link" href="/teams/new">
                <span>Create a team</span>
                <span className="material-symbols-outlined">arrow_forward</span>
              </Link>
              <Link className="action-link" href="/knowledge">
                <span>Upload knowledge</span>
                <span className="material-symbols-outlined">arrow_forward</span>
              </Link>
              <Link className="action-link" href="/chat">
                <span>Run chat</span>
                <span className="material-symbols-outlined">arrow_forward</span>
              </Link>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="panel-title">
            <h3>Queries Over Time</h3>
            <span>Session trend</span>
          </div>
          <QueriesChart metrics={metrics} />
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
