import { Header } from "./Header";
import { AgentGrid } from "../AgentGrid";
import { EvidenceBoard } from "../EvidenceBoard";
import { MissionTimeline } from "../MissionTimeline";
import { VoicePanel } from "../VoicePanel";

export function WarRoomLayout() {
  return (
    <div className="bg-background text-text-primary h-screen w-screen flex flex-col overflow-hidden relative">
      {/* Subtle scanline texture overlay */}
      <div className="scanline absolute inset-0 pointer-events-none z-0" />

      <Header />

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* Left: Agent Fleet Grid (60%) */}
        <div className="flex flex-col w-[60%] overflow-hidden">
          <AgentGrid />
        </div>

        {/* Right: Evidence Board + Timeline (40%) */}
        <div className="flex flex-col w-[40%] border-l border-[#1e293b] overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <EvidenceBoard />
          </div>
          <div className="border-t border-[#1e293b] h-44 overflow-hidden">
            <MissionTimeline />
          </div>
        </div>
      </div>

      {/* Bottom: Voice Panel */}
      <div className="border-t border-[#1e293b] shrink-0" style={{ height: 140 }}>
        <VoicePanel />
      </div>
    </div>
  );
}
