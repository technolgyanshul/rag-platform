"use client";

import { FormEvent, useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { MetricsCards } from "../../components/dashboard/MetricsCards";
import { QueriesChart } from "../../components/dashboard/QueriesChart";
import { AppShell } from "../../components/layout/AppShell";
import { getDashboardMetrics, logUiEvent } from "../../lib/api";
import { DashboardMetrics } from "../../lib/types";

export default function DashboardPage() {
  const [sessionId, setSessionId] = useState("");
  const [days, setDays] = useState(7);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [message, setMessage] = useState("Enter a session ID to view dashboard metrics.");

  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/dashboard", component: "DashboardPage", action: "load" }).catch(() => undefined);
  }, []);

  const handleLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionId.trim()) {
      setMessage("Please provide a session ID.");
      return;
    }
    try {
      const payload = await getDashboardMetrics(sessionId.trim(), days);
      await logUiEvent({
        event_name: "dashboard_metrics_success",
        page: "/dashboard",
        component: "DashboardPage",
        action: "load_metrics",
        payload: { session_id: sessionId.trim(), days, metrics: payload },
      }).catch(() => undefined);
      setMetrics(payload);
      setMessage("");
    } catch (error) {
      await logUiEvent({
        event_name: "dashboard_metrics_failure",
        page: "/dashboard",
        component: "DashboardPage",
        action: "load_metrics",
        payload: { session_id: sessionId.trim(), days, error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
      setMetrics(null);
      setMessage(error instanceof Error ? error.message : "Could not load dashboard metrics.");
    }
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
        <div className="card">
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

        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Metrics</h3>
          <MetricsCards metrics={metrics} />
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Queries Over Time</h3>
          <QueriesChart metrics={metrics} />
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
