"use client";

import { FormEvent, useState } from "react";

import { ApiRequestError, logUiEvent, uploadKnowledgeFile } from "../../lib/api";

type UploadPanelProps = {
  onUploaded: () => Promise<void> | void;
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
    await logUiEvent({
      event_name: "upload_submit",
      page: "/knowledge",
      component: "UploadPanel",
      action: "submit",
      payload: { name: file.name, size: file.size, type: file.type },
    }).catch(() => undefined);
    try {
      const result = await uploadKnowledgeFile(file);
      await logUiEvent({
        event_name: "upload_success",
        page: "/knowledge",
        component: "UploadPanel",
        action: "upload_complete",
        payload: { file: { name: file.name, size: file.size, type: file.type }, response: result.data, request_id: result.requestId },
      }).catch(() => undefined);
      setMessage(`Uploaded ${result.data.filename} with ${result.data.chunks_created} indexed chunks. Request ID: ${result.requestId}`);
      setFile(null);
      await Promise.resolve(onUploaded());
      setMessage("");
    } catch (error) {
      const requestId = error instanceof ApiRequestError ? error.requestId : "unknown";
      await logUiEvent({
        event_name: "upload_failure",
        page: "/knowledge",
        component: "UploadPanel",
        action: "upload_error",
        payload: {
          file: { name: file.name, size: file.size, type: file.type },
          error: error instanceof Error ? error.message : String(error),
          request_id: requestId,
        },
      }).catch(() => undefined);
      setMessage(`${error instanceof Error ? error.message : "Upload failed"} (Request ID: ${requestId})`);
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
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              setFile(selected);
              if (selected) {
                void logUiEvent({
                  event_name: "file_selected",
                  page: "/knowledge",
                  component: "UploadPanel",
                  action: "select_file",
                  payload: { name: selected.name, size: selected.size, type: selected.type },
                }).catch(() => undefined);
              }
            }}
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
