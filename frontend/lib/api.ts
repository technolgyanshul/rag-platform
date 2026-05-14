import {
  Agent,
  CollaborationRule,
  DashboardMetrics,
  DocumentDownloadResponse,
  QueryHistoryItem,
  QueryResponse,
  SessionRecord,
  Team,
  ProviderModels,
} from "./types";
import { createClient } from "@/utils/supabase/client";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function buildAuthHeaders(base?: HeadersInit): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error("You must be signed in to call the API");
  }
  return {
    ...(base ?? {}),
    Authorization: `Bearer ${session.access_token}`,
  };
}

export type IngestResponse = {
  document_id: string;
  filename: string;
  file_type: string;
  chunks_created: number;
};

export type UploadKnowledgeResult = {
  data: IngestResponse;
  requestId: string;
};

export class ApiRequestError extends Error {
  requestId: string;

  constructor(message: string, requestId: string) {
    super(message);
    this.name = "ApiRequestError";
    this.requestId = requestId;
  }
}

export type DocumentRow = {
  id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  uploaded_at: string;
  index_backend?: string;
  index_status?: "indexed" | "indexing" | "failed" | "legacy_unindexed" | string;
  indexed_at?: string | null;
  index_error?: string | null;
  storage_path?: string | null;
  file_size_bytes?: number | null;
  file_sha256?: string | null;
};

export type UiEventPayload = {
  event_name: string;
  page?: string;
  component?: string;
  action?: string;
  payload?: Record<string, unknown>;
  browser?: Record<string, unknown>;
  client_timestamp?: string;
};

function browserMetadata(): Record<string, unknown> {
  if (typeof window === "undefined") {
    return {};
  }
  return {
    userAgent: window.navigator.userAgent,
    language: window.navigator.language,
    pathname: window.location.pathname,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
  };
}

export async function uploadKnowledgeFile(file: File): Promise<UploadKnowledgeResult> {
  const formData = new FormData();
  formData.append("file", file);

  const requestId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `upload-${Date.now()}`;

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    headers: await buildAuthHeaders({ "x-request-id": requestId }),
    body: formData,
  });
  const responseRequestId = response.headers.get("x-request-id") || requestId;

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? "Upload failed";
    throw new ApiRequestError(message, responseRequestId);
  }

  return {
    data: await response.json(),
    requestId: responseRequestId,
  };
}

export async function listKnowledgeDocuments(): Promise<DocumentRow[]> {
  const response = await fetch(`${API_BASE_URL}/ingest/documents`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error("Could not load documents");
  }
  return response.json();
}

export async function getDocumentDownloadUrl(documentId: string): Promise<DocumentDownloadResponse> {
  const response = await fetch(`${API_BASE_URL}/ingest/documents/${encodeURIComponent(documentId)}/download`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error("Could not create document download URL");
  }
  return response.json();
}

export async function runQuery(payload: {
  query: string;
  session_id: string;
  top_k?: number;
}): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Query failed");
  }

  return response.json();
}

export async function createSession(title?: string): Promise<SessionRecord> {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not create session");
  }

  return response.json();
}

export async function listQueryHistory(sessionId: string, limit = 50): Promise<QueryHistoryItem[]> {
  const response = await fetch(
    `${API_BASE_URL}/query/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`,
    { headers: await buildAuthHeaders() },
  );
  if (!response.ok) {
    throw new Error("Could not load history");
  }
  return response.json();
}

export async function listRecentQueryHistory(limit = 50): Promise<QueryHistoryItem[]> {
  const response = await fetch(
    `${API_BASE_URL}/query/history/recent?limit=${limit}`,
    { headers: await buildAuthHeaders() },
  );
  if (!response.ok) {
    throw new Error("Could not load recent history");
  }
  return response.json();
}

export async function getDashboardMetrics(sessionId: string, days = 7): Promise<DashboardMetrics> {
  const response = await fetch(
    `${API_BASE_URL}/dashboard/metrics?session_id=${encodeURIComponent(sessionId)}&days=${days}`,
    { headers: await buildAuthHeaders() },
  );
  if (!response.ok) {
    throw new Error("Could not load dashboard metrics");
  }
  return response.json();
}

export async function logUiEvent(payload: UiEventPayload): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/observability/ui-events`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      page: typeof window !== "undefined" ? window.location.pathname : "",
      client_timestamp: new Date().toISOString(),
      browser: browserMetadata(),
      ...payload,
    }),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not log UI event");
  }
}

export type TeamCreatePayload = {
  name: string;
  domain?: string | null;
  collaboration_rule?: CollaborationRule;
};

export type TeamPatchPayload = Partial<TeamCreatePayload>;

export type AgentCreatePayload = {
  name: string;
  role: string;
  system_prompt: string;
  model_provider?: string;
  model_name?: string;
  provider_base_url?: string | null;
  provider_passcode?: string | null;
  response_style?: string | null;
  execution_order?: number;
};

export type AgentPatchPayload = Partial<AgentCreatePayload>;

export async function listTeams(): Promise<Team[]> {
  const response = await fetch(`${API_BASE_URL}/teams`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not load teams");
  }
  return response.json();
}

export async function createTeam(payload: TeamCreatePayload): Promise<Team> {
  const response = await fetch(`${API_BASE_URL}/teams`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not create team");
  }
  return response.json();
}

export async function updateTeam(teamId: string, payload: TeamPatchPayload): Promise<Team> {
  const response = await fetch(`${API_BASE_URL}/teams/${encodeURIComponent(teamId)}`, {
    method: "PATCH",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not update team");
  }
  return response.json();
}

export async function deleteTeam(teamId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/teams/${encodeURIComponent(teamId)}`, {
    method: "DELETE",
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not delete team");
  }
}

export async function listTeamAgents(teamId: string): Promise<Agent[]> {
  const response = await fetch(`${API_BASE_URL}/teams/${encodeURIComponent(teamId)}/agents`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not load agents");
  }
  return response.json();
}

export async function createTeamAgent(teamId: string, payload: AgentCreatePayload): Promise<Agent> {
  const response = await fetch(`${API_BASE_URL}/teams/${encodeURIComponent(teamId)}/agents`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not create agent");
  }
  return response.json();
}

export async function updateTeamAgent(teamId: string, agentId: string, payload: AgentPatchPayload): Promise<Agent> {
  const response = await fetch(
    `${API_BASE_URL}/teams/${encodeURIComponent(teamId)}/agents/${encodeURIComponent(agentId)}`,
    {
      method: "PATCH",
      headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not update agent");
  }
  return response.json();
}

export async function deleteTeamAgent(teamId: string, agentId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/teams/${encodeURIComponent(teamId)}/agents/${encodeURIComponent(agentId)}`,
    {
      method: "DELETE",
      headers: await buildAuthHeaders(),
    },
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not delete agent");
  }
}

export async function listProviderModels(): Promise<ProviderModels> {
  const response = await fetch(`${API_BASE_URL}/teams/models`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not load model catalog");
  }
  return response.json();
}

export async function listAgentDefaults(): Promise<Agent[]> {
  const response = await fetch(`${API_BASE_URL}/teams/defaults/agents`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not load agent defaults");
  }
  const payload = await response.json();
  return Array.isArray(payload?.agents) ? payload.agents : [];
}
