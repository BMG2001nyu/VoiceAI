"use client";

import React, { useState, useCallback } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";
import { AgentFleet } from "@/components/agents/AgentFleet";
import { Workbench } from "@/components/workbench/Workbench";
import { EvidenceBoard } from "@/components/evidence/EvidenceBoard";
import { CommandBar } from "@/components/command/CommandBar";
import { TimelineDrawer } from "@/components/timeline/TimelineDrawer";
import { Simulator } from "@/components/Simulator";
import { AgentFocusOverlay } from "@/components/agents/AgentFocusOverlay";
import { useFocusStore } from "@/store/focusStore";
import { MOCK_AGENTS, MOCK_EVIDENCE, MOCK_TIMELINE_EVENTS, MOCK_MISSION } from "@/mock/data";

export default function MissionControlPage() {
  const [agents, setAgents] = useState(MOCK_AGENTS);
  const [evidence, setEvidence] = useState(MOCK_EVIDENCE);
  const [activeCommand, setActiveCommand] = useState<{ agentId: string, text: string } | null>(null);

  const selectedAgentId = useFocusStore((s) => s.selectedAgentId);
  const activeAgent = agents.find((a) => a.id === selectedAgentId) || null;

  const handleSendMessage = useCallback((agentId: string, text: string) => {
    setActiveCommand({ agentId, text });
    // Reset after a short delay so simulator sees it
    setTimeout(() => setActiveCommand(null), 100);
  }, []);

  return (
    <div className="min-h-screen bg-background font-sans">
      <TopBar mission={MOCK_MISSION} />

      <ThreeColumnLayout
        left={<AgentFleet agents={agents} />}
        center={<Workbench mission={MOCK_MISSION} agents={agents} />}
        right={<EvidenceBoard evidence={evidence} />}
        bottom={<CommandBar />}
        drawer={<TimelineDrawer events={MOCK_TIMELINE_EVENTS} />}
      />

      <Simulator
        onAgentsUpdate={setAgents}
        onEvidenceUpdate={setEvidence}
        userCommand={activeCommand}
      />

      <AgentFocusOverlay
        agent={activeAgent}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
