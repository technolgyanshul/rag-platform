"use client";

import { useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { UploadPanel } from "../../components/knowledge/UploadPanel";
import { AppShell } from "../../components/layout/AppShell";
import { DocumentRow, listKnowledgeDocuments } from "../../lib/api";

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [message, setMessage] = useState("Upload a document to populate the demo knowledge base.");

  const refreshDocuments = async () => {
    try {
      const rows = await listKnowledgeDocuments();
      setDocuments(rows);
      setMessage(rows.length ? "" : "No documents uploaded yet.");
    } catch (_error) {
      setMessage("Could not load uploaded documents.");
    }
  };

  return (
    <ProtectedPage>
        <AppShell
          title="Knowledge Base Management"
          subtitle="Upload, inspect, and sync documents used by retrieval"
          actions={
          <button type="button" onClick={() => void refreshDocuments()}>
            Refresh Documents
          </button>
        }
      >
        <div className="split-2">
          <div className="card">
            <p className="status-message" style={{ marginTop: 10 }}>
              This demo uses your signed-in account as the workspace context for uploads, chat, and analytics.
            </p>
          </div>
          <UploadPanel onUploaded={() => void refreshDocuments()} />
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Uploaded Documents</h3>
          {documents.length === 0 ? (
            <p className="status-message">{message}</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Chunks</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document: DocumentRow) => (
                    <tr key={document.id}>
                      <td>{document.filename}</td>
                      <td>{document.file_type.toUpperCase()}</td>
                      <td>{document.chunk_count}</td>
                      <td>{new Date(document.uploaded_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
