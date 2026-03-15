import React, { useState } from "react";
import { Search, Info, LayoutGrid, List } from "lucide-react";
import { cn } from "@/lib/utils";
import { Evidence } from "@/types/mission";
import { EvidenceCardV2 } from "./EvidenceCardV2";

interface EvidenceBoardProps {
    evidence: Evidence[];
}

export function EvidenceBoardV2({ evidence }: EvidenceBoardProps) {
    const [activeTab, setActiveTab] = useState<string>("ALL");
    const [viewMode, setViewMode] = useState<"GRID" | "LIST">("LIST");
    const [sortBy, setSortBy] = useState<"NEWEST" | "CONFIDENCE">("NEWEST");

    const tags = ["ALL", ...Array.from(new Set(evidence.flatMap(e => e.tags)))];

    const filteredEvidence = evidence
        .filter(e => activeTab === "ALL" || e.tags.includes(activeTab))
        .sort((a, b) => {
            if (sortBy === "CONFIDENCE") return b.confidence - a.confidence;
            return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        });

    return (
        <div className="flex-1 flex flex-col min-h-0">
            {/* Header */}
            <div className="p-4 border-b border-border flex flex-col gap-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Evidence Board</h2>
                        <div className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground text-[10px] font-mono">
                            {filteredEvidence.length} FINDINGS
                        </div>
                    </div>
                    <div className="flex items-center bg-muted/50 rounded-lg p-0.5 border border-border">
                        <button
                            onClick={() => setViewMode("GRID")}
                            className={cn("p-1.5 rounded-md transition-all", viewMode === "GRID" ? "bg-background text-primary shadow-sm" : "text-muted-foreground")}
                        >
                            <LayoutGrid size={12} />
                        </button>
                        <button
                            onClick={() => setViewMode("LIST")}
                            className={cn("p-1.5 rounded-md transition-all", viewMode === "LIST" ? "bg-background text-primary shadow-sm" : "text-muted-foreground")}
                        >
                            <List size={12} />
                        </button>
                    </div>
                </div>

                <div className="flex items-center justify-between gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" size={12} />
                        <input
                            type="text"
                            placeholder="Search evidence..."
                            className="w-full bg-muted/30 border border-border rounded-lg py-1.5 pl-8 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all font-mono"
                        />
                    </div>
                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as "NEWEST" | "CONFIDENCE")}
                        className="bg-muted/30 border border-border rounded-lg py-1.5 px-2 text-[10px] font-bold text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all cursor-pointer outline-none"
                    >
                        <option value="NEWEST">NEWEST</option>
                        <option value="CONFIDENCE">CONFIDENCE</option>
                    </select>
                </div>
            </div>

            {/* Tabs */}
            <div className="px-4 py-2 border-b border-border flex items-center gap-1.5 overflow-x-auto scrollbar-none">
                {tags.map((tag) => (
                    <button
                        key={tag}
                        onClick={() => setActiveTab(tag)}
                        className={cn(
                            "px-2.5 py-1 rounded-md text-[10px] font-bold uppercase transition-all shrink-0",
                            activeTab === tag
                                ? "bg-primary/10 text-primary border border-primary/20"
                                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                        )}
                    >
                        {tag}
                    </button>
                ))}
            </div>

            {/* Evidence Cards List */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 scrollbar-thin">
                {filteredEvidence.length > 0 ? filteredEvidence.map((item) => (
                    <EvidenceCardV2 key={item.id} item={item} />
                )) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-center p-8 opacity-40">
                        <Info size={32} className="mb-4 text-muted-foreground" />
                        <p className="text-sm font-medium">Agents are gathering sources...</p>
                        <p className="text-xs text-muted-foreground">No evidence found for this filter yet.</p>
                    </div>
                )}
            </div>

            {/* Synthesis Trigger */}
            <div className="p-4 border-t border-border bg-card/20">
                <button className="w-full py-2 bg-primary text-primary-foreground rounded-lg text-xs font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-opacity">
                    <span>SYNTHESIZE INTELLIGENCE</span>
                </button>
            </div>
        </div>
    );
}
