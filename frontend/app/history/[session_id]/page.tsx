"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "../../../components/auth/ProtectedPage";
import { ScoreCard } from "../../../components/chat/ScoreCard";
import { TracePanel } from "../../../components/chat/TracePanel";
import { AppShell } from "../../../components/layout/AppShell";
import { downloadSessionExport, getSessionDetail, logUiEvent } from "../../../lib/api";
import { SessionDetail } from "../../../lib/types";

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

/** Session detail page showing full query timeline, traces, and export action. */
export default function SessionDetailPage() {
  const params = useParams<{ session_id: string }>();
  const sessionId = useMemo(() => params?.session_id ?? "", [params]);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [message, setMessage] = useState("Loading session detail...");
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!sessionId) {
      setMessage("Session ID is missing.");
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const payload = await getSessionDetail(sessionId);
      setDetail(payload);
      setMessage(payload.queries.length ? "" : "Session has no queries yet.");
      await logUiEvent({
        event_name: "history_session_detail_success",
        page: `/history/${sessionId}`,
        component: "SessionDetailPage",
        action: "load_detail",
        payload: { session_id: sessionId, query_count: payload.queries.length },
      }).catch(() => undefined);
    } catch (error) {
      setDetail(null);
      setMessage(error instanceof Error ? error.message : "Could not load session detail.");
      await logUiEvent({
        event_name: "history_session_detail_failure",
        page: `/history/${sessionId}`,
        component: "SessionDetailPage",
        action: "load_detail",
        payload: { session_id: sessionId, error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleExport = async () => {
    if (!sessionId) {
      return;
    }
    setExporting(true);
    try {
      const payload = await downloadSessionExport(sessionId);
      const blob = new Blob([formatJson(payload.data)], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = payload.filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);

      await logUiEvent({
        event_name: "history_session_export_success",
        page: `/history/${sessionId}`,
        component: "SessionDetailPage",
        action: "download_export",
        payload: { session_id: sessionId, filename: payload.filename },
      }).catch(() => undefined);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not export session.");
      await logUiEvent({
        event_name: "history_session_export_failure",
        page: `/history/${sessionId}`,
        component: "SessionDetailPage",
        action: "download_export",
        payload: { session_id: sessionId, error: error instanceof Error ? error.message : String(error) },
      }).catch(() => undefined);
    } finally {
      setExporting(false);
    }
  };

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    void logUiEvent({
      event_name: "page_view",
      page: `/history/${sessionId}`,
      component: "SessionDetailPage",
      action: "load",
      payload: { session_id: sessionId },
    }).catch(() => undefined);
    void loadDetail();
  }, [loadDetail, sessionId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  return (
    <ProtectedPage>
      <AppShell
        title="Session Detail"
        subtitle="Inspect query, final answer, scorecard, citations, and full agent trace"
        actions={(
          <>
            <button type="button" onClick={handleExport} disabled={exporting || !sessionId}>
              {exporting ? "Exporting..." : "Export JSON"}
            </button>
            <button type="button" onClick={() => void loadDetail()} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </>
        )}
      >
        <div className="card">
          <Link href="/history" className="history-link">Back To Sessions</Link>
          {detail ? (
            <p className="status-message" style={{ marginTop: 12 }}>
              Team: {detail.session.team_name || "Unknown"} | Created: {new Date(detail.session.created_at).toLocaleString()}
            </p>
          ) : null}
        </div>

        {!detail ? (
          <div className="card">
            <p className="status-message">{loading ? "Loading session detail..." : message}</p>
          </div>
        ) : (
          <>
            {detail.queries.length === 0 ? (
              <div className="card">
                <p className="status-message">{message || "Session has no queries yet."}</p>
              </div>
            ) : (
              <ul className="history-list">
                {detail.queries.map((query) => {
                  const citations = Array.isArray(query.citations) ? query.citations : [];
                  const traces = Array.isArray(query.agent_traces) ? query.agent_traces : [];
                  const sources = Array.isArray(query.sources) ? query.sources : [];
                  return (
                    <li key={query.id} className="history-item">
                    <div className="stack">
                      <div>
                        <h3 style={{ marginBottom: 8 }}>Query</h3>
                        <p>{query.query_text}</p>
                      </div>
                      <div>
                        <h3 style={{ marginBottom: 8 }}>Final Answer</h3>
                        <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{query.final_answer}</p>
                      </div>
                      <p className="status-message">
                        Date: {new Date(query.created_at).toLocaleString()} | Score: {query.overall_score ?? "N/A"} | Latency:{" "}
                        {query.response_time_ms == null ? "N/A" : `${query.response_time_ms} ms`}
                      </p>
                      <div>
                        <h4 style={{ marginBottom: 8 }}>Scorecard</h4>
                        {query.scorecard ? (
                          <ScoreCard scorecard={query.scorecard} />
                        ) : (
                          <p className="status-message">No scorecard available.</p>
                        )}
                      </div>
                      <div>
                        <h4 style={{ marginBottom: 8 }}>Citations</h4>
                        {citations.length > 0 ? (
                          <pre className="history-pre">{formatJson(citations)}</pre>
                        ) : (
                          <p className="status-message">No citations.</p>
                        )}
                      </div>
                      <div>
                        <h4 style={{ marginBottom: 8 }}>Agent Trace</h4>
                        <TracePanel traces={traces} sources={sources} fullOutput />
                      </div>
                    </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}
      </AppShell>
    </ProtectedPage>
  );
}
