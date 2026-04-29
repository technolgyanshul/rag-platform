"use client";

import { FormEvent, useState } from "react";

import { uploadKnowledgeFile } from "../../lib/api";

type UploadPanelProps = {
  teamId: string;
  onUploaded: () => void;
};

export function UploadPanel({ teamId, onUploaded }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!teamId) {
      setMessage("Enter a team ID first.");
      return;
    }
    if (!file) {
      setMessage("Please choose a file.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const response = await uploadKnowledgeFile(teamId, file);
      setMessage(`Uploaded ${response.filename} with ${response.chunks_created} chunks.`);
      setFile(null);
      onUploaded();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Upload Knowledge</h2>
      <form className="auth-form" onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.txt"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </form>
      {message && <p className="status-message">{message}</p>}
    </div>
  );
}
