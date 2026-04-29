"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { UploadPanel } from "../../components/knowledge/UploadPanel";
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
      <main className="container">
        <h1>Knowledge Base</h1>
        <div className="card auth-card">
          <label htmlFor="team-id">Team ID</label>
          <input
            id="team-id"
            type="text"
            value={teamId}
            onChange={(event) => setTeamId(event.target.value)}
            placeholder="Enter your team UUID"
          />
          <div style={{ marginTop: "10px" }}>
            <button type="button" onClick={() => void refreshDocuments()}>
              Load Documents
            </button>
          </div>
        </div>

        <UploadPanel teamId={teamId.trim()} onUploaded={() => void refreshDocuments()} />

        <div className="card">
          <h2>Uploaded Documents</h2>
          {documents.length === 0 ? (
            <p className="status-message">{message}</p>
          ) : (
            <ul>
              {documents.map((document) => (
                <li key={document.id}>
                  {document.filename} ({document.file_type}) - {document.chunk_count} chunks
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </ProtectedPage>
  );
}
