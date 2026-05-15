import { describe, expect, it } from "vitest";

import { SessionListItem } from "./types";
import { selectMostRecentRunnableSession } from "./session-selection";

const session = (overrides: Partial<SessionListItem>): SessionListItem => ({
  id: "session",
  team_id: null,
  team_name: null,
  title: null,
  created_at: "2026-05-15T00:00:00Z",
  query_count: 0,
  last_query_at: null,
  ...overrides,
});

describe("selectMostRecentRunnableSession", () => {
  it("prefers the latest queried session over a newer empty session", () => {
    const result = selectMostRecentRunnableSession([
      session({ id: "new-empty", created_at: "2026-05-15T12:00:00Z", last_query_at: null }),
      session({
        id: "older-run",
        created_at: "2026-05-15T09:00:00Z",
        query_count: 1,
        last_query_at: "2026-05-15T10:00:00Z",
      }),
      session({
        id: "latest-run",
        created_at: "2026-05-15T08:00:00Z",
        query_count: 2,
        last_query_at: "2026-05-15T11:00:00Z",
      }),
    ]);

    expect(result?.id).toBe("latest-run");
  });

  it("falls back to the newest created session when no sessions have queries", () => {
    const result = selectMostRecentRunnableSession([
      session({ id: "old-empty", created_at: "2026-05-15T09:00:00Z" }),
      session({ id: "new-empty", created_at: "2026-05-15T12:00:00Z" }),
    ]);

    expect(result?.id).toBe("new-empty");
  });

  it("returns null when there are no sessions", () => {
    expect(selectMostRecentRunnableSession([])).toBeNull();
  });
});
