import { AgentTraceRow } from "../../lib/types";

type AgentTraceProps = {
  traces: AgentTraceRow[];
};

export function AgentTrace({ traces }: AgentTraceProps) {
  if (traces.length === 0) {
    return <p className="status-message">No trace rows captured.</p>;
  }

  return (
    <ol className="trace-list">
      {traces.map((trace, index) => (
        <li key={`${trace.agent_name}-${index}`} className="trace-item">
          <p>
            <strong>{trace.agent_name}</strong> ({trace.model_name}) - {trace.response_time_ms} ms
          </p>
          <p>{trace.output}</p>
        </li>
      ))}
    </ol>
  );
}
