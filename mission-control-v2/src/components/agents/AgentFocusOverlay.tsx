"use client";

import React, { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Pause, Play, Terminal, Database, Activity, Globe, Command, Search, Cpu, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { Agent } from "@/types/mission";
import { AgentPulse } from "../visual/AgentPulse";
import { TokenStream } from "../visual/TokenStream";
import { useFocusStore } from "@/store/focusStore";

interface AgentFocusOverlayProps {
    agent: Agent | null;
    onSendMessage?: (agentId: string, message: string) => void;
}

export function AgentFocusOverlay({ agent, onSendMessage }: AgentFocusOverlayProps) {
    const { isFocusOpen, closeFocus } = useFocusStore();
    const [isPaused, setIsPaused] = useState(false);
    const [message, setMessage] = useState("");

    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === "Escape") closeFocus();
        };
        window.addEventListener("keydown", handleEsc);
        return () => window.removeEventListener("keydown", handleEsc);
    }, [closeFocus]);

    const modeColors: Record<string, string> = {
        Browsing: "#06b6d4", // cyan
        Reporting: "#a855f7", // purple
        Analyzing: "#22c55e", // green
        Waiting: "#64748b", // gray
        Failed: "#ef4444", // red
    };

    const accentColor = agent ? (modeColors[agent.mode] || modeColors.Waiting) : "#64748b";

    if (!agent) return null;

    return (
        <AnimatePresence>
            {isFocusOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[100] bg-background/90 backdrop-blur-3xl flex flex-col overflow-hidden font-sans"
                >
                    {/* Immersive Background Elements */}
                    <div className="absolute inset-0 bg-radial-vignette pointer-events-none opacity-80" />
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] pointer-events-none" />

                    {/* Top Navigation / Identity */}
                    <div className="relative z-10 flex items-center justify-between p-8 animate-in fade-in slide-in-from-top-4 duration-700">
                        <div className="flex items-center gap-6">
                            <button
                                onClick={closeFocus}
                                className="group flex items-center gap-2 px-4 py-2 rounded-full border border-white/5 bg-white/5 hover:bg-white/10 transition-all text-[10px] font-black tracking-widest uppercase text-muted-foreground hover:text-foreground"
                            >
                                <X size={14} className="group-hover:rotate-90 transition-transform" />
                                RETURN TO FLEET
                            </button>
                            <div className="h-4 w-px bg-white/10" />
                            <div className="flex flex-col">
                                <div className="flex items-center gap-2">
                                    <span className="text-xl font-black tracking-tighter font-mono">{agent.id}</span>
                                    <span className="text-[10px] font-bold text-muted-foreground/60">/ {agent.name.toUpperCase()}</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-2xl bg-white/5 border border-white/5">
                                <div className={cn("w-1.5 h-1.5 rounded-full", agent.status === "ACTIVE" ? "bg-primary animate-pulse" : "bg-failed")} />
                                <span className="text-[10px] font-black tracking-[0.2em] text-muted-foreground">CHANNEL_ENCRYPTED</span>
                            </div>
                            <button
                                onClick={() => setIsPaused(!isPaused)}
                                className="p-3 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 transition-all text-muted-foreground hover:text-foreground"
                            >
                                {isPaused ? <Play size={18} fill="currentColor" /> : <Pause size={18} fill="currentColor" />}
                            </button>
                        </div>
                    </div>

                    {/* Center Stage: The Intelligence Circle */}
                    <div className="flex-1 relative flex flex-col items-center justify-center -mt-12">
                        <div className="relative">
                            <AgentPulse
                                status={agent.status}
                                isSpeaking={!isPaused && agent.isSpeaking}
                                isThinking={!isPaused && agent.isThinking}
                                color={accentColor}
                            />

                            {/* Tool Badges orbiting or floating near center */}
                            <AnimatePresence>
                                {agent.currentTool && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.5, y: 20 }}
                                        animate={{ opacity: 1, scale: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.5, y: 20 }}
                                        className="absolute -bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/10 border border-primary/20 text-primary uppercase"
                                    >
                                        <Search size={14} className="animate-spin-slow" />
                                        <span className="text-[10px] font-black tracking-widest">USING {agent.currentTool}</span>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Conversation / Thought Stream */}
                        <div className="mt-16 w-full flex flex-col items-center gap-8 px-8">
                            <div className="flex flex-col items-center gap-2">
                                <span className="text-[10px] font-black text-muted-foreground/40 uppercase tracking-[0.4em] mb-2">
                                    {agent.isSpeaking ? "TRANSMITTING" : agent.isThinking ? "PROTOTYPING THOUGHTS" : "AWAITING INSTRUCTION"}
                                </span>
                                <TokenStream tokens={agent.currentTokens || []} isSpeaking={agent.isSpeaking} />
                            </div>
                        </div>
                    </div>

                    {/* Bottom Dock: Side Intel Panels */}
                    <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-8 p-8 animate-in fade-in slide-in-from-bottom-8 duration-1000">
                        {/* Task Context */}
                        <div className="p-6 rounded-[2rem] bg-white/5 border border-white/5 backdrop-blur-xl flex flex-col gap-4">
                            <div className="flex items-center gap-3 opacity-40">
                                <Command size={14} />
                                <span className="text-[9px] font-black uppercase tracking-widest">Mission Directive</span>
                            </div>
                            <p className="text-xs font-medium text-muted-foreground/80 leading-relaxed">
                                {agent.task}
                            </p>
                        </div>

                        {/* Conversational Input: Floating in the center of the dock area */}
                        <div className="flex flex-col gap-4 items-center justify-center">
                            <div className="w-full max-w-sm relative group/input">
                                <input
                                    type="text"
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    placeholder="Send command to agent..."
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/40 focus:bg-white/10 transition-all placeholder:text-muted-foreground/30 font-sans"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && message.trim()) {
                                            onSendMessage?.(agent.id, message);
                                            setMessage("");
                                        }
                                    }}
                                />
                                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground/40 group-focus-within/input:text-primary transition-colors">
                                    <MessageSquare size={18} />
                                </div>
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1">
                                    <span className="text-[10px] font-black text-muted-foreground/20 px-1.5 py-0.5 rounded border border-white/5">ENTER</span>
                                </div>
                            </div>
                            <span className="text-[9px] font-black text-muted-foreground/20 uppercase tracking-[0.2em]">DIRECT_CHANNEL_OVERRIDE</span>
                        </div>

                        {/* Telemetry Stats */}
                        <div className="p-6 rounded-[2rem] bg-white/5 border border-white/5 backdrop-blur-xl flex flex-col gap-4">
                            <div className="flex items-center gap-3 opacity-40">
                                <Cpu size={14} />
                                <span className="text-[9px] font-black uppercase tracking-widest">Cognitive Load</span>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="flex flex-col">
                                    <span className="text-[8px] font-black text-muted-foreground uppercase opacity-40 mb-1">STABILITY</span>
                                    <span className="text-sm font-mono font-bold tracking-tighter">99.8%</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-[8px] font-black text-muted-foreground uppercase opacity-40 mb-1">LATENCY</span>
                                    <span className="text-sm font-mono font-bold tracking-tighter">~120MS</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
