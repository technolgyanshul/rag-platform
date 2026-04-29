import { afterEach, describe, expect, it, vi } from "vitest";

import { listKnowledgeDocuments, uploadKnowledgeFile } from "./api";

afterEach(() => {
  vi.restoreAllMocks();
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

    const result = await uploadKnowledgeFile("team-1", new File(["hello"], "sample.txt"));
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

    await expect(uploadKnowledgeFile("team-1", new File(["hello"], "sample.txt"))).rejects.toThrow("Upload blocked");
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

    await expect(listKnowledgeDocuments("team-1")).rejects.toThrow("Could not load documents");
  });
});
