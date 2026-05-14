"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";
import {
  createTeam,
  createTeamAgent,
  deleteTeam,
  deleteTeamAgent,
  listAgentDefaults,
  listTeamAgents,
  listProviderModels,
  listTeams,
  logUiEvent,
  updateTeam,
  updateTeamAgent,
} from "../../lib/api";
import { Agent, CollaborationRule, ProviderModels, Team } from "../../lib/types";

type TeamFormState = {
  name: string;
  domain: string;
  collaboration_rule: CollaborationRule;
};

type AgentFormState = {
  name: string;
  role: string;
  system_prompt: string;
  model_provider: "groq" | "sarvam" | "lmstudio";
  model_name: string;
  provider_base_url: string;
  provider_passcode: string;
  response_style: string;
  execution_order: number;
};

const COLLAB_RULES: CollaborationRule[] = ["sequential", "debate", "hierarchical"];

const DEFAULT_AGENT_FORM: AgentFormState = {
  name: "",
  role: "researcher",
  system_prompt: "",
  model_provider: "groq",
  model_name: "llama-3.1-8b-instant",
  provider_base_url: "",
  provider_passcode: "",
  response_style: "balanced",
  execution_order: 0,
};

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [status, setStatus] = useState<string>("Loading teams...");
  const [savingTeam, setSavingTeam] = useState(false);
  const [savingAgent, setSavingAgent] = useState(false);
  const [creatingTeam, setCreatingTeam] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<string>("");
  const [providerModels, setProviderModels] = useState<ProviderModels>({
    groq: ["llama-3.1-8b-instant"],
    sarvam: ["sarvam-m"],
    lmstudio: [],
  });
  const [agentDefaultsByRole, setAgentDefaultsByRole] = useState<Record<string, Agent>>({});

  const [newTeamForm, setNewTeamForm] = useState<TeamFormState>({
    name: "",
    domain: "",
    collaboration_rule: "sequential",
  });
  const [teamForm, setTeamForm] = useState<TeamFormState>({
    name: "",
    domain: "",
    collaboration_rule: "sequential",
  });
  const [agentForm, setAgentForm] = useState<AgentFormState>(DEFAULT_AGENT_FORM);

  const selectedTeam = useMemo(
    () => teams.find((team) => team.id === selectedTeamId) ?? null,
    [teams, selectedTeamId],
  );

  const loadTeams = async () => {
    try {
      const rows = await listTeams();
      setTeams(rows);
      if (rows.length === 0) {
        setSelectedTeamId("");
        setStatus("No teams yet. Create one below.");
        return;
      }
      setSelectedTeamId((prev) => (prev && rows.some((team) => team.id === prev) ? prev : rows[0].id));
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load teams");
    }
  };

  const loadAgents = async (teamId: string) => {
    try {
      const rows = await listTeamAgents(teamId);
      setAgents(rows);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load agents");
    }
  };

  const loadProviderModels = async () => {
    try {
      const catalog = await listProviderModels();
      setProviderModels({
        groq: catalog.groq.length ? catalog.groq : ["llama-3.1-8b-instant"],
        sarvam: catalog.sarvam.length ? catalog.sarvam : ["sarvam-m"],
        lmstudio: [],
      });
    } catch {
      // Keep fallback defaults in state if catalog load fails.
    }
  };

  const loadAgentDefaults = async () => {
    try {
      const defaults = await listAgentDefaults();
      const map: Record<string, Agent> = {};
      for (const item of defaults) {
        map[item.role] = item;
      }
      setAgentDefaultsByRole(map);
      const researcherDefault = map.researcher;
      if (researcherDefault) {
        setAgentForm((prev) => ({
          ...prev,
          role: researcherDefault.role,
          name: researcherDefault.name,
          system_prompt: researcherDefault.system_prompt,
          response_style: researcherDefault.response_style ?? prev.response_style,
          execution_order: researcherDefault.execution_order,
        }));
      }
    } catch {
      // Keep existing local defaults if backend defaults cannot be loaded.
    }
  };

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    void logUiEvent({ event_name: "page_view", page: "/teams", component: "TeamsPage", action: "load" }).catch(() => undefined);
    void loadTeams();
    void loadProviderModels();
    void loadAgentDefaults();
  }, []);

  useEffect(() => {
    if (!selectedTeam) {
      setTeamForm({ name: "", domain: "", collaboration_rule: "sequential" });
      setAgents([]);
      return;
    }
    setTeamForm({
      name: selectedTeam.name,
      domain: selectedTeam.domain ?? "",
      collaboration_rule: selectedTeam.collaboration_rule,
    });
    void loadAgents(selectedTeam.id);
  }, [selectedTeam]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleCreateTeam = async () => {
    if (!newTeamForm.name.trim()) {
      setStatus("Team name is required");
      return;
    }
    setCreatingTeam(true);
    try {
      const created = await createTeam({
        name: newTeamForm.name.trim(),
        domain: newTeamForm.domain.trim() || null,
        collaboration_rule: newTeamForm.collaboration_rule,
      });
      setNewTeamForm({ name: "", domain: "", collaboration_rule: "sequential" });
      setSelectedTeamId(created.id);
      await loadTeams();
      setStatus("Team created");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create team");
    } finally {
      setCreatingTeam(false);
    }
  };

  const handleUpdateTeam = async () => {
    if (!selectedTeam) {
      return;
    }
    if (!teamForm.name.trim()) {
      setStatus("Team name is required");
      return;
    }
    setSavingTeam(true);
    try {
      await updateTeam(selectedTeam.id, {
        name: teamForm.name.trim(),
        domain: teamForm.domain.trim() || null,
        collaboration_rule: teamForm.collaboration_rule,
      });
      await loadTeams();
      setStatus("Team updated");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not update team");
    } finally {
      setSavingTeam(false);
    }
  };

  const handleDeleteTeam = async () => {
    if (!selectedTeam) {
      return;
    }
    setSavingTeam(true);
    try {
      await deleteTeam(selectedTeam.id);
      setAgents([]);
      setSelectedTeamId("");
      await loadTeams();
      setStatus("Team deleted");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not delete team");
    } finally {
      setSavingTeam(false);
    }
  };

  const resetAgentForm = () => {
    setEditingAgentId("");
    const fallback = agentDefaultsByRole.researcher;
    if (fallback) {
      setAgentForm({
        ...DEFAULT_AGENT_FORM,
        name: fallback.name,
        role: fallback.role,
        system_prompt: fallback.system_prompt,
        response_style: fallback.response_style ?? DEFAULT_AGENT_FORM.response_style,
        execution_order: fallback.execution_order,
      });
      return;
    }
    setAgentForm(DEFAULT_AGENT_FORM);
  };

  const beginEditAgent = (agent: Agent) => {
    setEditingAgentId(agent.id);
    setAgentForm({
      name: agent.name,
      role: agent.role,
      system_prompt: agent.system_prompt,
      model_provider: agent.model_provider === "sarvam" || agent.model_provider === "lmstudio" ? agent.model_provider : "groq",
      model_name: agent.model_name,
      provider_base_url: agent.provider_base_url ?? "",
      provider_passcode: "",
      response_style: agent.response_style ?? "",
      execution_order: agent.execution_order,
    });
  };

  const submitAgent = async () => {
    if (!selectedTeam) {
      return;
    }
    if (!agentForm.name.trim() || !agentForm.role.trim() || !agentForm.system_prompt.trim()) {
      setStatus("Agent name, role, and system prompt are required");
      return;
    }
    if (agentForm.model_provider === "lmstudio" && !agentForm.provider_base_url.trim()) {
      setStatus("LM Studio URL is required when provider is lmstudio");
      return;
    }
    setSavingAgent(true);
    try {
      const payload = {
        name: agentForm.name.trim(),
        role: agentForm.role.trim(),
        system_prompt: agentForm.system_prompt,
        model_provider: agentForm.model_provider,
        model_name: agentForm.model_name.trim(),
        provider_base_url: agentForm.provider_base_url.trim() || null,
        provider_passcode: agentForm.provider_passcode.trim() || null,
        response_style: agentForm.response_style.trim() || null,
        execution_order: agentForm.execution_order,
      };
      if (editingAgentId) {
        await updateTeamAgent(selectedTeam.id, editingAgentId, payload);
      } else {
        await createTeamAgent(selectedTeam.id, payload);
      }
      await loadAgents(selectedTeam.id);
      setStatus(editingAgentId ? "Agent updated" : "Agent created");
      resetAgentForm();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save agent");
    } finally {
      setSavingAgent(false);
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!selectedTeam) {
      return;
    }
    setSavingAgent(true);
    try {
      await deleteTeamAgent(selectedTeam.id, agentId);
      await loadAgents(selectedTeam.id);
      setStatus("Agent deleted");
      if (editingAgentId === agentId) {
        resetAgentForm();
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not delete agent");
    } finally {
      setSavingAgent(false);
    }
  };

  const onProviderChange = (provider: "groq" | "sarvam" | "lmstudio") => {
    const nextModel = provider === "lmstudio" ? agentForm.model_name || "local-model" : providerModels[provider][0] || "";
    setAgentForm((prev) => ({ ...prev, model_provider: provider, model_name: nextModel }));
  };

  return (
    <ProtectedPage>
      <AppShell title="Teams" subtitle="Manage multi-agent teams, collaboration rules, and model assignments">
        <div className="teams-layout">
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Create Team</h3>
            <div className="form-field">
              <label>Team name</label>
              <input value={newTeamForm.name} onChange={(event) => setNewTeamForm((prev) => ({ ...prev, name: event.target.value }))} />
            </div>
            <div className="form-field">
              <label>Research domain</label>
              <input value={newTeamForm.domain} onChange={(event) => setNewTeamForm((prev) => ({ ...prev, domain: event.target.value }))} />
            </div>
            <div className="form-field">
              <label>Collaboration rule</label>
              <select
                value={newTeamForm.collaboration_rule}
                onChange={(event) => setNewTeamForm((prev) => ({ ...prev, collaboration_rule: event.target.value as CollaborationRule }))}
              >
                {COLLAB_RULES.map((rule) => (
                  <option key={rule} value={rule}>{rule}</option>
                ))}
              </select>
            </div>
            <button type="button" disabled={creatingTeam} onClick={() => void handleCreateTeam()}>
              {creatingTeam ? "Creating..." : "Create team"}
            </button>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Teams</h3>
            {teams.length === 0 ? <p className="status-message">No teams created yet.</p> : null}
            <div className="stack">
              {teams.map((team) => (
                <button
                  key={team.id}
                  type="button"
                  className={`team-list-item${selectedTeamId === team.id ? " is-active" : ""}`}
                  onClick={() => setSelectedTeamId(team.id)}
                >
                  <span>{team.name}</span>
                  <small>{team.domain || "No domain"} · {team.collaboration_rule}</small>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="teams-layout">
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Team Details</h3>
            {!selectedTeam ? (
              <p className="status-message">Select a team to edit details.</p>
            ) : (
              <div className="stack">
                <div className="form-field">
                  <label>Team name</label>
                  <input value={teamForm.name} onChange={(event) => setTeamForm((prev) => ({ ...prev, name: event.target.value }))} />
                </div>
                <div className="form-field">
                  <label>Research domain</label>
                  <input value={teamForm.domain} onChange={(event) => setTeamForm((prev) => ({ ...prev, domain: event.target.value }))} />
                </div>
                <div className="form-field">
                  <label>Collaboration rule</label>
                  <select
                    value={teamForm.collaboration_rule}
                    onChange={(event) => setTeamForm((prev) => ({ ...prev, collaboration_rule: event.target.value as CollaborationRule }))}
                  >
                    {COLLAB_RULES.map((rule) => (
                      <option key={rule} value={rule}>{rule}</option>
                    ))}
                  </select>
                </div>
                <div className="button-row">
                  <button type="button" disabled={savingTeam} onClick={() => void handleUpdateTeam()}>
                    {savingTeam ? "Saving..." : "Save team"}
                  </button>
                  <button type="button" className="button-danger" disabled={savingTeam} onClick={() => void handleDeleteTeam()}>
                    Delete team
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Agents</h3>
            {!selectedTeam ? <p className="status-message">Select a team to manage agents.</p> : null}
            {selectedTeam ? (
              <div className="teams-agents-grid">
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Role</th>
                        <th>Prompt</th>
                        <th>Provider</th>
                        <th>Model</th>
                        <th>Order</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {agents.map((agent) => (
                        <tr key={agent.id}>
                          <td>{agent.name}</td>
                          <td>{agent.role}</td>
                          <td title={agent.system_prompt}>
                            {agent.system_prompt.length > 120
                              ? `${agent.system_prompt.slice(0, 120)}...`
                              : agent.system_prompt}
                          </td>
                          <td>{agent.model_provider}</td>
                          <td>{agent.model_name}</td>
                          <td>{agent.execution_order}</td>
                          <td>
                            <div className="button-row">
                              <button type="button" onClick={() => beginEditAgent(agent)}>Edit</button>
                              <button type="button" className="button-danger" onClick={() => void handleDeleteAgent(agent.id)}>Delete</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="stack">
                  <h4>{editingAgentId ? "Edit agent" : "Add agent"}</h4>
                  <div className="form-field">
                    <label>Name</label>
                    <input value={agentForm.name} onChange={(event) => setAgentForm((prev) => ({ ...prev, name: event.target.value }))} />
                  </div>
                <div className="form-field">
                  <label>Role</label>
                  <select
                    value={agentForm.role}
                    onChange={(event) => {
                      const nextRole = event.target.value;
                      const roleDefault = agentDefaultsByRole[nextRole];
                      setAgentForm((prev) => ({
                        ...prev,
                        role: nextRole,
                        name: editingAgentId ? prev.name : roleDefault?.name ?? prev.name,
                        system_prompt: editingAgentId ? prev.system_prompt : roleDefault?.system_prompt ?? prev.system_prompt,
                        response_style: editingAgentId ? prev.response_style : roleDefault?.response_style ?? prev.response_style,
                        execution_order: editingAgentId ? prev.execution_order : roleDefault?.execution_order ?? prev.execution_order,
                      }));
                    }}
                  >
                    <option value="researcher">researcher</option>
                    <option value="critic">critic</option>
                    <option value="synthesizer">synthesizer</option>
                  </select>
                </div>
                  <div className="form-field">
                    <label>System prompt</label>
                    <textarea rows={4} value={agentForm.system_prompt} onChange={(event) => setAgentForm((prev) => ({ ...prev, system_prompt: event.target.value }))} />
                  </div>
                  <div className="form-field">
                    <label>Provider</label>
                    <select value={agentForm.model_provider} onChange={(event) => onProviderChange(event.target.value as "groq" | "sarvam" | "lmstudio")}>
                      <option value="groq">groq</option>
                      <option value="sarvam">sarvam</option>
                      <option value="lmstudio">lmstudio</option>
                    </select>
                  </div>

                  {agentForm.model_provider === "lmstudio" ? (
                    <>
                      <div className="form-field">
                        <label>LM Studio URL</label>
                        <input
                          placeholder="http://localhost:1234/v1"
                          value={agentForm.provider_base_url}
                          onChange={(event) => setAgentForm((prev) => ({ ...prev, provider_base_url: event.target.value }))}
                        />
                      </div>
                      <div className="form-field">
                        <label>LM Studio passcode (optional)</label>
                        <input
                          type="password"
                          value={agentForm.provider_passcode}
                          onChange={(event) => setAgentForm((prev) => ({ ...prev, provider_passcode: event.target.value }))}
                        />
                      </div>
                      <div className="form-field">
                        <label>Model name</label>
                        <input value={agentForm.model_name} onChange={(event) => setAgentForm((prev) => ({ ...prev, model_name: event.target.value }))} />
                      </div>
                    </>
                  ) : (
                    <div className="form-field">
                      <label>Model name</label>
                      <select value={agentForm.model_name} onChange={(event) => setAgentForm((prev) => ({ ...prev, model_name: event.target.value }))}>
                        {(providerModels[agentForm.model_provider] || []).map((model) => (
                          <option key={model} value={model}>{model}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="form-field">
                    <label>Response style</label>
                    <input value={agentForm.response_style} onChange={(event) => setAgentForm((prev) => ({ ...prev, response_style: event.target.value }))} />
                  </div>
                  <div className="form-field">
                    <label>Execution order</label>
                    <input
                      type="number"
                      min={0}
                      max={20}
                      value={agentForm.execution_order}
                      onChange={(event) => setAgentForm((prev) => ({ ...prev, execution_order: Number(event.target.value || 0) }))}
                    />
                  </div>
                  <div className="button-row">
                    <button type="button" disabled={savingAgent} onClick={() => void submitAgent()}>
                      {savingAgent ? "Saving..." : editingAgentId ? "Update agent" : "Add agent"}
                    </button>
                    {editingAgentId ? (
                      <button type="button" onClick={resetAgentForm}>Cancel edit</button>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        {status ? <p className="status-message">{status}</p> : null}
      </AppShell>
    </ProtectedPage>
  );
}
