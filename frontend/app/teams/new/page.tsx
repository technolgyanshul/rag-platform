"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ProtectedPage } from "../../../components/auth/ProtectedPage";
import { AppShell } from "../../../components/layout/AppShell";
import { createTeam, retrySeedDefaultAgents } from "../../../lib/api";
import { COLLAB_RULES, TeamFormState } from "../../../components/teams/shared";

/** Team creation page that seeds a new team then redirects to editor. */
export default function NewTeamPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [createdTeamId, setCreatedTeamId] = useState<string | null>(null);
  const [retryingSeed, setRetryingSeed] = useState(false);
  const [form, setForm] = useState<TeamFormState>({
    name: "",
    domain: "",
    collaboration_rule: "sequential",
  });

  const onCreate = async () => {
    if (!form.name.trim()) {
      setStatus("Team name is required");
      return;
    }
    setSaving(true);
    try {
      const created = await createTeam({
        name: form.name.trim(),
        domain: form.domain.trim() || null,
        collaboration_rule: form.collaboration_rule,
      });
      if ((created.seed_report?.failed ?? 0) > 0) {
        setCreatedTeamId(created.id);
        setStatus("Team created, but default agents could not be fully seeded. Retry seeding or continue to team editor.");
        return;
      }
      router.push(`/teams/${created.id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create team");
    } finally {
      setSaving(false);
    }
  };

  const onRetrySeeding = async () => {
    if (!createdTeamId) {
      return;
    }
    setRetryingSeed(true);
    try {
      const report = await retrySeedDefaultAgents(createdTeamId);
      if (report.failed > 0) {
        setStatus("Retry completed, but some default agents still failed to seed. Open the team editor and add agents manually if needed.");
        return;
      }
      router.push(`/teams/${createdTeamId}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not retry default agent seeding");
    } finally {
      setRetryingSeed(false);
    }
  };

  return (
    <ProtectedPage>
      <AppShell title="Create Team" subtitle="Create a team and continue in the team editor">
        <div className="card">
          <div className="form-field">
            <label>Team name</label>
            <input value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} />
          </div>
          <div className="form-field">
            <label>Research domain</label>
            <input value={form.domain} onChange={(event) => setForm((prev) => ({ ...prev, domain: event.target.value }))} />
          </div>
          <div className="form-field">
            <label>Collaboration rule</label>
            <select
              value={form.collaboration_rule}
              onChange={(event) => setForm((prev) => ({ ...prev, collaboration_rule: event.target.value as TeamFormState["collaboration_rule"] }))}
            >
              {COLLAB_RULES.map((rule) => (
                <option key={rule} value={rule}>{rule}</option>
              ))}
            </select>
          </div>
          <button type="button" disabled={saving} onClick={() => void onCreate()}>
            {saving ? "Creating..." : "Create team"}
          </button>
        </div>
        {status ? <p className="status-message">{status}</p> : null}
        {createdTeamId ? (
          <div className="button-row">
            <button type="button" disabled={retryingSeed} onClick={() => void onRetrySeeding()}>
              {retryingSeed ? "Retrying..." : "Retry default seeding"}
            </button>
            <button type="button" onClick={() => router.push(`/teams/${createdTeamId}`)}>
              Continue to team editor
            </button>
          </div>
        ) : null}
      </AppShell>
    </ProtectedPage>
  );
}
