import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { TracePanel } from "./TracePanel";
import { AgentTrace, Source } from "../../lib/types";

const sources: Source[] = [
  {
    document_id: "doc-1",
    filename: "policy.pdf",
    chunk_index: 3,
    content_preview: "Policy source text",
    score: 0.92,
  },
];

const traces: AgentTrace[] = [
  {
    id: "trace-1",
    agent_id: "agent-1",
    agent_name: "Researcher",
    agent_role: "researcher",
    model_provider: "groq",
    model_name: "llama-3.1",
    status: "completed",
    latency_ms: 1234,
    output: "The policy requires a documented review before launch.",
    error: null,
    citations: [{ source_index: 1, document_id: "doc-1", chunk_index: 3 }],
  },
];

describe("TracePanel", () => {
  it("renders trace metadata, output preview, and mapped citation labels", () => {
    const html = renderToStaticMarkup(<TracePanel traces={traces} sources={sources} />);

    expect(html).toContain("Researcher");
    expect(html).toContain("researcher");
    expect(html).toContain("groq");
    expect(html).toContain("llama-3.1");
    expect(html).toContain("completed");
    expect(html).toContain("1234 ms");
    expect(html).toContain("The policy requires a documented review before launch.");
    expect(html).toContain("Source 1");
    expect(html).toContain("policy.pdf#3");
  });
});
