import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiRequestError,
  createSession,
  getDocumentDownloadUrl,
  listKnowledgeDocuments,
  listRecentQueryHistory,
  logUiEvent,
  runQuery,
  uploadKnowledgeFile,
} from "./api";

vi.mock("@/utils/supabase/client", () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: "test-token",
          },
        },
      }),
    },
  })),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("uploadKnowledgeFile", () => {
  it("returns parsed upload response", async () => {
    const mockResponse = {
      document_id: "doc-1",
      filename: "sample.txt",
      file_type: "txt",
      chunks_created: 3,
    };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        headers: {
          get: vi.fn().mockReturnValue("req-123"),
        },
        json: vi.fn().mockResolvedValue(mockResponse),
      }),
    );

    const result = await uploadKnowledgeFile(new File(["hello"], "sample.txt"));
    expect(result).toEqual({ data: mockResponse, requestId: "req-123" });
  });

  it("throws backend detail with request id when upload fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        headers: {
          get: vi.fn().mockReturnValue("req-456"),
        },
        json: vi.fn().mockResolvedValue({ detail: "Upload blocked" }),
      }),
    );

    await expect(uploadKnowledgeFile(new File(["hello"], "sample.txt"))).rejects.toBeInstanceOf(ApiRequestError);
    await expect(uploadKnowledgeFile(new File(["hello"], "sample.txt"))).rejects.toMatchObject({
      message: "Upload blocked",
      requestId: "req-456",
    });
  });
});

describe("listKnowledgeDocuments", () => {
  it("throws when list request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
      }),
    );

    await expect(listKnowledgeDocuments()).rejects.toThrow("Could not load documents");
  });
});

describe("listRecentQueryHistory", () => {
  it("throws when recent history request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
      }),
    );

    await expect(listRecentQueryHistory()).rejects.toThrow("Could not load recent history");
  });
});

describe("getDocumentDownloadUrl", () => {
  it("returns signed URL and sends Authorization header", async () => {
    const mockResponse = {
      url: "https://storage.example.com/signed-url",
      expires_in_seconds: 300,
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockResponse),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await getDocumentDownloadUrl("doc-1");

    expect(result).toEqual(mockResponse);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/ingest/documents/doc-1/download", {
      headers: {
        Authorization: "Bearer test-token",
      },
    });
  });
});

describe("logUiEvent", () => {
  it("posts browser interaction events with auth headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ accepted: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await logUiEvent({
      event_name: "query_submit",
      page: "/chat",
      component: "QueryInput",
      action: "submit",
      payload: { query: "hello" },
    });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/observability/ui-events", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer test-token",
      },
      body: expect.stringContaining('"event_name":"query_submit"'),
    });
  });
});

describe("createSession", () => {
  it("sends team_id when creating a team-scoped session", async () => {
    const mockResponse = {
      id: "session-1",
      title: "Chat session",
      created_at: "2026-05-14T00:00:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockResponse),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createSession({ title: "Chat session", team_id: "team-1" });

    expect(result).toEqual(mockResponse);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer test-token",
      },
      body: JSON.stringify({ title: "Chat session", team_id: "team-1" }),
    });
  });
});

describe("runQuery", () => {
  it("sends team_id with the query payload", async () => {
    const mockResponse = {
      query_id: "query-1",
      query: "What changed?",
      final_answer: "A team-aware answer.",
      reasoning: null,
      sources: [],
      citations: [],
      traces: [],
      scorecard: null,
      retrieval_count: 0,
      insufficient_context: false,
      model_version: "test-model",
      retrieval_metadata: {
        embedding_model_version: "test-embedding",
        index_version: "test-index",
        top_k: 5,
      },
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockResponse),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery({
      query: "What changed?",
      session_id: "session-1",
      team_id: "team-1",
      top_k: 5,
    });

    expect(result).toEqual(mockResponse);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer test-token",
      },
      body: JSON.stringify({
        query: "What changed?",
        session_id: "session-1",
        team_id: "team-1",
        top_k: 5,
      }),
    });
  });
});

describe("API_BASE_URL", () => {
  it("uses NEXT_PUBLIC_API_BASE_URL when set for the demo tunnel", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "/api");

    const api = await import("./api");

    expect(api.API_BASE_URL).toBe("/api");
  });
});
