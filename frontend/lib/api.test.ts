import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiRequestError, getDocumentDownloadUrl, listKnowledgeDocuments, listRecentQueryHistory, logUiEvent, uploadKnowledgeFile } from "./api";

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

describe("API_BASE_URL", () => {
  it("uses NEXT_PUBLIC_API_BASE_URL when set for the demo tunnel", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "/api");

    const api = await import("./api");

    expect(api.API_BASE_URL).toBe("/api");
  });
});
