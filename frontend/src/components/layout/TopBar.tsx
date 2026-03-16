import React from "react";
import { Cpu, Pause, Play, RotateCcw, Share2, Settings, User, Radio, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";
import { Mission } from "@/types/mission";
import { toast } from "@/hooks/useToast";
import type { AppMode } from "@/App";

interface TopBarProps {
    mission: Mission;
    isPaused: boolean;
    onPause: () => void;
    onReset: () => void;
    mode?: AppMode;
    onModeToggle?: () => void;
    isConnected?: boolean;
}

export function TopBar({ mission, isPaused, onPause, onReset, mode = "demo", onModeToggle, isConnected = false }: TopBarProps) {
    const handleShare = () => {
        const url = `${window.location.origin}/mission/${mission.id}`;
        navigator.clipboard.writeText(url).then(() => {
            toast.success("Mission URL copied to clipboard");
        }).catch(() => {
            toast.error("Failed to copy URL");
        });
    };

    const handleSettings = () => {
        toast.show("Settings coming soon", "info");
    };

    return (
        <header className="fixed top-0 left-0 right-0 h-14 border-b border-border bg-background/80 backdrop-blur-md z-50 flex items-center justify-between px-4">
            {/* Left: Brand & Status */}
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                        <Cpu size={18} />
                    </div>
                    <span className="font-bold text-sm tracking-tight hidden sm:inline-block">MISSION CONTROL</span>
                </div>

                <div className="h-4 w-px bg-border mx-1" />

                <div className="flex items-center gap-2">
                    <div className={cn(
                        "px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase",
                        isPaused
                            ? "bg-yellow-500/10 text-yellow-500"
                            : mission.status === "ACTIVE" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                    )}>
                        {isPaused ? "PAUSED" : mission.status}
                    </div>
                    {!isPaused && (
                        <div className="flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest">LIVE</span>
                        </div>
                    )}
                </div>

                <div className="h-4 w-px bg-border mx-1" />

                {/* Mode Toggle */}
                <button
                    onClick={onModeToggle}
                    className={cn(
                        "flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer",
                        mode === "live"
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-500"
                            : "bg-muted/50 border-border text-muted-foreground hover:bg-muted"
                    )}
                    title={mode === "demo" ? "Switch to live backend mode" : "Switch to demo mode"}
                >
                    {mode === "live" ? <Radio size={10} /> : <Monitor size={10} />}
                    {mode === "live" ? "LIVE" : "DEMO"}
                </button>

                {mode === "live" && (
                    <div className="flex items-center gap-1.5">
                        <div className={cn(
                            "w-1.5 h-1.5 rounded-full",
                            isConnected ? "bg-emerald-500" : "bg-red-500"
                        )} />
                        <span className="text-[10px] font-mono text-muted-foreground">
                            {isConnected ? "WS OK" : "WS OFF"}
                        </span>
                    </div>
                )}
            </div>

            {/* Center: Mission Info */}
            <div className="hidden md:flex flex-col items-center max-w-xl flex-1 px-8">
                <h1 className="text-sm font-semibold truncate w-full text-center">
                    {mission.title}
                </h1>
                <p className="text-[11px] text-muted-foreground truncate w-full text-center">
                    {mission.summary}
                </p>
            </div>

            {/* Right: Controls */}
            <div className="flex items-center gap-2">
                <div className="flex items-center bg-muted/50 rounded-lg p-0.5 border border-border">
                    <button
                        onClick={onPause}
                        className="p-1.5 rounded-md hover:bg-background text-muted-foreground transition-all"
                        title={isPaused ? "Resume mission" : "Pause mission"}
                    >
                        {isPaused ? <Play size={14} /> : <Pause size={14} />}
                    </button>
                    <button
                        onClick={onReset}
                        className="p-1.5 rounded-md hover:bg-background text-muted-foreground transition-all"
                        title="Reset mission"
                    >
                        <RotateCcw size={14} />
                    </button>
                </div>

                <button
                    onClick={handleShare}
                    className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition-colors"
                    title="Share mission"
                >
                    <Share2 size={16} />
                </button>
                <button
                    onClick={handleSettings}
                    className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition-colors"
                    title="Settings"
                >
                    <Settings size={16} />
                </button>

                <div className="h-6 w-px bg-border mx-1" />

                <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center text-muted-foreground border border-border overflow-hidden">
                    <User size={16} />
                </div>
            </div>
        </header>
    );
}
