import React, { useState } from "react";
import { Filter, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Agent, AgentStatus } from "@/types/mission";
import { AgentRow } from "./AgentRow";

interface AgentFleetProps {
    agents: Agent[];
    onStop: (agentId: string) => void;
    onReassign: (agentId: string) => void;
}

export function AgentFleet({ agents, onStop, onReassign }: AgentFleetProps) {
    const [filter, setFilter] = useState<AgentStatus | "ALL">("ALL");
    const [searchQuery, setSearchQuery] = useState("");

    const filteredAgents = agents
        .filter(a => filter === "ALL" || a.status === filter)
        .filter(a => {
            if (searchQuery.trim().length === 0) return true;
            const q = searchQuery.toLowerCase();
            return a.name.toLowerCase().includes(q) || a.task.toLowerCase().includes(q) || a.id.toLowerCase().includes(q);
        });

    const activeCount = agents.filter(a => a.status === "ACTIVE").length;

    return (
        <div className="flex-1 flex flex-col min-h-0">
            {/* Header */}
            <div className="p-4 border-b border-border flex flex-col gap-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Agent Fleet</h2>
                        <div className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground text-[10px] font-mono">
                            {activeCount}/{agents.length}
                        </div>
                    </div>
                    <button className="p-1.5 rounded-md hover:bg-muted text-muted-foreground">
                        <Filter size={14} />
                    </button>
                </div>

                <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" size={12} />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search agents..."
                        className="w-full bg-muted/30 border border-border rounded-lg py-1.5 pl-8 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all font-mono"
                    />
                </div>
            </div>

            {/* Filter Tabs */}
            <div className="px-4 py-2 border-b border-border flex items-center gap-1.5 overflow-x-auto scrollbar-none">
                {["ALL", "ACTIVE", "IDLE", "FAILED"].map((s) => (
                    <button
                        key={s}
                        onClick={() => setFilter(s as AgentStatus | "ALL")}
                        className={cn(
                            "px-2.5 py-1 rounded-md text-[10px] font-bold uppercase transition-all shrink-0",
                            filter === s
                                ? "bg-secondary text-foreground border border-border"
                                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                        )}
                    >
                        {s}
                    </button>
                ))}
            </div>

            {/* Agent Cards List */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 scrollbar-thin">
                {filteredAgents.map((agent) => (
                    <AgentRow key={agent.id} agent={agent} onStop={onStop} onReassign={onReassign} />
                ))}
                {filteredAgents.length === 0 && (
                    <div className="p-8 text-center opacity-40">
                        <p className="text-xs text-muted-foreground italic">No agents match this filter.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
