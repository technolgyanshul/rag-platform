import { QueryResponse } from "../../lib/types";

type ChatWindowProps = {
  status: "idle" | "loading" | "success" | "error";
  response: QueryResponse | null;
  errorMessage: string;
};

export function ChatWindow({ status, response, errorMessage }: ChatWindowProps) {
  if (status === "idle") {
    return <p className="status-message">Run a query to view the answer, trace, and scorecard.</p>;
  }
  if (status === "loading") {
    return <p className="status-message">Running retrieval and multi-agent pipeline...</p>;
  }
  if (status === "error") {
    return <p className="status-message">{errorMessage}</p>;
  }
  if (!response) {
    return <p className="status-message">No response returned.</p>;
  }

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
    </div>
  );
}
