import { Scorecard } from "../../lib/types";

type ScoreCardProps = {
  scorecard: Scorecard | null;
};

export function ScoreCard({ scorecard }: ScoreCardProps) {
  if (!scorecard) {
    return <p className="status-message">Scorecard unavailable for this response.</p>;
  }

  return (
    <div className="score-grid">
      <p>
        <strong>Overall:</strong> {scorecard.overall}
      </p>
      <p>
        <strong>Citation Accuracy:</strong> {scorecard.citation_accuracy}
      </p>
      <p>
        <strong>Insight Depth:</strong> {scorecard.insight_depth}
      </p>
      <p>
        <strong>Reasoning:</strong> {scorecard.reasoning}
      </p>
    </div>
  );
}
