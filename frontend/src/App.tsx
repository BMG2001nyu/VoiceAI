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
import { useLiveMissionStore } from "./store/missionStore";
import { useMissionWebSocket } from "./hooks/useMissionWebSocket";
import { MOCK_AGENTS, MOCK_EVIDENCE, MOCK_TIMELINE_EVENTS, MOCK_MISSION } from "./mock/data";
import { useVoiceCapture } from "./hooks/useVoiceCapture";
import { toast } from "./hooks/useToast";
import type { Mission } from "./types/mission";

export type AppMode = "demo" | "live";

export default function App() {
  const [mode, setMode] = useState<AppMode>("demo");

  // ---- Demo state (existing behavior) ----
  const [demoAgents, setDemoAgents] = useState(MOCK_AGENTS);
  const [demoEvidence, setDemoEvidence] = useState(MOCK_EVIDENCE);
  const [activeCommand, setActiveCommand] = useState<{ agentId: string; text: string } | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);

  // ---- Live state from store ----
  const liveStore = useLiveMissionStore();

  // Connect WebSocket when in live mode and missionId is set
  useMissionWebSocket();

  // ---- Derived values based on mode ----
  const agents = mode === "live" ? liveStore.agents : demoAgents;
  const evidence = mode === "live" ? liveStore.evidence : demoEvidence;
  const timelineEvents = mode === "live" ? liveStore.timelineEvents : MOCK_TIMELINE_EVENTS;

  const mission: Mission = mode === "live" && liveStore.missionId
    ? {
        id: liveStore.missionId,
        title: liveStore.objective || "New Mission",
        status: (liveStore.status === "COMPLETE" ? "COMPLETED" : liveStore.status) as Mission["status"],
        summary: liveStore.briefing ?? "Live mission in progress...",
        prompt: liveStore.objective,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
    : MOCK_MISSION;

  // ---- Focus overlay ----
  const selectedAgentId = useFocusStore((s) => s.selectedAgentId);
  const activeAgent = agents.find((a) => a.id === selectedAgentId) || null;

  // ---- Handlers ----
  const handleSendMessage = useCallback((agentId: string, text: string) => {
    setActiveCommand({ agentId, text });
    setTimeout(() => setActiveCommand(null), 100);
  }, []);

  const handleSend = useCallback(async (text: string) => {
    if (mode === "live") {
      try {
        await liveStore.createMission(text);
        toast.success("Mission created. Agents deploying...");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create mission";
        toast.error(message);
      }
      return;
    }

    // Demo mode: send command to active agent
    const target = demoAgents.find(a => a.status === "ACTIVE");
    if (target) {
      setActiveCommand({ agentId: target.id, text });
      setTimeout(() => setActiveCommand(null), 100);
    } else {
      toast.show("No active agents to receive command", "error");
    }
  }, [mode, demoAgents, liveStore]);

  const handleStop = useCallback((agentId: string) => {
    if (mode === "demo") {
      setDemoAgents(prev => prev.map(a =>
        a.id === agentId
          ? { ...a, status: "IDLE" as const, mode: "Waiting" as const, progress: 0 }
          : a
      ));
    }
    toast.success(`Agent ${agentId} stopped`);
  }, [mode]);

  const handleReassign = useCallback((agentId: string) => {
    if (mode === "demo") {
      setDemoAgents(prev => prev.map(a =>
        a.id === agentId
          ? { ...a, status: "ACTIVE" as const, mode: "Browsing" as const, progress: 0 }
          : a
      ));
    }
    toast.success(`Agent ${agentId} reassigned`);
  }, [mode]);

  const handlePause = useCallback(() => {
    setIsPaused(prev => !prev);
  }, []);

  const handleReset = useCallback(() => {
    if (mode === "live") {
      liveStore.reset();
      setMode("demo");
      toast.success("Switched back to demo mode");
    } else {
      setDemoAgents(MOCK_AGENTS);
      setDemoEvidence(MOCK_EVIDENCE);
      setIsPaused(false);
      toast.success("Mission reset to initial state");
    }
  }, [mode, liveStore]);

  const voiceCapture = useVoiceCapture({
    onTranscript: handleSend,
  });

  const handleMicToggle = useCallback(() => {
    setIsMicActive(prev => !prev);
    voiceCapture.toggle();
  }, [voiceCapture]);

  const handleSynthesize = useCallback(async () => {
    if (mode === "live" && liveStore.missionId) {
      try {
        await liveStore.synthesize();
        toast.success("Synthesis complete");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Synthesis failed";
        toast.error(message);
      }
    } else {
      toast.success("Synthesizing intelligence from " + evidence.length + " findings...");
    }
  }, [mode, liveStore, evidence.length]);

  const handleModeToggle = useCallback(() => {
    const nextMode = mode === "demo" ? "live" : "demo";
    setMode(nextMode);
    toast.show(`Switched to ${nextMode.toUpperCase()} mode`, "info");
  }, [mode]);

  return (
    <div className="min-h-screen bg-background font-sans">
      <TopBar
        mission={mission}
        isPaused={isPaused}
        onPause={handlePause}
        onReset={handleReset}
        mode={mode}
        onModeToggle={handleModeToggle}
        isConnected={liveStore.isConnected}
      />
      <ThreeColumnLayout
        left={<AgentFleet agents={agents} onStop={handleStop} onReassign={handleReassign} />}
        center={<Workbench mission={mission} agents={agents} />}
        right={
          <EvidenceBoardV2
            evidence={evidence}
            onSynthesize={handleSynthesize}
            isSynthesizing={liveStore.isSynthesizing}
          />
        }
        bottom={
          <CommandBar
            onSend={handleSend}
            isMicActive={isMicActive}
            onMicToggle={handleMicToggle}
            isCreating={liveStore.isCreating}
            mode={mode}
            missionActive={mode === "live" && !!liveStore.missionId}
          />
        }
        drawer={<TimelineDrawer events={timelineEvents} />}
      />
      {mode === "demo" && (
        <Simulator
          onAgentsUpdate={setDemoAgents}
          onEvidenceUpdate={setDemoEvidence}
          userCommand={activeCommand}
        />
      )}
      <AgentFocusOverlay
        agent={activeAgent}
        onSendMessage={handleSendMessage}
      />
      <ToastHost />
    </div>
  );
}
