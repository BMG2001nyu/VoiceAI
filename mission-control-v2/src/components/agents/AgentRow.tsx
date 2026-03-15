"use client";

import React, { useState } from "react";
import { Globe, RefreshCcw, Power, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { Agent } from "@/types/mission";
import { usePulseOnUpdate } from "@/hooks/usePulseOnUpdate";
import { ExpandableCard } from "@/components/ui/ExpandableCard";
import { useFocusStore } from "@/store/focusStore";

interface AgentRowProps {
    agent: Agent;
}

export function AgentRow({ agent }: AgentRowProps) {
    const [isOpen, setIsOpen] = useState(false);
    const isPulsing = usePulseOnUpdate(agent.lastUpdate);
    const openFocus = useFocusStore((s) => s.openFocus);

    const statusColor = {
        ACTIVE: "text-active",
        FAILED: "text-failed",
        IDLE: "text-idle",
    }[agent.status];

    const modeColor = {
        Browsing: "bg-browsing/10 text-browsing border-browsing/20",
        Reporting: "bg-reporting/10 text-reporting border-reporting/20",
        Analyzing: "bg-primary/10 text-primary border-primary/20",
        Waiting: "bg-muted text-muted-foreground border-border",
    }[agent.mode];

    const header = (
        <div className="w-full">
            {/* Top Row: Meta & Status */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <div className={cn(
                        "w-2 h-2 rounded-full",
                        agent.status === "ACTIVE" ? "bg-active animate-pulse" : (statusColor ? statusColor.replace("text-", "bg-") : "bg-muted")
                    )} />
                    <span className="text-[10px] font-mono font-bold text-muted-foreground uppercase">{agent.id}</span>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            openFocus(agent.id);
                        }}
                        className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-primary/10 text-[9px] font-bold text-primary border border-primary/20 hover:bg-primary/20 transition-all uppercase tracking-tighter"
                    >
                        <Activity size={10} /> Focus
                    </button>
                    <div className={cn("px-2 py-0.5 rounded text-[9px] font-bold tracking-tight border truncate max-w-[80px]", modeColor)}>
                        {agent.mode}
                    </div>
                </div>
            </div>

            {/* Name & Target */}
            <div className="flex flex-col gap-1">
                <h3 className="text-sm font-semibold truncate leading-none">{agent.name}</h3>
                <p className="text-[11px] text-muted-foreground line-clamp-1">{agent.task}</p>
                {agent.targetDomain && (
                    <div className="flex items-center gap-1.5 text-[10px] text-browsing font-mono mt-1">
                        <Globe size={10} />
                        <span className="truncate">{agent.targetDomain}</span>
                    </div>
                )}
            </div>

            {/* Progress bar */}
            {agent.status === "ACTIVE" && (
                <div className="mt-3 space-y-1">
                    <div className="flex items-center justify-between text-[9px] font-mono font-medium text-muted-foreground">
                        <span>{agent.progress}%</span>
                        <span>ETA {agent.eta}</span>
                    </div>
                    <div className="h-1 w-full bg-secondary rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary transition-all duration-1000 ease-in-out"
                            style={{ width: `${agent.progress}%` }}
                        />
                    </div>
                </div>
            )}
        </div>
    );

    return (
        <ExpandableCard
            isOpen={isOpen}
            onToggle={() => setIsOpen(!isOpen)}
            header={header}
            isPulsing={isPulsing}
        >
            <div className="space-y-4 pt-2">
                {/* Step Log */}
                <div className="space-y-2">
                    <span className="text-[9px] font-bold text-muted-foreground tracking-widest uppercase">RECENT EVENTS</span>
                    <div className="space-y-1.5">
                        {agent.steps.length > 0 ? agent.steps.slice(-3).map((step) => (
                            <div key={step.id} className="flex gap-2 text-[10px] leading-relaxed">
                                <span className="text-[9px] font-mono text-muted-foreground opacity-50 shrink-0">
                                    {new Date(step.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}
                                </span>
                                <span className={cn(
                                    "flex-1",
                                    step.type === "error" ? "text-failed" : "text-muted-foreground"
                                )}>{step.message}</span>
                            </div>
                        )) : (
                            <span className="text-[10px] text-muted-foreground italic">No recent events recorded...</span>
                        )}
                    </div>
                </div>

                {/* Failure Message */}
                {agent.error && (
                    <div className="p-2 rounded-lg bg-failed/10 border border-failed/20 text-[10px] text-failed">
                        <strong>ERROR:</strong> {agent.error}
                    </div>
                )}

                {/* Actions */}
                <div className="grid grid-cols-2 gap-2 mt-4">
                    <button className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-secondary text-[10px] font-bold hover:bg-muted transition-colors">
                        <Power size={11} /> STOP
                    </button>
                    <button className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-secondary text-[10px] font-bold hover:bg-muted transition-colors">
                        <RefreshCcw size={11} /> {agent.status === "FAILED" ? "RETRY" : "REASSIGN"}
                    </button>
                </div>
            </div>
        </ExpandableCard>
    );
}
