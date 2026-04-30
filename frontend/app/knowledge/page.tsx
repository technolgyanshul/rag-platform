"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { UploadPanel } from "../../components/knowledge/UploadPanel";
import { AppShell } from "../../components/layout/AppShell";
import { DocumentRow, listKnowledgeDocuments } from "../../lib/api";

export default function KnowledgePage() {
  const [teamId, setTeamId] = useState("");
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [message, setMessage] = useState("Enter a team ID to load or upload documents.");

  const refreshDocuments = async () => {
    if (!teamId.trim()) {
      return;
    }

    try {
      const rows = await listKnowledgeDocuments(teamId.trim());
      setDocuments(rows);
      setMessage(rows.length ? "" : "No documents uploaded yet.");
    } catch (_error) {
      setMessage("Could not load documents for this team.");
    }
  };

  useEffect(() => {
    void refreshDocuments();
  }, []);

  return (
    <ProtectedPage>
      <AppShell
        title="Knowledge Base Management"
        subtitle="Upload, inspect, and sync team documents used by retrieval"
        actions={
          <button type="button" onClick={() => void refreshDocuments()} disabled={!teamId.trim()}>
            Refresh Documents
          </button>
        }
      >
        <div className="split-2">
          <div className="card">
            <label htmlFor="team-id">
              Team ID
              <input
                id="team-id"
                type="text"
                value={teamId}
                onChange={(event) => setTeamId(event.target.value)}
                placeholder="Enter your team UUID"
              />
            </label>
            <p className="status-message" style={{ marginTop: 10 }}>
              Use one team context for upload + retrieval + analytics.
            </p>
          </div>
          <UploadPanel teamId={teamId.trim()} onUploaded={() => void refreshDocuments()} />
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
