import React from "react";
import { Cpu, Pause, RotateCcw, Share2, Settings, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { Mission } from "@/types/mission";

interface TopBarProps {
    mission: Mission;
}

export function TopBar({ mission }: TopBarProps) {
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
                        mission.status === "ACTIVE" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                    )}>
                        {mission.status}
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest">LIVE</span>
                    </div>
                </div>
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
                    <button className="p-1.5 rounded-md hover:bg-background text-muted-foreground transition-all">
                        <Pause size={14} />
                    </button>
                    <button className="p-1.5 rounded-md hover:bg-background text-muted-foreground transition-all">
                        <RotateCcw size={14} />
                    </button>
                </div>

                <button className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition-colors">
                    <Share2 size={16} />
                </button>
                <button className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition-colors">
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
