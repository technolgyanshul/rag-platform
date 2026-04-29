import { DashboardMetrics, QueryHistoryItem, QueryResponse } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type IngestResponse = {
  document_id: string;
  filename: string;
  file_type: string;
  chunks_created: number;
};

export type DocumentRow = {
  id: string;
  team_id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  uploaded_at: string;
};

export async function uploadKnowledgeFile(teamId: string, file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("team_id", teamId);
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail ?? "Upload failed";
    throw new Error(message);
  }

  return response.json();
}

export async function listKnowledgeDocuments(teamId: string): Promise<DocumentRow[]> {
  const response = await fetch(`${API_BASE_URL}/ingest/documents?team_id=${encodeURIComponent(teamId)}`);
  if (!response.ok) {
    throw new Error("Could not load documents");
  }
  return response.json();
}

export async function runQuery(payload: {
  query: string;
  team_id: string;
  session_id: string;
  top_k?: number;
}): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? "Query failed");
  }

  return response.json();
}

export async function listQueryHistory(sessionId: string, limit = 50): Promise<QueryHistoryItem[]> {
  const response = await fetch(
    `${API_BASE_URL}/query/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`,
  );
  if (!response.ok) {
    throw new Error("Could not load history");
  }
  return response.json();
}

export async function getDashboardMetrics(sessionId: string, days = 7): Promise<DashboardMetrics> {
  const response = await fetch(
    `${API_BASE_URL}/dashboard/metrics?session_id=${encodeURIComponent(sessionId)}&days=${days}`,
  );
  if (!response.ok) {
    throw new Error("Could not load dashboard metrics");
  }
  return response.json();
}
