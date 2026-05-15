import {
  Agent,
  CollaborationRule,
  DashboardMetrics,
  DocumentDownloadResponse,
  QueryHistoryItem,
  QueryResponse,
  SessionDetail,
  SessionExport,
  SessionListItem,
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

/** Captures lightweight browser context for observability payloads. */
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

export async function deleteKnowledgeDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/ingest/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not delete document");
  }
}

export async function runQuery(payload: {
  query: string;
  session_id: string;
  team_id: string;
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

export type CreateSessionPayload = {
  title?: string;
  team_id?: string;
};

export async function createSession(payload?: string | CreateSessionPayload): Promise<SessionRecord> {
  const body = typeof payload === "string" ? { title: payload } : (payload ?? {});
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
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

export async function listSessions(): Promise<SessionListItem[]> {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not load sessions");
  }
  return response.json();
}

export async function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not load session detail");
  }
  return response.json();
}

/** Extracts a download filename from a Content-Disposition header value. */
function exportFilenameFromDisposition(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(value);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const filenameMatch = /filename=\"?([^\";]+)\"?/i.exec(value);
  return filenameMatch?.[1] ?? null;
}

export async function downloadSessionExport(sessionId: string): Promise<{ filename: string; data: SessionExport }> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}/export.json`, {
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not export session");
  }

  const data = await response.json();
  const filename = exportFilenameFromDisposition(response.headers.get("content-disposition"))
    ?? `session-${sessionId}.json`;
  return {
    filename,
    data,
  };
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

export type SeedError = {
  agent_name: string;
  error: string;
};

export type SeedReport = {
  attempted: number;
  created: number;
  failed: number;
  skipped_existing: number;
  errors: SeedError[];
};

export type TeamCreateResult = Team & {
  seed_report?: SeedReport | null;
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
export type LMStudioProbePayload = {
  base_url: string;
  passcode?: string | null;
  timeout_seconds?: number;
};

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

export async function createTeam(payload: TeamCreatePayload): Promise<TeamCreateResult> {
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

export async function retrySeedDefaultAgents(teamId: string): Promise<SeedReport> {
  const response = await fetch(`${API_BASE_URL}/teams/${encodeURIComponent(teamId)}/seed-default-agents`, {
    method: "POST",
    headers: await buildAuthHeaders(),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Could not seed default agents");
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

/** Normalizes heterogeneous API error bodies into a user-facing message. */
function parseApiErrorMessage(errorBody: unknown, fallback: string): string {
  if (errorBody && typeof errorBody === "object") {
    const detail = (errorBody as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (detail && typeof detail === "object") {
      const message = (detail as { message?: unknown }).message;
      const category = (detail as { category?: unknown }).category;
      if (typeof message === "string" && typeof category === "string") {
        return `${category}: ${message}`;
      }
      if (typeof message === "string") {
        return message;
      }
    }
  }
  return fallback;
}

export async function probeLmStudioHealth(payload: LMStudioProbePayload): Promise<{ ok: boolean; models_count: number }> {
  const response = await fetch(`${API_BASE_URL}/teams/lmstudio/health`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(parseApiErrorMessage(errorBody, "Could not verify LM Studio connection"));
  }
  return response.json();
}

export async function listLmStudioModels(payload: LMStudioProbePayload): Promise<{ models: string[] }> {
  const response = await fetch(`${API_BASE_URL}/teams/lmstudio/models`, {
    method: "POST",
    headers: await buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(parseApiErrorMessage(errorBody, "Could not list LM Studio models"));
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
