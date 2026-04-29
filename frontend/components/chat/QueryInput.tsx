"use client";

import { FormEvent, useState } from "react";

type QueryInputProps = {
  onSubmit: (payload: { teamId: string; sessionId: string; query: string; topK: number }) => Promise<void>;
  disabled?: boolean;
};

export function QueryInput({ onSubmit, disabled = false }: QueryInputProps) {
  const [teamId, setTeamId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!teamId.trim() || !sessionId.trim() || !query.trim()) {
      return;
    }
    await onSubmit({ teamId: teamId.trim(), sessionId: sessionId.trim(), query: query.trim(), topK });
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <label htmlFor="chat-team-id">Team ID</label>
      <input id="chat-team-id" value={teamId} onChange={(event) => setTeamId(event.target.value)} placeholder="Team UUID" />

      <label htmlFor="chat-session-id">Session ID</label>
      <input
        id="chat-session-id"
        value={sessionId}
        onChange={(event) => setSessionId(event.target.value)}
        placeholder="Session UUID"
      />

      <label htmlFor="chat-top-k">Top K</label>
      <input
        id="chat-top-k"
        type="number"
        min={1}
        max={20}
        value={topK}
        onChange={(event) => setTopK(Number(event.target.value) || 5)}
      />

      <label htmlFor="chat-query">Question</label>
      <textarea
        id="chat-query"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        rows={4}
        placeholder="Ask a question grounded in your uploaded files..."
      />

      <button type="submit" disabled={disabled}>
        {disabled ? "Running..." : "Run Query"}
      </button>
    </form>
  );
}
