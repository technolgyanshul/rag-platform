"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { UploadPanel } from "../../components/knowledge/UploadPanel";
import { AppShell } from "../../components/layout/AppShell";
import { DocumentRow, getDocumentDownloadUrl, listKnowledgeDocuments, logUiEvent } from "../../lib/api";

function documentStatus(document: DocumentRow): { label: string; className: string; title?: string } {
  if (document.index_status === "indexed") {
    return { label: "indexed", className: "badge badge--success" };
  }
  if (document.index_status === "indexing") {
    return { label: "indexing", className: "badge badge--warn" };
  }
  if (document.index_status === "failed") {
    return { label: "failed", className: "badge badge--danger", title: document.index_error ?? undefined };
  }
  return { label: "legacy", className: "badge", title: "Not indexed in Qdrant" };
}

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [message, setMessage] = useState("Upload a document to populate the demo knowledge base.");

  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/knowledge", component: "KnowledgePage", action: "load" }).catch((error: unknown) => {
      console.error("Failed to log knowledge page view event", error);
    });
  }, []);

  const refreshDocuments = async () => {
    try {
      const rows = await listKnowledgeDocuments();
      await logUiEvent({
        event_name: "documents_refresh_success",
        page: "/knowledge",
        component: "KnowledgePage",
        action: "refresh_documents",
        payload: { row_count: rows.length, documents: rows },
      }).catch((eventError: unknown) => {
        console.error("Failed to log documents refresh success event", eventError);
      });
      setDocuments(rows);
      setMessage(rows.length ? "" : "No documents uploaded yet.");
    } catch (error) {
      await logUiEvent({
        event_name: "documents_refresh_failure",
        page: "/knowledge",
        component: "KnowledgePage",
        action: "refresh_documents",
        payload: { error: error instanceof Error ? error.message : String(error) },
      }).catch((eventError: unknown) => {
        console.error("Failed to log documents refresh failure event", eventError);
      });
      setMessage("Could not load uploaded documents.");
    }
  };

  const handleDownload = async (documentId: string) => {
    try {
      const { url } = await getDocumentDownloadUrl(documentId);
      await logUiEvent({
        event_name: "document_open_success",
        page: "/knowledge",
        component: "KnowledgePage",
        action: "open_document",
        payload: { document_id: documentId, url },
      }).catch((eventError: unknown) => {
        console.error("Failed to log document open success event", eventError);
      });
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (error) {
      await logUiEvent({
        event_name: "document_open_failure",
        page: "/knowledge",
        component: "KnowledgePage",
        action: "open_document",
        payload: { document_id: documentId, error: error instanceof Error ? error.message : String(error) },
      }).catch((eventError: unknown) => {
        console.error("Failed to log document open failure event", eventError);
      });
      setMessage("Could not open the stored source file.");
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
                    <th>Status</th>
                    <th>Uploaded</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document: DocumentRow) => (
                    <tr key={document.id}>
                      <td>{document.filename}</td>
                      <td>{document.file_type.toUpperCase()}</td>
                      <td>{document.chunk_count}</td>
                      <td>
                        {(() => {
                          const status = documentStatus(document);
                          return (
                            <span className={status.className} title={status.title}>
                              {status.label}
                            </span>
                          );
                        })()}
                      </td>
                      <td>{new Date(document.uploaded_at).toLocaleString()}</td>
                      <td>
                        <button type="button" onClick={() => void handleDownload(document.id)}>
                          Open file
                        </button>
                      </td>
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
