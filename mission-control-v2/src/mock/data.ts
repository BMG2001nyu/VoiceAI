import { Mission, Agent, Evidence, TimelineEvent } from "../types/mission";

export const MOCK_MISSION: Mission = {
    id: "m-001",
    title: "Sequoia Capital Investment Strategy (2025)",
    status: "ACTIVE",
    summary: "Identifying AI portfolio weaknesses, partner priorities, and founder sentiment for the upcoming pitch.",
    prompt: "Investigate Sequoia's recent AI investments, identify potential gaps in their portfolio, and research partner investment thesis. Aggregate common founder complaints from public forums.",
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    updatedAt: new Date().toISOString(),
};

export const MOCK_AGENTS: Agent[] = [
    {
        id: "agent-1",
        name: "WebSentry-01",
        status: "ACTIVE",
        mode: "Browsing",
        task: "Scraping official portfolio pages",
        targetDomain: "sequoiacap.com",
        progress: 75,
        eta: "2m",
        lastUpdate: new Date().toISOString(),
        activity: 0.4,
        lastEventTimestamp: new Date().toISOString(),
        steps: [
            { id: "s1", timestamp: new Date(Date.now() - 300000).toISOString(), message: "Initialized crawling on people page", type: "info" },
            { id: "s2", timestamp: new Date(Date.now() - 150000).toISOString(), message: "Extracted 12 partner bios", type: "success" },
        ],
    },
    {
        id: "agent-2",
        name: "DeepSignal",
        status: "ACTIVE",
        mode: "Reporting",
        task: "Analyzing recent news for Series B leads",
        targetDomain: "techcrunch.com",
        progress: 90,
        eta: "45s",
        lastUpdate: new Date().toISOString(),
        activity: 0.8,
        lastEventTimestamp: new Date().toISOString(),
        steps: [
            { id: "s1", timestamp: new Date(Date.now() - 600000).toISOString(), message: "Searching for 'Sequoia Series B AI'", type: "info" },
            { id: "s2", timestamp: new Date(Date.now() - 200000).toISOString(), message: "Found Wayve investment details", type: "success" },
        ],
    },
    {
        id: "agent-3",
        name: "ForumSpy",
        status: "FAILED",
        mode: "Waiting",
        task: "Scanning HN for sentiment",
        targetDomain: "news.ycombinator.com",
        progress: 40,
        lastUpdate: new Date(Date.now() - 600000).toISOString(),
        activity: 0.1,
        lastEventTimestamp: new Date(Date.now() - 600000).toISOString(),
        steps: [
            { id: "s1", timestamp: new Date(Date.now() - 900000).toISOString(), message: "Connecting to YC search API", type: "info" },
            { id: "s2", timestamp: new Date(Date.now() - 600000).toISOString(), message: "Rate limit exceeded on endpoint", type: "error" },
        ],
        error: "Failed to bypass Cloudflare protection on HN search.",
    },
    {
        id: "agent-4",
        name: "GitAnalyzer",
        status: "IDLE",
        mode: "Waiting",
        task: "Verifying open source contributions of portfolio companies",
        progress: 0,
        lastUpdate: new Date(Date.now() - 1200000).toISOString(),
        activity: 0,
        steps: [],
    },
];

export const MOCK_EVIDENCE: Evidence[] = [
    {
        id: "ev-1",
        title: "Sequoia has 8 AI-focused partners",
        summary: "Identification of key decision makers in the AI space, including Sonya Huang and Pat Grady. Thesis leans towards infrastructure.",
        tags: ["Partner Priorities", "AI"],
        confidence: 0.95,
        sources: [
            { url: "https://sequoiacap.com/people", title: "Sequoia Partners", timestamp: new Date(Date.now() - 1800000).toISOString() },
        ],
        createdAt: new Date(Date.now() - 1800000).toISOString(),
        snippets: [
            "Sonya Huang: Leading AI/ML investments with a focus on generative applications.",
            "Pat Grady: Managing partner with oversight on core tech foundations.",
        ],
    },
    {
        id: "ev-2",
        title: "Gap in Agentic AI Layer",
        summary: "Sequoia's current portfolio is heavy on foundational models (OpenAI, Glean) but lacks recent representation in the agentic orchestration layer.",
        tags: ["AI Portfolio", "Risks"],
        confidence: 0.82,
        sources: [
            { url: "https://techcrunch.com/sequoia-portfolio", title: "Next-gen AI landscape", timestamp: new Date(Date.now() - 3600000).toISOString() },
        ],
        createdAt: new Date(Date.now() - 3400000).toISOString(),
        snippets: [
            "Analysis reveals no major investments in agentic frameworks in the last 12 months.",
        ],
    },
    {
        id: "ev-3",
        title: "Founders report 'Slow Term Sheets'",
        summary: "Multiple reports suggest that while Sequoia is prestigious, their decision loop (2-3 weeks) is becoming a competitive risk against faster 'Tiger-style' funds.",
        tags: ["Founder Complaints"],
        confidence: 0.74,
        sources: [
            { url: "https://news.ycombinator.com", title: "HN Discussion", timestamp: new Date(Date.now() - 7200000).toISOString() },
        ],
        createdAt: new Date(Date.now() - 7200000).toISOString(),
        snippets: [
            "u/founder2024: Sequoia took 21 days for a TS while a16z did it in 48 hours.",
        ],
    },
];

export const MOCK_TIMELINE_EVENTS: TimelineEvent[] = [
    {
        id: "t-1",
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        type: "MISSION_STARTED",
        message: "Mission control initialized for Sequoia Research.",
    },
    {
        id: "t-2",
        timestamp: new Date(Date.now() - 3500000).toISOString(),
        type: "AGENT_DEPLOYED",
        agentId: "agent-1",
        message: "WebSentry-01 deployed to sequoiacap.com",
    },
    {
        id: "t-3",
        timestamp: new Date(Date.now() - 1800000).toISOString(),
        type: "EVIDENCE_FOUND",
        agentId: "agent-1",
        message: "Found 8 AI-focused partners on team page.",
    },
    {
        id: "t-4",
        timestamp: new Date(Date.now() - 600000).toISOString(),
        type: "AGENT_FAILED",
        agentId: "agent-3",
        message: "ForumSpy failed to access Hacker News.",
    },
];
