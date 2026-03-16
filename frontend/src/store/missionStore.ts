import { create } from "zustand";
import type { Agent, AgentStep, Evidence, TimelineEvent } from "../types/mission";
import { createMission as apiCreateMission, synthesizeMission as apiSynthesizeMission } from "../services/api";
import type { MissionResponse } from "../services/api";

// ---------------------------------------------------------------------------
// Helpers: map backend payloads to v2 types
// ---------------------------------------------------------------------------

function mapAgentStatus(backendStatus: string): Agent["status"] {
  switch (backendStatus) {
    case "BROWSING":
    case "REPORTING":
    case "ASSIGNED":
      return "ACTIVE";
    case "IDLE":
      return "IDLE";
    default:
      return "IDLE";
  }
}

function mapAgentMode(backendStatus: string): Agent["mode"] {
  switch (backendStatus) {
    case "BROWSING":
      return "Browsing";
    case "REPORTING":
      return "Reporting";
    case "ASSIGNED":
      return "Analyzing";
    case "IDLE":
    default:
      return "Waiting";
  }
}

function mapAgentProgress(backendStatus: string): number {
  switch (backendStatus) {
    case "IDLE":
      return 100;
    case "ASSIGNED":
      return 15;
    case "BROWSING":
      return 50;
    case "REPORTING":
      return 85;
    default:
      return 0;
  }
}

function mapAgentActivity(backendStatus: string): number {
  switch (backendStatus) {
    case "BROWSING":
      return 0.8;
    case "REPORTING":
      return 0.6;
    case "ASSIGNED":
      return 0.3;
    case "IDLE":
      return 0.1;
    default:
      return 0;
  }
}

function agentNameFromId(agentId: string): string {
  const names: Record<string, string> = {
    agent_0: "WebSentry-00",
    agent_1: "DeepSignal-01",
    agent_2: "ForumSpy-02",
    agent_3: "GitAnalyzer-03",
    agent_4: "FinTracker-04",
    agent_5: "NewsRadar-05",
  };
  return names[agentId] ?? agentId;
}

interface MappedAgentUpdate extends Partial<Agent> {
  id: string;
  backendStatus: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapAgentUpdate(payload: any): MappedAgentUpdate {
  const id = payload.agent_id ?? payload.id ?? "unknown";
  const objective = payload.objective ?? payload.task_description ?? "";
  const siteUrl = payload.site_url ?? "";
  const backendStatus: string = payload.status ?? "IDLE";

  const result: MappedAgentUpdate = {
    id,
    name: agentNameFromId(id),
    status: mapAgentStatus(backendStatus),
    mode: mapAgentMode(backendStatus),
    progress: mapAgentProgress(backendStatus),
    lastUpdate: new Date().toISOString(),
    activity: mapAgentActivity(backendStatus),
    lastEventTimestamp: new Date().toISOString(),
    backendStatus,
  };

  // Only set task/targetDomain if we have non-empty values
  if (objective) {
    result.task = objective;
  }
  if (siteUrl) {
    result.targetDomain = siteUrl;
  }

  return result;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapEvidenceFound(payload: any): Evidence {
  const ev = payload.evidence ?? payload;
  return {
    id: ev.id ?? crypto.randomUUID(),
    title: ev.claim ?? "Untitled finding",
    summary: ev.summary ?? "",
    tags: ev.theme ? [ev.theme] : [],
    confidence: ev.confidence ?? 0.5,
    sources: ev.source_url
      ? [{ url: ev.source_url, title: ev.source_url, timestamp: ev.created_at ?? new Date().toISOString() }]
      : [],
    createdAt: ev.created_at ?? new Date().toISOString(),
    snippets: ev.snippet ? [ev.snippet] : [],
  };
}

function mapTimelineEventType(backendType: string): TimelineEvent["type"] {
  const mapping: Record<string, TimelineEvent["type"]> = {
    agent_assigned: "AGENT_DEPLOYED",
    evidence_found: "EVIDENCE_FOUND",
    agent_redirected: "AGENT_DEPLOYED",
    agent_timeout: "AGENT_FAILED",
    synthesis_start: "SYNTHESIS_COMPLETED",
    mission_complete: "SYNTHESIS_COMPLETED",
    contradiction_detected: "CONTRADICTION_DETECTED",
  };
  return mapping[backendType] ?? "EVIDENCE_FOUND";
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapTimelineEvent(payload: any): TimelineEvent {
  return {
    id: payload.id ?? crypto.randomUUID(),
    timestamp: payload.timestamp ?? new Date().toISOString(),
    type: mapTimelineEventType(payload.type ?? ""),
    agentId: payload.agent_id,
    message: payload.description ?? "",
    metadata: payload.metadata,
  };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export interface LiveMissionState {
  // Connection
  missionId: string | null;
  isConnected: boolean;
  isCreating: boolean;
  error: string | null;
  isSynthesizing: boolean;

  // Mission data
  objective: string;
  status: string;
  briefing: string | null;
  taskGraph: unknown[];

  // Live data from WebSocket
  agents: Agent[];
  evidence: Evidence[];
  timelineEvents: TimelineEvent[];

  // Actions
  createMission: (objective: string) => Promise<void>;
  synthesize: () => Promise<void>;
  reset: () => void;
  setConnected: (connected: boolean) => void;

  // WebSocket event handlers
  handleMissionStatus: (payload: MissionResponse) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleAgentUpdate: (payload: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleEvidenceFound: (payload: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleTimelineEvent: (payload: any) => void;
}

const INITIAL_STATE = {
  missionId: null,
  isConnected: false,
  isCreating: false,
  error: null,
  isSynthesizing: false,
  objective: "",
  status: "PENDING",
  briefing: null,
  taskGraph: [],
  agents: [],
  evidence: [],
  timelineEvents: [],
};

export const useLiveMissionStore = create<LiveMissionState>((set, get) => ({
  ...INITIAL_STATE,

  createMission: async (objective: string) => {
    set({ isCreating: true, error: null });
    try {
      const response = await apiCreateMission(objective);
      set({
        missionId: response.id,
        objective: response.objective,
        status: response.status,
        briefing: response.briefing,
        taskGraph: response.task_graph ?? [],
        isCreating: false,
        // Clear any stale live data
        agents: [],
        evidence: [],
        timelineEvents: [
          {
            id: crypto.randomUUID(),
            timestamp: new Date().toISOString(),
            type: "MISSION_STARTED",
            message: `Mission created: ${objective}`,
          },
        ],
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      set({ isCreating: false, error: message });
      throw err;
    }
  },

  synthesize: async () => {
    const { missionId } = get();
    if (!missionId) return;
    set({ isSynthesizing: true, error: null });
    try {
      const response = await apiSynthesizeMission(missionId);
      set({
        status: response.status,
        briefing: response.briefing,
        isSynthesizing: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      set({ isSynthesizing: false, error: message });
      throw err;
    }
  },

  reset: () => set(INITIAL_STATE),

  setConnected: (connected: boolean) => set({ isConnected: connected }),

  handleMissionStatus: (payload) => {
    set({
      status: payload.status ?? get().status,
      briefing: payload.briefing ?? get().briefing,
      objective: payload.objective ?? get().objective,
    });
  },

  handleAgentUpdate: (payload) => {
    const mapped = mapAgentUpdate(payload);
    const stepEntry: AgentStep = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      message: `${mapped.mode ?? "Status change"}: ${mapped.backendStatus}`,
      type: mapped.backendStatus === "IDLE" ? "success" : "info",
    };

    set((state) => {
      const existing = state.agents.find((a) => a.id === mapped.id);
      if (existing) {
        // Merge: preserve task/targetDomain if new payload lacks them
        const merged: Agent = {
          ...existing,
          name: mapped.name ?? existing.name,
          status: mapped.status ?? existing.status,
          mode: mapped.mode ?? existing.mode,
          progress: mapped.progress ?? existing.progress,
          lastUpdate: mapped.lastUpdate ?? existing.lastUpdate,
          activity: mapped.activity ?? existing.activity,
          lastEventTimestamp: mapped.lastEventTimestamp ?? existing.lastEventTimestamp,
          task: mapped.task ?? existing.task,
          targetDomain: mapped.targetDomain ?? existing.targetDomain,
          steps: [...existing.steps.slice(-19), stepEntry],
        };
        return {
          agents: state.agents.map((a) =>
            a.id === mapped.id ? merged : a
          ),
        };
      }
      // New agent: build full Agent object with defaults
      const newAgent: Agent = {
        id: mapped.id,
        name: mapped.name ?? mapped.id,
        status: mapped.status ?? "IDLE",
        mode: mapped.mode ?? "Waiting",
        task: mapped.task ?? "",
        targetDomain: mapped.targetDomain ?? "",
        progress: mapped.progress ?? 0,
        lastUpdate: mapped.lastUpdate ?? new Date().toISOString(),
        steps: [stepEntry],
        activity: mapped.activity ?? 0,
        lastEventTimestamp: mapped.lastEventTimestamp,
      };
      return { agents: [...state.agents, newAgent] };
    });
  },

  handleEvidenceFound: (payload) => {
    const mapped = mapEvidenceFound(payload);
    set((state) => {
      if (state.evidence.some((e) => e.id === mapped.id)) return state;
      return { evidence: [mapped, ...state.evidence] };
    });
  },

  handleTimelineEvent: (payload) => {
    const mapped = mapTimelineEvent(payload);
    set((state) => ({
      timelineEvents: [mapped, ...state.timelineEvents],
    }));
  },
}));
