"use client";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";

export default function TeamPage() {
  return (
    <ProtectedPage>
      <AppShell
        title="Demo Workspace"
        subtitle="This demo runs in a single user-scoped workspace"
      >
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Workspace Scope</h3>
          <p className="status-message">
            Team setup is disabled in this demo. Uploaded documents, sessions, history, and dashboard metrics are scoped to your signed-in account automatically.
          </p>
        </div>
      </AppShell>
    </ProtectedPage>
  );
}
