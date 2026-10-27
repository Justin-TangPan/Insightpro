export interface Subscriber {
  id: number;
  email: string;
  name: string;
  active: number;
  weekdays: number[];
  send_time: string;
  language: "zh" | "en";
  subscriptions: EmailSubscription[];
}

export interface EmailSubscription {
  id: number;
  email_type: "business" | "technical";
  enabled: boolean;
  weekdays: number[];
  send_time: string;
  timezone: string;
}

export interface AccountUser {
  id: string;
  email: string;
  name: string;
  role: string;
  status: "active" | "disabled";
  agent_space_status: string;
  created_at: string;
  last_sign_in_at: string | null;
}

export interface AgentSpace extends AccountUser {
  runtime_status: "running" | "stopped";
  workspace_status: "ready" | "not_created";
  last_used_at: string | null;
  disk_bytes: number;
}

export interface AgentUsage {
  user_id: string;
  runtime_starts: number;
  days: Record<string, { requests?: number; input_tokens?: number; output_tokens?: number }>;
}

export interface ArtifactRequest {
  id: string;
  title: string;
  type: string;
  created_at: string;
}
