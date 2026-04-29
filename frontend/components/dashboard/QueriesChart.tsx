import { DashboardMetrics } from "../../lib/types";

type QueriesChartProps = {
  metrics: DashboardMetrics | null;
};

export function QueriesChart({ metrics }: QueriesChartProps) {
  if (!metrics || metrics.queries_over_time.length === 0) {
    return <p className="status-message">No chart data available yet.</p>;
  }

  const maxCount = Math.max(...metrics.queries_over_time.map((item) => item.count), 1);

  return (
    <div className="chart-grid">
      {metrics.queries_over_time.map((item) => (
        <div key={item.date} className="chart-row">
          <span>{item.date}</span>
          <div className="chart-bar-wrap">
            <div className="chart-bar" style={{ width: `${(item.count / maxCount) * 100}%` }} />
          </div>
          <span>{item.count}</span>
        </div>
      ))}
    </div>
  );
}
