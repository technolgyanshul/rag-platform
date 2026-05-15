import { SessionListItem } from "./types";

const toTimestamp = (value: string | null): number => {
  if (!value) {
    return 0;
  }
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : 0;
};

/** Selects the best default session for dashboard metrics. */
export function selectMostRecentRunnableSession(sessions: readonly SessionListItem[]): SessionListItem | null {
  const hasRunSessions = sessions.some((session) => Boolean(session.last_query_at));
  const candidates = hasRunSessions ? sessions.filter((session) => Boolean(session.last_query_at)) : sessions;

  return (
    [...candidates].sort((left, right) => {
      const leftPrimary = toTimestamp(hasRunSessions ? left.last_query_at : left.created_at);
      const rightPrimary = toTimestamp(hasRunSessions ? right.last_query_at : right.created_at);
      if (rightPrimary !== leftPrimary) {
        return rightPrimary - leftPrimary;
      }
      return toTimestamp(right.created_at) - toTimestamp(left.created_at);
    })[0] ?? null
  );
}
