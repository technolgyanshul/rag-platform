import {
  DashboardMetrics,
  DocumentDownloadResponse,
  QueryHistoryItem,
  QueryResponse,
  SessionRecord,
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

export type DocumentRow = {
  id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  uploaded_at: string;
  storage_path?: string | null;
  file_size_bytes?: number | null;
  file_sha256?: string | null;
};

export async function uploadKnowledgeFile(file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    headers: await buildAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? "Upload failed";
    throw new Error(message);
  }

  return response.json();
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
