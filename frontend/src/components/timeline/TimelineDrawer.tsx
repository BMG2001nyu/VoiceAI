import React, { useState } from "react";
import { Clock, ChevronUp, ChevronDown, ListFilter, CalendarSync, Info, AlertTriangle, CheckCircle, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { TimelineEvent } from "@/types/mission";

interface TimelineDrawerProps {
    events: TimelineEvent[];
}

export function TimelineDrawer({ events }: TimelineDrawerProps) {
    const [isOpen, setIsOpen] = useState(false);

    const getTypeIcon = (type: string) => {
        switch (type) {
            case "MISSION_STARTED": return <CheckCircle size={14} className="text-primary" />;
            case "AGENT_DEPLOYED": return <CalendarSync size={14} className="text-browsing" />;
            case "EVIDENCE_FOUND": return <Info size={14} className="text-active" />;
            case "AGENT_FAILED": return <AlertTriangle size={14} className="text-failed" />;
            default: return <Clock size={14} className="text-muted-foreground" />;
        }
    };

    return (
        <div
            className={cn(
                "fixed right-0 bottom-20 left-0 bg-background/95 backdrop-blur-md border-t border-border z-30 transition-all duration-300 ease-in-out",
                isOpen ? "h-96" : "h-0"
            )}
        >
            {/* Drawer Handle */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="absolute -top-10 left-1/2 -translate-x-1/2 px-4 py-2 rounded-t-xl bg-background border-t border-x border-border flex items-center gap-2 text-[10px] font-bold text-muted-foreground hover:text-foreground transition-all"
            >
                {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                MISSION TIMELINE
            </button>

            {isOpen && (
                <div className="h-full flex flex-col p-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Historical Event Stream</h3>
                            <div className="flex items-center bg-muted/50 rounded-lg p-0.5 border border-border">
                                <button className="px-2 py-1 rounded-md bg-background text-[9px] font-bold text-primary shadow-sm">Real-time</button>
                                <button className="px-2 py-1 rounded-md text-[9px] font-bold text-muted-foreground">Historical</button>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="relative">
                                <Search className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground" size={10} />
                                <input
                                    type="text"
                                    placeholder="Filter by agent ID..."
                                    className="bg-muted/30 border border-border rounded-lg py-1 pl-6 pr-3 text-[10px] focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all font-mono w-40"
                                />
                            </div>
                            <button className="p-2 rounded-lg hover:bg-muted text-muted-foreground">
                                <ListFilter size={16} />
                            </button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto scrollbar-thin">
                        <div className="max-w-4xl mx-auto space-y-6">
                            {events.slice().reverse().map((event, i) => (
                                <div key={event.id} className="flex gap-6 group">
                                    <div className="w-24 shrink-0 text-right">
                                        <span className="text-[10px] font-mono font-medium text-muted-foreground opacity-40">
                                            {new Date(event.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                        </span>
                                    </div>

                                    <div className="flex flex-col items-center gap-2 shrink-0 pt-1">
                                        <div className="p-1.5 rounded-full bg-muted/40 border border-border/50 group-hover:border-primary/40 transition-colors">
                                            {getTypeIcon(event.type)}
                                        </div>
                                        {i !== events.length - 1 && <div className="w-px flex-1 bg-border/40" />}
                                    </div>

                                    <div className="flex-1 pb-8">
                                        <div className="flex items-baseline gap-2 mb-1">
                                            <span className="text-[11px] font-bold text-foreground">{event.type.replace("_", " ")}</span>
                                            {event.agentId && (
                                                <span className="px-1.5 py-0.5 rounded bg-secondary text-[8px] font-mono font-bold text-muted-foreground uppercase border border-border">
                                                    {event.agentId}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                                            {event.message}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
