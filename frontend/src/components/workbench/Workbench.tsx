import React, { useState } from "react";
import { Sparkles, Terminal, ListChecks, ChevronRight, Zap, Target } from "lucide-react";
import { Mission, Agent } from "@/types/mission";
import { toast } from "@/hooks/useToast";

interface WorkbenchProps {
    mission: Mission;
    agents: Agent[];
}

export function Workbench({ mission, agents }: WorkbenchProps) {
    const [showAllLogs, setShowAllLogs] = useState(false);
    const activeAgents = agents.filter(a => a.status === "ACTIVE");

    const tasks = [
        "Audit Tiger Global AI portfolio overlaps",
        "Scan Glassdoor for partner sentiment",
        "Verify Sequoia 2024 LP report data",
        "Extract YC demo day participants list"
    ];

    const handleTaskClick = (task: string) => {
        toast.success(`Task queued: ${task}`);
    };

    return (
        <div className="flex-1 flex flex-col min-h-0 bg-background/20 overflow-y-auto scrollbar-thin">
            {/* Current Focus Panel */}
            <div className="p-6 border-b border-border bg-gradient-to-br from-primary/[0.03] to-transparent">
                <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                        <Target size={18} />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-primary uppercase tracking-widest">CURRENT MISSION FOCUS</span>
                        <h2 className="text-sm font-bold text-foreground">{mission.title}</h2>
                    </div>
                </div>

                <div className="p-4 rounded-xl bg-card/60 border border-border/50 shadow-sm relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-3 text-primary/20 group-hover:text-primary/40 transition-colors">
                        <Sparkles size={48} />
                    </div>
                    <p className="text-[13px] text-muted-foreground leading-relaxed relative z-10 pr-12">
                        {mission.summary}
                    </p>
                    <div className="mt-4 flex items-center gap-3 relative z-10">
                        <div className="flex -space-x-2">
                            {activeAgents.map((a) => (
                                <div key={a.id} className="w-6 h-6 rounded-full bg-secondary border-2 border-background flex items-center justify-center text-[8px] font-bold text-muted-foreground">
                                    {a.name[0]}
                                </div>
                            ))}
                        </div>
                        <span className="text-[10px] font-bold text-muted-foreground uppercase">{activeAgents.length} Agents Collaborating</span>
                        <div className="flex-1 h-px bg-border/50" />
                        <span className="text-[10px] font-mono text-primary font-bold animate-pulse">ANALYZING...</span>
                    </div>
                </div>
            </div>

            {/* Active Agent Streams */}
            <div className="flex-1 p-6 flex flex-col gap-6">
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Terminal size={14} className="text-muted-foreground" />
                            <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Active Agent Streams</h3>
                        </div>
                        <button
                            onClick={() => setShowAllLogs((prev) => !prev)}
                            className="text-[10px] font-bold text-primary hover:underline uppercase"
                        >
                            {showAllLogs ? "Show Latest Only" : "View Full Logs"}
                        </button>
                    </div>

                    <div className="space-y-3">
                        {activeAgents.map((agent) => {
                            const steps = showAllLogs ? agent.steps : agent.steps.slice(-1);
                            return (
                                <div key={agent.id} className="flex gap-4 group">
                                    <div className="flex flex-col items-center gap-1 shrink-0 pt-1">
                                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                                        <div className="w-px flex-1 bg-border group-last:bg-transparent" />
                                    </div>
                                    <div className="flex-1 space-y-1.5 pb-4">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[11px] font-bold font-mono text-foreground">{agent.id}</span>
                                            <span className="text-[10px] font-medium text-muted-foreground">{agent.mode} on {agent.targetDomain || "Task"}</span>
                                            <span className="text-[9px] font-mono text-muted-foreground opacity-40 ml-auto">JUST NOW</span>
                                        </div>
                                        {steps.map((step) => (
                                            <div key={step.id} className="p-3 rounded-lg bg-secondary/30 border border-border/40 text-[11px] font-mono text-muted-foreground leading-relaxed">
                                                {step.message}
                                            </div>
                                        ))}
                                        {steps.length === 0 && (
                                            <div className="p-3 rounded-lg bg-secondary/30 border border-border/40 text-[11px] font-mono text-muted-foreground leading-relaxed">
                                                Initializing connection...
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Tasks Queue */}
                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <ListChecks size={14} className="text-muted-foreground" />
                        <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Pending Task Queue</h3>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {tasks.map((task, i) => (
                            <div
                                key={i}
                                onClick={() => handleTaskClick(task)}
                                className="flex items-center justify-between p-3 rounded-xl border border-border bg-card/20 hover:bg-card/40 transition-colors cursor-pointer group"
                            >
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className="p-1.5 rounded bg-muted text-muted-foreground">
                                        <Zap size={12} />
                                    </div>
                                    <span className="text-[11px] font-medium text-muted-foreground truncate group-hover:text-foreground transition-colors">
                                        {task}
                                    </span>
                                </div>
                                <ChevronRight size={12} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
