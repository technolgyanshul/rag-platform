"use client";

import { FormEvent, useState } from "react";

import { uploadKnowledgeFile } from "../../lib/api";

type UploadPanelProps = {
  onUploaded: () => void;
};

export function UploadPanel({ onUploaded }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setMessage("Please choose a file.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const response = await uploadKnowledgeFile(file);
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
      <h3 style={{ marginBottom: 12 }}>Upload Document</h3>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          File
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </form>
      {message && <p className="status-message">{message}</p>}
    </div>
  );
}
