import { afterEach, describe, expect, it, vi } from "vitest";

import { getDocumentDownloadUrl, listKnowledgeDocuments, uploadKnowledgeFile } from "./api";

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
        json: vi.fn().mockResolvedValue(mockResponse),
      }),
    );

    const result = await uploadKnowledgeFile(new File(["hello"], "sample.txt"));
    expect(result).toEqual(mockResponse);
  });

  it("throws backend detail when upload fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: vi.fn().mockResolvedValue({ detail: "Upload blocked" }),
      }),
    );

    await expect(uploadKnowledgeFile(new File(["hello"], "sample.txt"))).rejects.toThrow("Upload blocked");
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
