export type Source = {
  document_id: string;
  filename: string;
  chunk_index: number;
  content_preview: string;
  score: number;
};

export type Citation = {
  document_id: string;
  filename: string;
  chunk_index: number;
  source_index: number;
};

export type AgentTrace = {
  id: string | null;
  agent_id: string | null;
  agent_name: string;
  agent_role: string;
  model_provider: string;
  model_name: string;
  status: string;
  latency_ms: number | null;
  output: string;
  error: string | null;
  citations: Record<string, unknown>[];
};

export type QueryScorecard = {
  overall_quality: number | null;
  citation_accuracy: number | null;
  insight_depth: number | null;
  model_contribution_breakdown: Record<string, unknown>;
  notes: string | null;
};

export type QueryResponse = {
  query_id: string | null;
  query: string;
  final_answer: string;
  reasoning?: string | null;
  sources: Source[];
  citations: Citation[];
  traces: AgentTrace[];
  scorecard: QueryScorecard | null;
  retrieval_count: number;
  insufficient_context: boolean;
  model_version: string;
  retrieval_metadata: {
    embedding_model_version: string;
    index_version: string;
    top_k: number;
  };
};

export type QueryUiState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: QueryResponse }
  | { status: "error"; message: string };

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

export type SessionListItem = {
  id: string;
  team_id: string | null;
  team_name: string | null;
  title: string | null;
  created_at: string;
  query_count: number;
  last_query_at: string | null;
};

export type SessionMessage = {
  id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SessionDetailRow = {
  id: string;
  session_id: string;
  query_text: string;
  final_answer: string;
  overall_score: number | null;
  citation_accuracy: number | null;
  insight_depth: number | null;
  response_time_ms: number | null;
  created_at: string;
  sources: Source[];
  citations: Citation[];
  retrieval_metadata: Record<string, unknown>;
  scorecard: QueryScorecard | null;
  agent_traces: AgentTrace[];
};

export type SessionDetail = {
  session: {
    id: string;
    team_id: string | null;
    team_name: string | null;
    title: string | null;
    created_at: string;
  };
  messages: SessionMessage[];
  queries: SessionDetailRow[];
};

export type SessionExport = {
  exported_at: string;
  schema_version: string;
  session: SessionDetail["session"];
  messages: SessionMessage[];
  queries: SessionDetailRow[];
};

export type DashboardMetrics = {
  total_queries: number;
  average_response_time_ms: number;
  average_overall_score: number;
  queries_over_time: Array<{ date: string; count: number }>;
};

export type SessionRecord = {
  id: string;
  title: string | null;
  team_id?: string | null;
  created_at: string;
};

export type DocumentDownloadResponse = {
  url: string;
  expires_in_seconds: number;
};

export type CollaborationRule = "sequential" | "debate" | "hierarchical";

export type Team = {
  id: string;
  user_id: string;
  name: string;
  domain: string | null;
  collaboration_rule: CollaborationRule;
  created_at: string;
};

export type Agent = {
  id: string;
  team_id: string;
  name: string;
  role: string;
  system_prompt: string;
  model_provider: "groq" | "sarvam" | "lmstudio" | string;
  model_name: string;
  provider_base_url: string | null;
  provider_passcode_configured: boolean;
  response_style: string | null;
  execution_order: number;
  created_at: string;
};

export type ProviderModels = {
  groq: string[];
  sarvam: string[];
  lmstudio: string[];
};
