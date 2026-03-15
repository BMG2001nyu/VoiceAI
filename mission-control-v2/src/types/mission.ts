export type MissionStatus = "ACTIVE" | "PAUSED" | "COMPLETED" | "FAILED";

export interface Mission {
    id: string;
    title: string;
    status: MissionStatus;
    summary: string;
    prompt: string;
    createdAt: string;
    updatedAt: string;
}

export type AgentStatus = "IDLE" | "ACTIVE" | "FAILED";
export type AgentMode = "Browsing" | "Reporting" | "Analyzing" | "Waiting";

export interface AgentStep {
    id: string;
    timestamp: string;
    message: string;
    type: "info" | "success" | "warning" | "error";
}

export interface Agent {
    id: string;
    name: string;
    status: AgentStatus;
    mode: AgentMode;
    task: string;
    targetDomain?: string;
    progress: number;
    eta?: string;
    lastUpdate: string;
    steps: AgentStep[];
    error?: string;
    activity?: number; // 0-1 for waveform intensity
    lastEventTimestamp?: string; // for triggering spikes
    transcriptSnippet?: string; // for displaying the latest agent thought/action
    isSpeaking?: boolean;
    isThinking?: boolean;
    currentTool?: string;
    currentTokens?: string[];
}

export interface Source {
    url: string;
    title: string;
    favicon?: string;
    timestamp: string;
}

export interface Evidence {
    id: string;
    title: string;
    summary: string;
    tags: string[];
    confidence: number;
    sources: Source[];
    createdAt: string;
    snippets: string[];
}

export type TimelineEventType =
    | "MISSION_STARTED"
    | "AGENT_DEPLOYED"
    | "EVIDENCE_FOUND"
    | "CONTRADICTION_DETECTED"
    | "SYNTHESIS_COMPLETED"
    | "AGENT_FAILED"
    | "MISSION_PAUSED"
    | "MISSION_RESUMED";

export interface TimelineEvent {
    id: string;
    timestamp: string;
    type: TimelineEventType;
    agentId?: string;
    message: string;
    metadata?: Record<string, any>;
}
