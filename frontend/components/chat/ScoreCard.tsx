import { QueryScorecard } from "../../lib/types";

type ScoreCardProps = Readonly<{
  scorecard: QueryScorecard;
}>;

function formatScore(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "N/A";
  }
  return `${Math.round(value)}/10`;
}

function formatContribution(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return formatScore(value);
  }
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (value === null || value === undefined) {
    return "N/A";
  }
  return JSON.stringify(value);
}

export function ScoreCard({ scorecard }: ScoreCardProps) {
  const contributions = Object.entries(scorecard.model_contribution_breakdown ?? {});

  return (
    <section className="scorecard" aria-label="Research scorecard">
      <div className="scorecard__header">
        <h4>Research Scorecard</h4>
        {scorecard.notes ? <p className="status-message">{scorecard.notes}</p> : null}
      </div>

      <div className="score-grid">
        <div className="scorecard__metric">
          <span>Overall Quality</span>
          <strong>{formatScore(scorecard.overall_quality)}</strong>
        </div>
        <div className="scorecard__metric">
          <span>Citation Accuracy</span>
          <strong>{formatScore(scorecard.citation_accuracy)}</strong>
        </div>
        <div className="scorecard__metric">
          <span>Insight Depth</span>
          <strong>{formatScore(scorecard.insight_depth)}</strong>
        </div>
      </div>

      <div className="scorecard__breakdown">
        <h5>Model Contribution</h5>
        {contributions.length > 0 ? (
          <div className="scorecard__rows">
            {contributions.map(([model, contribution]) => (
              <div key={model} className="scorecard__row">
                <span>{model}</span>
                <strong>{formatContribution(contribution)}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="status-message">No model contribution data.</p>
        )}
      </div>
    </section>
  );
}
