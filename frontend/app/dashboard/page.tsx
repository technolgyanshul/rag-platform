"use client";

import { FormEvent, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { MetricsCards } from "../../components/dashboard/MetricsCards";
import { QueriesChart } from "../../components/dashboard/QueriesChart";
import { getDashboardMetrics } from "../../lib/api";
import { DashboardMetrics } from "../../lib/types";

export default function DashboardPage() {
  const [sessionId, setSessionId] = useState("");
  const [days, setDays] = useState(7);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [message, setMessage] = useState("Enter a session ID to view dashboard metrics.");

  const handleLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionId.trim()) {
      setMessage("Please provide a session ID.");
      return;
    }
    try {
      const payload = await getDashboardMetrics(sessionId.trim(), days);
      setMetrics(payload);
      setMessage("");
    } catch (error) {
      setMetrics(null);
      setMessage(error instanceof Error ? error.message : "Could not load dashboard metrics.");
    }
  };

  return (
    <ProtectedPage>
      <main className="container page-stack">
        <h1>Dashboard</h1>
        <div className="card auth-card">
          <form className="auth-form" onSubmit={handleLoad}>
            <label htmlFor="dashboard-session-id">Session ID</label>
            <input
              id="dashboard-session-id"
              value={sessionId}
              onChange={(event) => setSessionId(event.target.value)}
              placeholder="Session UUID"
            />
            <label htmlFor="dashboard-days">Days</label>
            <input
              id="dashboard-days"
              type="number"
              min={1}
              max={30}
              value={days}
              onChange={(event) => setDays(Number(event.target.value) || 7)}
            />
            <button type="submit">Load Metrics</button>
          </form>
          {message && <p className="status-message">{message}</p>}
        </div>
        <div className="card">
          <h2>Summary</h2>
          <MetricsCards metrics={metrics} />
        </div>
        <div className="card">
          <h2>Queries Over Time</h2>
          <QueriesChart metrics={metrics} />
        </div>
      </main>
    </ProtectedPage>
  );
}
