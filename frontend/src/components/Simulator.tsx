import { useEffect, useState, useCallback, useRef } from "react";
import { MOCK_AGENTS, MOCK_EVIDENCE } from "@/mock/data";
import { Agent, Evidence } from "@/types/mission";

const MOCK_TOKENS = [
    "I am currently", "analyzing", "the seed", "funding", "landscape", "for", "agentic", "AI", "startups.",
    "Initial", "findings", "suggest", "a", "34%", "increase", "in", "valuation", "tiers", "compared", "to", "Q3.",
    "Scanning", "Crunchbase", "and", "TechCrunch", "for", "related", "liquidations.",
    "Wait,", "I found", "a", "critical", "overlap", "in", "Sequoia's", "portfolio", "concerning", "Mistral", "AI."
];

const RESPONSE_MAP: Record<string, string[]> = {
    "status": ["Systems", "checking", "out.", "All", "modules", "operating", "at", "99.8%", "efficiency.", "Current", "task:", "analyzing", "market", "volatility."],
    "update": ["Roger", "that.", "Initiating", "synchronized", "update", "across", "all", "monitored", "nodes.", "Estimated", "time:", "45s."],
    "default": ["Message", "received.", "I'm", "processing", "your", "request", "and", "aligning", "my", "current", "mission", "parameters", "accordingly."]
};

export function Simulator({
    onAgentsUpdate,
    onEvidenceUpdate,
    userCommand,
}: {
    onAgentsUpdate: (agents: Agent[]) => void;
    onEvidenceUpdate: (evidence: Evidence[]) => void;
    userCommand?: { agentId: string, text: string } | null;
}) {
    const [agents, setAgents] = useState<Agent[]>(MOCK_AGENTS);
    const [evidence, setEvidence] = useState<Evidence[]>(MOCK_EVIDENCE);
    const isRespondingRef = useRef<boolean>(false);

    const updateAgents = useCallback((newAgents: Agent[]) => {
        setAgents(newAgents);
        onAgentsUpdate(newAgents);
    }, [onAgentsUpdate]);

    // Handle User Commands
    useEffect(() => {
        if (userCommand && !isRespondingRef.current) {
            const { agentId, text } = userCommand;
            const index = agents.findIndex(a => a.id === agentId);
            if (index === -1) return;

            isRespondingRef.current = true;
            const newAgents = [...agents];
            const agent = { ...newAgents[index] };

            // Phase 1: Sudden Spike & Thinking
            agent.isThinking = true;
            agent.isSpeaking = false;
            agent.currentTokens = [];
            agent.activity = 1.0;
            agent.lastEventTimestamp = new Date().toISOString();
            agent.steps = [...agent.steps, {
                id: Math.random().toString(36).substring(2, 9),
                timestamp: new Date().toISOString(),
                message: `DIRECT_COMMAND_RECEIVED: "${text}"`,
                type: "info"
            }];

            newAgents[index] = agent;
            updateAgents(newAgents);

            // Phase 2: Response Stream
            setTimeout(() => {
                const responseTokens = RESPONSE_MAP[text.toLowerCase().includes("status") ? "status" : text.toLowerCase().includes("update") ? "update" : "default"];

                let tokenIdx = 0;
                const streamInterval = setInterval(() => {
                    const currentAgents = [...agents];
                    const currentAgent = { ...currentAgents[index] };

                    if (tokenIdx === 0) {
                        currentAgent.isThinking = false;
                        currentAgent.isSpeaking = true;
                    }

                    if (tokenIdx < responseTokens.length) {
                        currentAgent.currentTokens = [...(currentAgent.currentTokens || []), responseTokens[tokenIdx]];
                        currentAgent.activity = 0.9;
                        tokenIdx++;
                        currentAgents[index] = currentAgent;
                        updateAgents(currentAgents);
                    } else {
                        clearInterval(streamInterval);
                        currentAgent.isSpeaking = false;
                        currentAgent.activity = 0.2;
                        isRespondingRef.current = false;
                        currentAgents[index] = currentAgent;
                        updateAgents(currentAgents);
                    }
                }, 150);
            }, 1500);
        }
    }, [userCommand, agents, updateAgents]);

    // Regular Random Background Updates
    useEffect(() => {
        const interval = setInterval(() => {
            if (isRespondingRef.current) return;

            const mode = Math.random();
            if (mode < 0.8) {
                const index = Math.floor(Math.random() * agents.length);
                const newAgents = [...agents];
                const agent = { ...newAgents[index] };

                if (agent.status === "ACTIVE") {
                    const stateRoll = Math.random();
                    if (stateRoll < 0.2) {
                        agent.isThinking = true;
                        agent.isSpeaking = false;
                        agent.currentTool = undefined;
                        if (Math.random() > 0.5) agent.currentTokens = [];
                    } else if (stateRoll < 0.5) {
                        if (agent.isThinking) {
                            agent.isThinking = false;
                            agent.isSpeaking = true;
                            const count = Math.floor(Math.random() * 5) + 1;
                            const currentCount = agent.currentTokens?.length || 0;
                            agent.currentTokens = [...(agent.currentTokens || []), ...MOCK_TOKENS.slice(currentCount, currentCount + count)];
                            if (currentCount >= MOCK_TOKENS.length) agent.currentTokens = [];
                        }
                    } else if (stateRoll < 0.7) {
                        agent.isThinking = false;
                        agent.isSpeaking = false;
                        agent.currentTool = ["SEARCH", "ANALYZE", "FETCH", "REASON"][Math.floor(Math.random() * 4)];
                    } else {
                        agent.isThinking = false;
                        agent.isSpeaking = false;
                        agent.currentTool = undefined;
                    }

                    agent.progress = Math.min(100, agent.progress + 0.5);
                    agent.activity = agent.isSpeaking ? 0.9 : agent.isThinking ? 0.4 : agent.currentTool ? 0.6 : 0.2;

                    if (Math.random() > 0.8) {
                        agent.steps = [...agent.steps, {
                            id: Math.random().toString(36).substring(2, 9),
                            timestamp: new Date().toISOString(),
                            message: agent.currentTool ? `Executing ${agent.currentTool} against Sequoia dataset...` : `Synchronizing intelligence channel ${agent.id}...`,
                            type: "info"
                        }];
                        agent.lastUpdate = new Date().toISOString();
                        agent.lastEventTimestamp = new Date().toISOString();
                    }

                    newAgents[index] = agent;
                    updateAgents(newAgents);
                }
            } else {
                const index = Math.floor(Math.random() * evidence.length);
                const newEvidence = [...evidence];
                const item = { ...newEvidence[index] };
                item.createdAt = new Date().toISOString();
                item.confidence = Math.min(0.99, item.confidence + 0.002);
                newEvidence[index] = item;
                setEvidence(newEvidence);
                onEvidenceUpdate(newEvidence);
            }
        }, 4000);

        return () => clearInterval(interval);
    }, [agents, evidence, updateAgents, onEvidenceUpdate]);

    return null;
}
