import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ScoreCard } from "./ScoreCard";
import { QueryScorecard } from "../../lib/types";

const scorecard: QueryScorecard = {
  overall_quality: 8,
  citation_accuracy: 9,
  insight_depth: 7,
  notes: "Strong synthesis with grounded citations.",
  model_contribution_breakdown: {
    Researcher: "completed",
    Critic: "completed",
    Synthesizer: "completed",
  },
};

describe("ScoreCard", () => {
  it("renders quality scores, notes, and model contribution breakdown", () => {
    const html = renderToStaticMarkup(<ScoreCard scorecard={scorecard} />);

    expect(html).toContain("Research Scorecard");
    expect(html).toContain("Overall Quality");
    expect(html).toContain("8/10");
    expect(html).toContain("Citation Accuracy");
    expect(html).toContain("9/10");
    expect(html).toContain("Insight Depth");
    expect(html).toContain("7/10");
    expect(html).toContain("Strong synthesis with grounded citations.");
    expect(html).toContain("Researcher");
    expect(html).toContain("completed");
    expect(html).toContain("Critic");
    expect(html).toContain("Synthesizer");
  });
});
