import { QueryUiState } from "../../lib/types";
import { ScoreCard } from "./ScoreCard";

type ChatWindowProps = Readonly<{
  queryState: QueryUiState;
}>;

export function ChatWindow({ queryState }: ChatWindowProps) {
  if (queryState.status === "idle") {
    return <p className="status-message">Run a query to view the answer and supporting sources.</p>;
  }
  if (queryState.status === "loading") {
    return <p className="status-message">Running retrieval and answer generation...</p>;
  }
  if (queryState.status === "error") {
    return <p className="status-message">{queryState.message}</p>;
  }
  const response = queryState.data;

  return (
    <div className="stack">
      <p>
        <strong>Query:</strong> {response.query}
      </p>
      {response.reasoning ? (
        <div className="card answer-panel answer-panel--reasoning">
          <h4>Reasoning</h4>
          <p>{response.reasoning}</p>
        </div>
      ) : null}
      <div className="card answer-panel answer-panel--final">
        <h4>Final Answer</h4>
        <p>{response.final_answer}</p>
      </div>
      {response.scorecard ? <ScoreCard scorecard={response.scorecard} /> : null}
      <p className="status-message">
        Retrieval count: {response.retrieval_count} | Insufficient context: {response.insufficient_context ? "yes" : "no"}
      </p>
      <p className="status-message">
        Model version: {response.model_version} | Embeddings: {response.retrieval_metadata.embedding_model_version} | Index:{" "}
        {response.retrieval_metadata.index_version}
      </p>
    </div>
  );
}
