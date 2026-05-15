"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";
import { listTeams, logUiEvent } from "../../lib/api";
import { Team } from "../../lib/types";

/** Teams overview page with navigation into team editors. */
export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [status, setStatus] = useState<string>("Loading teams...");

  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/teams", component: "TeamsPage", action: "load" }).catch(() => undefined);
    void (async () => {
      try {
        const rows = await listTeams();
        setTeams(rows);
        setStatus(rows.length ? "" : "No teams yet. Create one to continue.");
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Could not load teams");
      }
    })();
  }, []);

  return (
    <ProtectedPage>
      <AppShell title="Teams" subtitle="Manage teams and open team-specific editors">
        <div className="hero-card">
          <div className="panel-title">
            <div>
              <h3>Teams</h3>
              <p className="status-message">Configure collaboration rules and open team-specific agent editors.</p>
            </div>
            <Link href="/teams/new"><button type="button">Create team</button></Link>
          </div>
          {teams.length === 0 ? <p className="status-message">No teams created yet.</p> : null}
          <div className="stack">
            {teams.map((team) => (
              <Link key={team.id} href={`/teams/${team.id}`} className="team-list-item" style={{ textDecoration: "none" }}>
                <span>{team.name}</span>
                <small>{team.domain || "No domain"} · {team.collaboration_rule}</small>
              </Link>
            ))}
          </div>
        </div>
        {status ? <p className="status-message">{status}</p> : null}
      </AppShell>
    </ProtectedPage>
  );
}
