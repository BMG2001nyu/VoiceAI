import { create } from "zustand";
import type {
  MissionRecord,
  AgentState,
  EvidenceRecord,
  TimelineEvent,
  TranscriptEntry,
  ConnectionStatus,
} from "../types/api";

const MOCK_MISSION: MissionRecord = {
  id: "demo-mission-001",
  objective:
    "I'm pitching to Sequoia next week. Find their recent investments, partner priorities, founder complaints, and AI portfolio weaknesses.",
  status: "ACTIVE",
  created_at: new Date(Date.now() - 120_000).toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_AGENTS: AgentState[] = [
  {
    agent_id: "agent_0",
    status: "BROWSING",
    task_type: "OFFICIAL_SITE",
    objective: "Scrape sequoiacap.com for recent portfolio and partners",
    site_url: "sequoiacap.com",
  },
  {
    agent_id: "agent_1",
    status: "REPORTING",
    task_type: "NEWS_BLOG",
    objective: "Search news and blogs for Sequoia 2024–2025 investments",
    site_url: "techcrunch.com",
  },
  {
    agent_id: "agent_2",
    status: "BROWSING",
    task_type: "REDDIT_HN",
    objective: "Search Reddit/HN for founder complaints about Sequoia",
    site_url: "reddit.com",
  },
  {
    agent_id: "agent_3",
    status: "ASSIGNED",
    task_type: "GITHUB",
    objective: "Search GitHub for AI projects in Sequoia portfolio",
    site_url: "github.com",
  },
  {
    agent_id: "agent_4",
    status: "IDLE",
    task_type: "FINANCIAL",
    objective: "Retrieve financial data on recent Sequoia fund sizes",
  },
  {
    agent_id: "agent_5",
    status: "IDLE",
    task_type: "RECENT_NEWS",
    objective: "Find recent news about Sequoia AI strategy and bets",
  },
];

const MOCK_EVIDENCE: EvidenceRecord[] = [
  {
    id: "ev-001",
    mission_id: "demo-mission-001",
    agent_id: "agent_0",
    claim: "Sequoia has 8 active AI-focused partners as of 2025",
    summary:
      "Sequoia's website lists 8 partners with explicit AI/ML expertise including Sonya Huang (AI) and Pat Grady.",
    source_url: "https://sequoiacap.com/people",
    theme: "Partner Priorities",
    confidence: 0.95,
    created_at: new Date(Date.now() - 80_000).toISOString(),
  },
  {
    id: "ev-002",
    mission_id: "demo-mission-001",
    agent_id: "agent_1",
    claim: "Sequoia led $60M Series B in Wayve AI in late 2024",
    summary:
      "Sequoia Capital participated as lead investor in autonomous driving startup Wayve's $60M Series B round announced Q4 2024.",
    source_url: "https://techcrunch.com/2024/wayve-sequoia",
    theme: "AI Portfolio",
    confidence: 0.91,
    created_at: new Date(Date.now() - 55_000).toISOString(),
  },
  {
    id: "ev-003",
    mission_id: "demo-mission-001",
    agent_id: "agent_2",
    claim: "Founders report slow term sheet turnaround (>2 weeks) vs a16z",
    summary:
      "Multiple HN threads from 2024 cite Sequoia taking 2–3 weeks to issue term sheets vs a16z doing same-day decisions.",
    source_url: "https://news.ycombinator.com",
    theme: "Founder Complaints",
    confidence: 0.73,
    created_at: new Date(Date.now() - 30_000).toISOString(),
  },
];

const MOCK_TIMELINE: TimelineEvent[] = [
  {
    id: "t-001",
    type: "agent_assigned",
    description: "Agent agent_0 assigned to OFFICIAL_SITE",
    timestamp: new Date(Date.now() - 115_000).toISOString(),
    agent_id: "agent_0",
  },
  {
    id: "t-002",
    type: "agent_assigned",
    description: "Agent agent_1 assigned to NEWS_BLOG",
    timestamp: new Date(Date.now() - 113_000).toISOString(),
    agent_id: "agent_1",
  },
  {
    id: "t-003",
    type: "agent_assigned",
    description: "Agent agent_2 assigned to REDDIT_HN",
    timestamp: new Date(Date.now() - 111_000).toISOString(),
    agent_id: "agent_2",
  },
  {
    id: "t-004",
    type: "agent_assigned",
    description: "Agent agent_3 assigned to GITHUB",
    timestamp: new Date(Date.now() - 109_000).toISOString(),
    agent_id: "agent_3",
  },
  {
    id: "t-005",
    type: "evidence_found",
    description: "New finding: Sequoia has 8 active AI-focused partners as of 2025",
    timestamp: new Date(Date.now() - 80_000).toISOString(),
    agent_id: "agent_0",
  },
  {
    id: "t-006",
    type: "evidence_found",
    description: "New finding: Sequoia led $60M Series B in Wayve AI",
    timestamp: new Date(Date.now() - 55_000).toISOString(),
    agent_id: "agent_1",
  },
  {
    id: "t-007",
    type: "evidence_found",
    description: "New finding: Founders report slow term sheet turnaround",
    timestamp: new Date(Date.now() - 30_000).toISOString(),
    agent_id: "agent_2",
  },
];

const MOCK_TRANSCRIPT: TranscriptEntry[] = [
  {
    id: "tr-001",
    role: "user",
    text: "I'm pitching to Sequoia next week. Find their recent investments, partner priorities, founder complaints, and AI portfolio weaknesses.",
    timestamp: new Date(Date.now() - 120_000).toISOString(),
  },
  {
    id: "tr-002",
    role: "assistant",
    text: "Mission accepted. Deploying six agents now — covering official site, news, Reddit, GitHub, financial data, and recent AI news.",
    timestamp: new Date(Date.now() - 118_000).toISOString(),
  },
];

interface MissionStore {
  mission: MissionRecord | null;
  agents: AgentState[];
  evidence: EvidenceRecord[];
  timeline: TimelineEvent[];
  transcript: TranscriptEntry[];
  connectionStatus: ConnectionStatus;

  setMission: (m: MissionRecord) => void;
  updateAgent: (update: Partial<AgentState> & { agent_id: string }) => void;
  addEvidence: (e: EvidenceRecord) => void;
  addTimelineEvent: (ev: TimelineEvent) => void;
  addTranscriptEntry: (entry: TranscriptEntry) => void;
  setConnectionStatus: (s: ConnectionStatus) => void;
}

export const useMissionStore = create<MissionStore>((set) => ({
  mission: MOCK_MISSION,
  agents: MOCK_AGENTS,
  evidence: MOCK_EVIDENCE,
  timeline: MOCK_TIMELINE,
  transcript: MOCK_TRANSCRIPT,
  connectionStatus: "open",

  setMission: (m) => set({ mission: m }),

  updateAgent: (update) =>
    set((state) => {
      const existing = state.agents.find((a) => a.agent_id === update.agent_id);
      if (existing) {
        return {
          agents: state.agents.map((a) =>
            a.agent_id === update.agent_id ? { ...a, ...update } : a
          ),
        };
      }
      return { agents: [...state.agents, update as AgentState] };
    }),

  addEvidence: (e) =>
    set((state) => {
      if (state.evidence.some((ev) => ev.id === e.id)) return state;
      return { evidence: [e, ...state.evidence] };
    }),

  addTimelineEvent: (ev) =>
    set((state) => ({ timeline: [ev, ...state.timeline] })),

  addTranscriptEntry: (entry) =>
    set((state) => ({ transcript: [...state.transcript, entry] })),

  setConnectionStatus: (s) => set({ connectionStatus: s }),
}));
