import React, { useState, useCallback } from "react";
import { TopBar } from "./components/layout/TopBar";
import { ThreeColumnLayout } from "./components/layout/ThreeColumnLayout";
import { AgentFleet } from "./components/agents/AgentFleet";
import { Workbench } from "./components/workbench/Workbench";
import { EvidenceBoardV2 } from "./components/evidence/EvidenceBoardV2";
import { CommandBar } from "./components/command/CommandBar";
import { TimelineDrawer } from "./components/timeline/TimelineDrawer";
import { Simulator } from "./components/Simulator";
import { AgentFocusOverlay } from "./components/agents/AgentFocusOverlay";
import { ToastHost } from "./components/ui/ToastHost";
import { useFocusStore } from "./store/focusStore";
import { MOCK_AGENTS, MOCK_EVIDENCE, MOCK_TIMELINE_EVENTS, MOCK_MISSION } from "./mock/data";
import { toast } from "./hooks/useToast";

export default function App() {
  const [agents, setAgents] = useState(MOCK_AGENTS);
  const [evidence, setEvidence] = useState(MOCK_EVIDENCE);
  const [activeCommand, setActiveCommand] = useState<{ agentId: string; text: string } | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);

  const selectedAgentId = useFocusStore((s) => s.selectedAgentId);
  const activeAgent = agents.find((a) => a.id === selectedAgentId) || null;

  const handleSendMessage = useCallback((agentId: string, text: string) => {
    setActiveCommand({ agentId, text });
    setTimeout(() => setActiveCommand(null), 100);
  }, []);

  const handleSend = useCallback((text: string) => {
    const target = agents.find(a => a.status === "ACTIVE");
    if (target) {
      setActiveCommand({ agentId: target.id, text });
      setTimeout(() => setActiveCommand(null), 100);
    } else {
      toast.show("No active agents to receive command", "error");
    }
  }, [agents]);

  const handleStop = useCallback((agentId: string) => {
    setAgents(prev => prev.map(a =>
      a.id === agentId
        ? { ...a, status: "IDLE" as const, mode: "Waiting" as const, progress: 0 }
        : a
    ));
    toast.success(`Agent ${agentId} stopped`);
  }, []);

  const handleReassign = useCallback((agentId: string) => {
    setAgents(prev => prev.map(a =>
      a.id === agentId
        ? { ...a, status: "ACTIVE" as const, mode: "Browsing" as const, progress: 0 }
        : a
    ));
    toast.success(`Agent ${agentId} reassigned`);
  }, []);

  const handlePause = useCallback(() => {
    setIsPaused(prev => !prev);
  }, []);

  const handleReset = useCallback(() => {
    setAgents(MOCK_AGENTS);
    setEvidence(MOCK_EVIDENCE);
    setIsPaused(false);
    toast.success("Mission reset to initial state");
  }, []);

  const handleMicToggle = useCallback(() => {
    setIsMicActive(prev => !prev);
  }, []);

  return (
    <div className="min-h-screen bg-background font-sans">
      <TopBar
        mission={MOCK_MISSION}
        isPaused={isPaused}
        onPause={handlePause}
        onReset={handleReset}
      />
      <ThreeColumnLayout
        left={<AgentFleet agents={agents} onStop={handleStop} onReassign={handleReassign} />}
        center={<Workbench mission={MOCK_MISSION} agents={agents} />}
        right={<EvidenceBoardV2 evidence={evidence} />}
        bottom={<CommandBar onSend={handleSend} isMicActive={isMicActive} onMicToggle={handleMicToggle} />}
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
      <ToastHost />
    </div>
  );
}
