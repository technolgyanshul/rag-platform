import { DashboardMetrics } from "../../lib/types";

type MetricsCardsProps = {
  metrics: DashboardMetrics | null;
};

export function MetricsCards({ metrics }: MetricsCardsProps) {
  if (!metrics) {
    return <p className="status-message">Load a session to view metrics.</p>;
  }

  return (
    <div className="metrics-grid">
      <article className="metric-card">
        <h3>Total Queries</h3>
        <p>{metrics.total_queries}</p>
      </article>
      <article className="metric-card">
        <h3>Avg Response Time</h3>
        <p>{metrics.average_response_time_ms} ms</p>
      </article>
      <article className="metric-card">
        <h3>Avg Overall Score</h3>
        <p>{metrics.average_overall_score.toFixed(2)}</p>
      </article>
    </div>
  );
}
