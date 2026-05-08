"use client";

import { FormEvent, useState } from "react";

type QueryInputProps = {
  onSubmit: (payload: { sessionId: string; query: string; topK: number }) => Promise<void>;
  onCreateSession: () => Promise<string>;
  disabled?: boolean;
};

export function QueryInput({ onSubmit, onCreateSession, disabled = false }: QueryInputProps) {
  const [sessionId, setSessionId] = useState("");
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [sessionMessage, setSessionMessage] = useState("");

  const handleCreateSession = async () => {
    try {
      setSessionMessage("Creating session...");
      const createdSessionId = await onCreateSession();
      setSessionId(createdSessionId);
      setSessionMessage("Session created.");
    } catch (error) {
      setSessionMessage(error instanceof Error ? error.message : "Could not create session.");
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }

    let nextSessionId = sessionId.trim();
    if (!nextSessionId) {
      try {
        setSessionMessage("Creating session...");
        nextSessionId = await onCreateSession();
        setSessionId(nextSessionId);
        setSessionMessage("");
      } catch (error) {
        setSessionMessage(error instanceof Error ? error.message : "Could not create session.");
        return;
      }
    }

    if (!nextSessionId) {
      return;
    }
    await onSubmit({ sessionId: nextSessionId, query: query.trim(), topK });
  };

  return (
    <form className="auth-form query-form" onSubmit={handleSubmit}>
      <div className="query-form__controls">
        <label className="form-field" htmlFor="chat-session-id">
          Session ID
          <div className="query-form__session-row">
            <input
              id="chat-session-id"
              value={sessionId}
              onChange={(event) => setSessionId(event.target.value)}
              placeholder="Session UUID"
            />
            <button type="button" onClick={() => void handleCreateSession()} disabled={disabled}>
              Create
            </button>
          </div>
        </label>

        <label className="form-field query-form__top-k" htmlFor="chat-top-k">
          Top K
          <input
            id="chat-top-k"
            type="number"
            min={1}
            max={20}
            value={topK}
            onChange={(event) => setTopK(Number(event.target.value) || 5)}
          />
        </label>
      </div>

      {sessionMessage ? <p className="status-message">{sessionMessage}</p> : null}

      <label className="form-field" htmlFor="chat-query">
        Question
        <textarea
          id="chat-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          rows={4}
          placeholder="Ask a question grounded in your uploaded files..."
        />
      </label>

      <button type="submit" disabled={disabled}>
        {disabled ? "Running..." : "Run Query"}
      </button>
    </form>
  );
}
