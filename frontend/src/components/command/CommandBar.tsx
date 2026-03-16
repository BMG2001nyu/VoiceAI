import React, { useState } from "react";
import { Mic, Send, Zap, ChevronUp, Terminal, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AppMode } from "@/App";

interface CommandBarProps {
    onSend: (text: string) => void;
    isMicActive: boolean;
    onMicToggle: () => void;
    isCreating?: boolean;
    mode?: AppMode;
    missionActive?: boolean;
}

export function CommandBar({ onSend, isMicActive, onMicToggle, isCreating = false, mode = "demo", missionActive = false }: CommandBarProps) {
    const [input, setInput] = useState("");
    const [isAutopilot, setIsAutopilot] = useState(false);

    const handleSend = () => {
        const trimmed = input.trim();
        if (trimmed.length === 0) return;
        if (isCreating) return;
        onSend(trimmed);
        setInput("");
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const statusLine = (() => {
        if (isMicActive) {
            return "Listening... speak your command or mission objective";
        }
        if (mode === "live" && isCreating) {
            return "Creating mission... deploying agents...";
        }
        if (mode === "live" && missionActive) {
            return "Mission active. Agents working. Type a follow-up command...";
        }
        if (mode === "live") {
            return "LIVE MODE: Type a mission objective to begin...";
        }
        return "Mission accepted. Deploying agents to target domains...";
    })();

    const placeholder = (() => {
        if (isMicActive) {
            return "Listening... speak now";
        }
        if (mode === "live" && !missionActive) {
            return "Describe your research mission objective...";
        }
        if (mode === "live" && missionActive) {
            return "Send a follow-up command to agents...";
        }
        return "Assign agent_2 reddit or /focus partner priorities...";
    })();

    return (
        <div className="w-full max-w-4xl px-4 flex flex-col gap-2">
            {/* System Status Line */}
            <div className="flex items-center gap-2 px-4 animate-in fade-in slide-in-from-bottom-1">
                {isMicActive ? (
                    <Mic size={10} className="text-red-500 animate-pulse" />
                ) : isCreating ? (
                    <Loader2 size={10} className="text-primary animate-spin" />
                ) : (
                    <Terminal size={10} className="text-primary" />
                )}
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                    {statusLine}
                </span>
            </div>

            {/* Main Input Group */}
            <div className="relative group">
                <div className="absolute inset-0 bg-primary/5 rounded-2xl blur-xl group-focus-within:bg-primary/10 transition-all" />

                <div className={cn(
                    "relative flex items-center gap-3 bg-card border rounded-xl px-4 py-2 shadow-2xl focus-within:border-primary/50 transition-all",
                    isMicActive
                        ? "border-red-500/60 shadow-red-500/20 shadow-lg"
                        : "border-border"
                )}>
                    <button
                        onClick={onMicToggle}
                        className={cn(
                            "p-2 rounded-lg transition-colors shrink-0",
                            isMicActive
                                ? "bg-primary/20 text-primary animate-pulse"
                                : "hover:bg-muted text-muted-foreground"
                        )}
                    >
                        <Mic size={18} />
                    </button>

                    <div className="flex-1 min-w-0 flex items-center gap-2">
                        <span className={cn(
                            "font-mono font-bold text-sm",
                            input.startsWith("/") ? "text-primary" : "text-primary/40"
                        )}>/</span>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={placeholder}
                            disabled={isCreating}
                            className="w-full bg-transparent border-none py-2 text-sm focus:outline-none placeholder:text-muted-foreground/50 font-medium disabled:opacity-50"
                        />
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                        <button
                            onClick={() => setIsAutopilot((prev) => !prev)}
                            className={cn(
                                "hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md border transition-all cursor-pointer",
                                isAutopilot
                                    ? "bg-primary/20 border-primary/40 text-primary"
                                    : "bg-muted/50 border-border text-muted-foreground hover:bg-muted"
                            )}
                        >
                            <Zap size={12} className={isAutopilot ? "text-primary" : ""} />
                            <span className="text-[10px] font-bold uppercase">AUTOPILOT</span>
                        </button>

                        <button
                            onClick={handleSend}
                            disabled={isCreating}
                            className="p-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
                        >
                            {isCreating ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
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
