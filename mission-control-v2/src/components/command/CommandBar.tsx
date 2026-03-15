"use client";

import React from "react";
import { Mic, Send, Zap, ChevronUp, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

export function CommandBar() {
    return (
        <div className="w-full max-w-4xl px-4 flex flex-col gap-2">
            {/* System Status Line */}
            <div className="flex items-center gap-2 px-4 animate-in fade-in slide-in-from-bottom-1">
                <Terminal size={10} className="text-primary" />
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                    Mission accepted. Deploying agents to target domains...
                </span>
            </div>

            {/* Main Input Group */}
            <div className="relative group">
                <div className="absolute inset-0 bg-primary/5 rounded-2xl blur-xl group-focus-within:bg-primary/10 transition-all" />

                <div className="relative flex items-center gap-3 bg-card border border-border rounded-xl px-4 py-2 shadow-2xl focus-within:border-primary/50 transition-all">
                    <button className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition-colors shrink-0">
                        <Mic size={18} />
                    </button>

                    <div className="flex-1 min-w-0 flex items-center gap-2">
                        <span className="text-primary font-mono font-bold text-sm">/</span>
                        <input
                            type="text"
                            placeholder="Assign agent_2 reddit or /focus partner priorities..."
                            className="w-full bg-transparent border-none py-2 text-sm focus:outline-none placeholder:text-muted-foreground/50 font-medium"
                        />
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                        <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted/50 border border-border">
                            <Zap size={12} className="text-primary" />
                            <span className="text-[10px] font-bold text-muted-foreground uppercase">AUTOPILOT</span>
                        </div>

                        <button className="p-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity">
                            <Send size={18} />
                        </button>
                    </div>
                </div>

                {/* Floating Quick Action */}
                <button className="absolute -top-3 right-8 px-2 py-0.5 rounded bg-muted border border-border text-[9px] font-bold text-muted-foreground flex items-center gap-1 hover:text-foreground transition-colors group-hover:block hidden">
                    <ChevronUp size={10} /> QUICK ACTIONS
                </button>
            </div>
        </div>
    );
}
