import { AgentTrace, Source } from "../../lib/types";

type TracePanelProps = Readonly<{
  traces: readonly AgentTrace[];
  sources: readonly Source[];
}>;

function outputPreview(output: string): string {
  const trimmed = output.trim();
  if (!trimmed) {
    return "No output captured.";
  }
  return trimmed.length > 240 ? `${trimmed.slice(0, 240)}...` : trimmed;
}

function citationSourceIndex(citation: Record<string, unknown>): number | null {
  const raw = citation.source_index ?? citation.sourceIndex ?? citation.source;
  if (typeof raw === "number" && Number.isFinite(raw)) {
    return raw;
  }
  if (typeof raw === "string") {
    const parsed = Number.parseInt(raw, 10);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function citationLabel(citation: Record<string, unknown>, sources: readonly Source[]): string {
  const sourceIndex = citationSourceIndex(citation);
  const source = sourceIndex ? sources[sourceIndex - 1] : null;
  if (sourceIndex && source) {
    return `Source ${sourceIndex}: ${source.filename}#${source.chunk_index}`;
  }

  const filename = typeof citation.filename === "string" ? citation.filename : null;
  const chunkIndex = typeof citation.chunk_index === "number" ? citation.chunk_index : null;
  if (sourceIndex) {
    return `Source ${sourceIndex}`;
  }
  if (filename && chunkIndex !== null) {
    return `${filename}#${chunkIndex}`;
  }
  if (filename) {
    return filename;
  }
  return "Citation";
}

export function TracePanel({ traces, sources }: TracePanelProps) {
  if (traces.length === 0) {
    return <p className="status-message">No agent traces returned for this answer.</p>;
  }

  return (
    <ul className="trace-list">
      {traces.map((trace, index) => (
        <li key={trace.id ?? `${trace.agent_name}-${index}`} className="trace-item">
          <div className="trace-item__header">
            <div>
              <h4>{trace.agent_name || "Agent"}</h4>
              <p className="status-message">{trace.agent_role || "role unavailable"}</p>
            </div>
            <span className="trace-item__status">{trace.status || "unknown"}</span>
          </div>
          <dl className="trace-item__meta">
            <div>
              <dt>Provider</dt>
              <dd>{trace.model_provider || "unknown"}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>{trace.model_name || "unknown"}</dd>
            </div>
            <div>
              <dt>Latency</dt>
              <dd>{trace.latency_ms === null ? "not recorded" : `${trace.latency_ms} ms`}</dd>
            </div>
          </dl>
          <p className="trace-item__output">{outputPreview(trace.error ?? trace.output)}</p>
          {trace.citations.length > 0 ? (
            <div className="trace-item__citations">
              {trace.citations.map((citation, citationIndex) => (
                <span key={`${trace.id ?? index}-citation-${citationIndex}`}>{citationLabel(citation, sources)}</span>
              ))}
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
