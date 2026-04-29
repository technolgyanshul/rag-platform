export type Scorecard = {
  overall: number;
  citation_accuracy: number;
  insight_depth: number;
  reasoning: string;
};

export type Source = {
  document_id: string;
  filename: string;
  chunk_index: number;
  content_preview: string;
  score: number;
};

export type AgentTraceRow = {
  agent_name: string;
  model_name: string;
  output: string;
  response_time_ms: number;
};

export type QueryResponse = {
  query_id: string | null;
  query: string;
  final_answer: string;
  sources: Source[];
  scorecard: Scorecard | null;
  agent_trace: AgentTraceRow[];
  retrieval_count: number;
  insufficient_context: boolean;
};

export type QueryHistoryItem = {
  id: string;
  session_id: string;
  query_text: string;
  final_answer: string;
  overall_score: number | null;
  citation_accuracy: number | null;
  insight_depth: number | null;
  response_time_ms: number | null;
  created_at: string;
};

export type DashboardMetrics = {
  total_queries: number;
  average_response_time_ms: number;
  average_overall_score: number;
  queries_over_time: Array<{ date: string; count: number }>;
};
