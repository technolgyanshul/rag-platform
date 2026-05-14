"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ProtectedPage } from "../../../components/auth/ProtectedPage";
import { AppShell } from "../../../components/layout/AppShell";
import {
  createTeamAgent,
  deleteTeam,
  deleteTeamAgent,
  listAgentDefaults,
  listLmStudioModels,
  listProviderModels,
  listTeamAgents,
  listTeams,
  probeLmStudioHealth,
  updateTeam,
  updateTeamAgent,
} from "../../../lib/api";
import { Agent, ProviderModels, Team } from "../../../lib/types";
import { AgentFormState, COLLAB_RULES, DEFAULT_AGENT_FORM, TeamFormState } from "../../../components/teams/shared";

export default function TeamDetailPage() {
  const params = useParams<{ id: string }>();
  const teamId = params.id;
  const router = useRouter();
  const [teams, setTeams] = useState<Team[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [status, setStatus] = useState<string>("Loading team...");
  const [savingTeam, setSavingTeam] = useState(false);
  const [savingAgent, setSavingAgent] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<string>("");
  const [probingLmStudio, setProbingLmStudio] = useState(false);
  const [providerModels, setProviderModels] = useState<ProviderModels>({ groq: ["llama-3.1-8b-instant"], sarvam: ["sarvam-m"], lmstudio: [] });
  const [agentDefaultsByRole, setAgentDefaultsByRole] = useState<Record<string, Agent>>({});
  const [teamForm, setTeamForm] = useState<TeamFormState>({ name: "", domain: "", collaboration_rule: "sequential" });
  const [agentForm, setAgentForm] = useState<AgentFormState>(DEFAULT_AGENT_FORM);

  const selectedTeam = useMemo(() => teams.find((team) => team.id === teamId) ?? null, [teams, teamId]);

  const loadTeams = async () => {
    const rows = await listTeams();
    setTeams(rows);
    const current = rows.find((row) => row.id === teamId);
    if (!current) {
      throw new Error("Team not found");
    }
    setTeamForm({ name: current.name, domain: current.domain ?? "", collaboration_rule: current.collaboration_rule });
  };

  const loadAgents = async () => {
    const rows = await listTeamAgents(teamId);
    setAgents(rows);
  };

  useEffect(() => {
    void (async () => {
      try {
        const [catalog, defaults] = await Promise.all([listProviderModels(), listAgentDefaults()]);
        setProviderModels({ groq: catalog.groq.length ? catalog.groq : ["llama-3.1-8b-instant"], sarvam: catalog.sarvam.length ? catalog.sarvam : ["sarvam-m"], lmstudio: [] });
        const map: Record<string, Agent> = {};
        for (const item of defaults) {
          map[item.role] = item;
        }
        setAgentDefaultsByRole(map);
        const researcherDefault = map.researcher;
        if (researcherDefault) {
          setAgentForm((prev) => ({ ...prev, role: researcherDefault.role, name: researcherDefault.name, system_prompt: researcherDefault.system_prompt, response_style: researcherDefault.response_style ?? prev.response_style, execution_order: researcherDefault.execution_order }));
        }
        await loadTeams();
        await loadAgents();
        setStatus("");
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Could not load team");
      }
    })();
  }, [teamId]);

  const resetAgentForm = () => {
    setEditingAgentId("");
    const fallback = agentDefaultsByRole.researcher;
    if (fallback) {
      setAgentForm({ ...DEFAULT_AGENT_FORM, name: fallback.name, role: fallback.role, system_prompt: fallback.system_prompt, response_style: fallback.response_style ?? DEFAULT_AGENT_FORM.response_style, execution_order: fallback.execution_order });
      return;
    }
    setAgentForm(DEFAULT_AGENT_FORM);
  };

  const onProviderChange = (provider: "groq" | "sarvam" | "lmstudio") => {
    const nextModel = provider === "lmstudio" ? agentForm.model_name || "local-model" : providerModels[provider][0] || "";
    setAgentForm((prev) => ({ ...prev, model_provider: provider, model_name: nextModel }));
  };

  const checkLmStudio = async () => {
    if (!agentForm.provider_base_url.trim()) {
      setStatus("LM Studio URL is required before testing connection");
      return;
    }
    setProbingLmStudio(true);
    try {
      const result = await probeLmStudioHealth({ base_url: agentForm.provider_base_url.trim(), passcode: agentForm.provider_passcode.trim() || null });
      setStatus(`LM Studio connected. Models visible: ${result.models_count}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "LM Studio connection failed");
    } finally {
      setProbingLmStudio(false);
    }
  };

  const fetchLmStudioModels = async () => {
    if (!agentForm.provider_base_url.trim()) {
      setStatus("LM Studio URL is required before fetching models");
      return;
    }
    setProbingLmStudio(true);
    try {
      const result = await listLmStudioModels({ base_url: agentForm.provider_base_url.trim(), passcode: agentForm.provider_passcode.trim() || null });
      setProviderModels((prev) => ({ ...prev, lmstudio: result.models }));
      if (result.models.length > 0) {
        setAgentForm((prev) => ({ ...prev, model_name: result.models[0] ?? prev.model_name }));
      }
      setStatus(result.models.length ? `Loaded ${result.models.length} LM Studio models` : "No LM Studio models were returned");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not fetch LM Studio models");
    } finally {
      setProbingLmStudio(false);
    }
  };

  const handleUpdateTeam = async () => {
    if (!selectedTeam || !teamForm.name.trim()) {
      setStatus("Team name is required");
      return;
    }
    setSavingTeam(true);
    try {
      await updateTeam(selectedTeam.id, { name: teamForm.name.trim(), domain: teamForm.domain.trim() || null, collaboration_rule: teamForm.collaboration_rule });
      await loadTeams();
      setStatus("Team updated");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not update team");
    } finally {
      setSavingTeam(false);
    }
  };

  const handleDeleteTeam = async () => {
    if (!selectedTeam) return;
    setSavingTeam(true);
    try {
      await deleteTeam(selectedTeam.id);
      router.push("/teams");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not delete team");
      setSavingTeam(false);
    }
  };

  const submitAgent = async () => {
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
      const payload = { name: agentForm.name.trim(), role: agentForm.role.trim(), system_prompt: agentForm.system_prompt, model_provider: agentForm.model_provider, model_name: agentForm.model_name.trim(), provider_base_url: agentForm.provider_base_url.trim() || null, provider_passcode: agentForm.provider_passcode.trim() || null, response_style: agentForm.response_style.trim() || null, execution_order: agentForm.execution_order };
      if (editingAgentId) await updateTeamAgent(teamId, editingAgentId, payload);
      else await createTeamAgent(teamId, payload);
      await loadAgents();
      setStatus(editingAgentId ? "Agent updated" : "Agent created");
      resetAgentForm();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save agent");
    } finally {
      setSavingAgent(false);
    }
  };

  return (
    <ProtectedPage>
      <AppShell title="Team Editor" subtitle="Edit team details and manage agent configuration">
        <div className="button-row" style={{ marginBottom: 12 }}><Link href="/teams">Back to teams</Link></div>
        <div className="teams-layout">
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Team Details</h3>
            <div className="form-field"><label>Team name</label><input value={teamForm.name} onChange={(event) => setTeamForm((prev) => ({ ...prev, name: event.target.value }))} /></div>
            <div className="form-field"><label>Research domain</label><input value={teamForm.domain} onChange={(event) => setTeamForm((prev) => ({ ...prev, domain: event.target.value }))} /></div>
            <div className="form-field"><label>Collaboration rule</label><select value={teamForm.collaboration_rule} onChange={(event) => setTeamForm((prev) => ({ ...prev, collaboration_rule: event.target.value as TeamFormState["collaboration_rule"] }))}>{COLLAB_RULES.map((rule) => (<option key={rule} value={rule}>{rule}</option>))}</select></div>
            <div className="button-row">
              <button type="button" disabled={savingTeam} onClick={() => void handleUpdateTeam()}>{savingTeam ? "Saving..." : "Save team"}</button>
              <button type="button" className="button-danger" disabled={savingTeam} onClick={() => void handleDeleteTeam()}>Delete team</button>
            </div>
          </div>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Agents</h3>
            <div className="table-wrap">
              <table className="data-table"><thead><tr><th>Name</th><th>Role</th><th>Prompt</th><th>Provider</th><th>Model</th><th>Order</th><th /></tr></thead><tbody>{agents.map((agent) => (
                <tr key={agent.id}><td>{agent.name}</td><td>{agent.role}</td><td title={agent.system_prompt}>{agent.system_prompt.length > 120 ? `${agent.system_prompt.slice(0, 120)}...` : agent.system_prompt}</td><td>{agent.model_provider}</td><td>{agent.model_name}</td><td>{agent.execution_order}</td><td><div className="button-row"><button type="button" onClick={() => { setEditingAgentId(agent.id); setAgentForm({ name: agent.name, role: agent.role, system_prompt: agent.system_prompt, model_provider: agent.model_provider === "sarvam" || agent.model_provider === "lmstudio" ? agent.model_provider : "groq", model_name: agent.model_name, provider_base_url: agent.provider_base_url ?? "", provider_passcode: "", response_style: agent.response_style ?? "", execution_order: agent.execution_order }); }}>Edit</button><button type="button" className="button-danger" onClick={() => void (async () => { setSavingAgent(true); try { await deleteTeamAgent(teamId, agent.id); await loadAgents(); setStatus("Agent deleted"); if (editingAgentId === agent.id) resetAgentForm(); } catch (error) { setStatus(error instanceof Error ? error.message : "Could not delete agent"); } finally { setSavingAgent(false); } })()}>Delete</button></div></td></tr>
              ))}</tbody></table>
            </div>
            <div className="stack">
              <h4>{editingAgentId ? "Edit agent" : "Add agent"}</h4>
              <div className="form-field"><label>Name</label><input value={agentForm.name} onChange={(event) => setAgentForm((prev) => ({ ...prev, name: event.target.value }))} /></div>
              <div className="form-field"><label>Role</label><select value={agentForm.role} onChange={(event) => { const nextRole = event.target.value; const roleDefault = agentDefaultsByRole[nextRole]; setAgentForm((prev) => ({ ...prev, role: nextRole, name: editingAgentId ? prev.name : roleDefault?.name ?? prev.name, system_prompt: editingAgentId ? prev.system_prompt : roleDefault?.system_prompt ?? prev.system_prompt, response_style: editingAgentId ? prev.response_style : roleDefault?.response_style ?? prev.response_style, execution_order: editingAgentId ? prev.execution_order : roleDefault?.execution_order ?? prev.execution_order })); }}><option value="researcher">researcher</option><option value="critic">critic</option><option value="synthesizer">synthesizer</option></select></div>
              <div className="form-field"><label>System prompt</label><textarea rows={4} value={agentForm.system_prompt} onChange={(event) => setAgentForm((prev) => ({ ...prev, system_prompt: event.target.value }))} /></div>
              <div className="form-field"><label>Provider</label><select value={agentForm.model_provider} onChange={(event) => onProviderChange(event.target.value as "groq" | "sarvam" | "lmstudio")}><option value="groq">groq</option><option value="sarvam">sarvam</option><option value="lmstudio">lmstudio</option></select></div>
              {agentForm.model_provider === "lmstudio" ? (<>
                <div className="form-field"><label>LM Studio URL</label><input placeholder="http://localhost:1234/v1" value={agentForm.provider_base_url} onChange={(event) => setAgentForm((prev) => ({ ...prev, provider_base_url: event.target.value }))} /></div>
                <div className="form-field"><label>LM Studio passcode (optional)</label><input type="password" value={agentForm.provider_passcode} onChange={(event) => setAgentForm((prev) => ({ ...prev, provider_passcode: event.target.value }))} /></div>
                <div className="button-row"><button type="button" disabled={probingLmStudio} onClick={() => void checkLmStudio()}>{probingLmStudio ? "Testing..." : "Test connection"}</button><button type="button" disabled={probingLmStudio} onClick={() => void fetchLmStudioModels()}>{probingLmStudio ? "Loading..." : "Fetch models"}</button></div>
                {providerModels.lmstudio.length > 0 ? (<div className="form-field"><label>Model name</label><select value={agentForm.model_name} onChange={(event) => setAgentForm((prev) => ({ ...prev, model_name: event.target.value }))}>{providerModels.lmstudio.map((model) => (<option key={model} value={model}>{model}</option>))}</select></div>) : (<div className="form-field"><label>Model name</label><input value={agentForm.model_name} onChange={(event) => setAgentForm((prev) => ({ ...prev, model_name: event.target.value }))} /></div>)}
              </>) : (<div className="form-field"><label>Model name</label><select value={agentForm.model_name} onChange={(event) => setAgentForm((prev) => ({ ...prev, model_name: event.target.value }))}>{(providerModels[agentForm.model_provider] || []).map((model) => (<option key={model} value={model}>{model}</option>))}</select></div>)}
              <div className="form-field"><label>Response style</label><input value={agentForm.response_style} onChange={(event) => setAgentForm((prev) => ({ ...prev, response_style: event.target.value }))} /></div>
              <div className="form-field"><label>Execution order</label><input type="number" min={0} max={20} value={agentForm.execution_order} onChange={(event) => setAgentForm((prev) => ({ ...prev, execution_order: Number(event.target.value || 0) }))} /></div>
              <div className="button-row"><button type="button" disabled={savingAgent} onClick={() => void submitAgent()}>{savingAgent ? "Saving..." : editingAgentId ? "Update agent" : "Add agent"}</button>{editingAgentId ? (<button type="button" onClick={resetAgentForm}>Cancel edit</button>) : null}</div>
            </div>
          </div>
        </div>
        {status ? <p className="status-message">{status}</p> : null}
      </AppShell>
    </ProtectedPage>
  );
}
