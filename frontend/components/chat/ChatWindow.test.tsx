import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ChatWindow } from "./ChatWindow";
import { QueryResponse } from "../../lib/types";

const response: QueryResponse = {
  query_id: "query-1",
  query: "What changed?",
  final_answer: "The final answer cites the new evidence.",
  reasoning: null,
  sources: [],
  citations: [],
  traces: [],
  scorecard: {
    overall_quality: 8,
    citation_accuracy: 9,
    insight_depth: 7,
    notes: "Grounded final response.",
    model_contribution_breakdown: {
      Researcher: "completed",
      Synthesizer: "completed",
    },
  },
  retrieval_count: 0,
  insufficient_context: false,
  model_version: "test-model",
  retrieval_metadata: {
    embedding_model_version: "test-embedding",
    index_version: "test-index",
    top_k: 5,
  },
};

describe("ChatWindow", () => {
  it("renders scorecard below a successful final answer", () => {
    const html = renderToStaticMarkup(<ChatWindow queryState={{ status: "success", data: response }} />);
    const finalAnswerIndex = html.indexOf("The final answer cites the new evidence.");
    const scorecardIndex = html.indexOf("Research Scorecard");

    expect(finalAnswerIndex).toBeGreaterThanOrEqual(0);
    expect(scorecardIndex).toBeGreaterThan(finalAnswerIndex);
    expect(html).toContain("Citation Accuracy");
    expect(html).toContain("9/10");
    expect(html).toContain("Grounded final response.");
  });

  it("renders reasoning below the final answer", () => {
    const html = renderToStaticMarkup(
      <ChatWindow
        queryState={{
          status: "success",
          data: {
            ...response,
            reasoning: "Reasoning details.",
          },
        }}
      />,
    );

    const finalHeadingIndex = html.indexOf("Final Answer");
    const reasoningHeadingIndex = html.indexOf("Reasoning");

    expect(finalHeadingIndex).toBeGreaterThanOrEqual(0);
    expect(reasoningHeadingIndex).toBeGreaterThan(finalHeadingIndex);
  });
});
