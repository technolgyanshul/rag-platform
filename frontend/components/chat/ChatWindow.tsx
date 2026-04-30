import { QueryUiState } from "../../lib/types";

type ChatWindowProps = {
  queryState: QueryUiState;
};

export function ChatWindow({ queryState }: ChatWindowProps) {
  if (queryState.status === "idle") {
    return <p className="status-message">Run a query to view the answer, trace, and scorecard.</p>;
  }
  if (queryState.status === "loading") {
    return <p className="status-message">Running retrieval and multi-agent pipeline...</p>;
  }
  if (queryState.status === "error") {
    return <p className="status-message">{queryState.message}</p>;
  }
  const response = queryState.data;

  return (
    <div>
      <p>
        <strong>Query:</strong> {response.query}
      </p>
      <p>
        <strong>Final Answer:</strong> {response.final_answer}
      </p>
      <p className="status-message">
        Retrieval count: {response.retrieval_count} | Insufficient context: {response.insufficient_context ? "yes" : "no"}
      </p>
      <p className="status-message">
        Model version: {response.model_version} | Embeddings: {response.retrieval_metadata.embedding_model_version} | Index: {response.retrieval_metadata.index_version}
      </p>
    </div>
  );
}
