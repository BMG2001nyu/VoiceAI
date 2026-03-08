import { useMissionStore } from "../store";
import { AgentTile } from "./AgentTile";

export function AgentGrid() {
  const agents = useMissionStore((s) => s.agents);

  return (
    <div className="flex flex-col h-full">
      {/* Section header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1e293b] shrink-0">
        <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-text-secondary">
          Agent Fleet
        </span>
        <span className="text-[11px] font-mono text-text-secondary">
          {agents.filter((a) => a.status !== "IDLE").length}/{agents.length} active
        </span>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3">
        <div className="grid grid-cols-2 gap-3 h-full content-start">
          {agents.map((agent) => (
            <AgentTile key={agent.agent_id} agent={agent} />
          ))}
        </div>
      </div>
    </div>
  );
}
