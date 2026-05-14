import { CollaborationRule } from "../../lib/types";

export type TeamFormState = {
  name: string;
  domain: string;
  collaboration_rule: CollaborationRule;
};

export type AgentFormState = {
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

export const COLLAB_RULES: CollaborationRule[] = ["sequential", "debate", "hierarchical"];

export const DEFAULT_AGENT_FORM: AgentFormState = {
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
