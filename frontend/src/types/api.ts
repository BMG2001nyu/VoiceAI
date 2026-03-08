export type MissionStatus =
  | "PENDING"
  | "ACTIVE"
  | "SYNTHESIZING"
  | "COMPLETE"
  | "FAILED";

export type AgentStatus = "IDLE" | "ASSIGNED" | "BROWSING" | "REPORTING";

export type AgentType =
  | "OFFICIAL_SITE"
  | "NEWS_BLOG"
  | "REDDIT_HN"
  | "GITHUB"
  | "FINANCIAL"
  | "RECENT_NEWS";

export type TimelineEventType =
  | "agent_assigned"
  | "evidence_found"
  | "agent_redirected"
  | "agent_timeout"
  | "synthesis_start"
  | "mission_complete"
  | "contradiction_detected";

export type ConnectionStatus = "connecting" | "open" | "closed" | "error";

export interface MissionRecord {
  id: string;
  objective: string;
  status: MissionStatus;
  created_at: string;
  updated_at: string;
  briefing?: string;
}

export interface AgentState {
  agent_id: string;
  status: AgentStatus;
  task_type?: AgentType;
  objective?: string;
  site_url?: string;
  screenshot_url?: string;
}

export interface EvidenceRecord {
  id: string;
  mission_id: string;
  agent_id: string;
  claim: string;
  summary: string;
  source_url: string;
  snippet?: string;
  theme?: string;
  confidence: number;
  created_at: string;
  screenshot_url?: string;
}

export interface TimelineEvent {
  id: string;
  type: TimelineEventType;
  description: string;
  timestamp: string;
  agent_id?: string;
}

export interface TranscriptEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: string;
}
