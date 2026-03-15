import React, { useState } from "react";
import { ExternalLink, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { Evidence } from "@/types/mission";
import { usePulseOnUpdate } from "@/hooks/usePulseOnUpdate";
import { ExpandableCard } from "@/components/ui/ExpandableCard";
import { toast } from "@/hooks/useToast";

interface EvidenceCardProps {
    item: Evidence;
}

export function EvidenceCardV2({ item }: EvidenceCardProps) {
    const [isOpen, setIsOpen] = useState(false);
    const isPulsing = usePulseOnUpdate(item.createdAt);

    const handleCopy = (e: React.MouseEvent) => {
        e.stopPropagation();
        const text = `
${item.title}
${item.summary}
Confidence: ${Math.round(item.confidence * 100)}%
Sources: ${item.sources.map(s => new URL(s.url).hostname).join(", ")}
Timestamp: ${item.createdAt}
    `.trim();

        navigator.clipboard.writeText(text)
            .then(() => toast.success("Copied finding"))
            .catch(() => toast.error("Copy failed"));
    };

    const header = (
        <div className="w-full relative">
            {/* Header: tags & Copy button */}
            <div className="flex items-start justify-between mb-3 gap-8">
                <div className="flex flex-wrap gap-1">
                    {item.tags.map(t => (
                        <span key={t} className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-muted/50 text-muted-foreground border border-border uppercase">
                            {t}
                        </span>
                    ))}
                </div>
                <button
                    onClick={handleCopy}
                    aria-label="Copy finding"
                    className="p-1.5 rounded-lg bg-secondary/50 border border-border text-muted-foreground hover:text-primary transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
                >
                    <Copy size={12} />
                </button>
            </div>

            <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                    <h3 className="text-sm font-bold mb-2 group-hover:text-primary transition-colors">
                        {item.title}
                    </h3>
                    <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                        {item.summary}
                    </p>
                </div>

                {/* Confidence Meter */}
                <div className="flex items-center gap-2 shrink-0">
                    <div className="flex flex-col items-end">
                        <span className="text-[8px] font-bold text-muted-foreground tracking-tighter leading-none">CONF</span>
                        <span className={cn(
                            "text-[10px] font-mono font-bold leading-normal",
                            item.confidence > 0.9 ? "text-active" : item.confidence > 0.7 ? "text-browsing" : "text-failed"
                        )}>
                            {Math.round(item.confidence * 100)}%
                        </span>
                    </div>
                    <div className="w-1 h-8 rounded-full bg-secondary overflow-hidden">
                        <div
                            className={cn(
                                "w-full rounded-full transition-all",
                                item.confidence > 0.9 ? "bg-active" : item.confidence > 0.7 ? "bg-browsing" : "bg-failed"
                            )}
                            style={{ height: `${item.confidence * 100}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Source Favicons/Domains Preview */}
            <div className="mt-3 flex items-center gap-3">
                {item.sources.slice(0, 2).map((s, i) => (
                    <div key={i} className="flex items-center gap-1 text-[9px] text-muted-foreground opacity-60">
                        <ExternalLink size={8} />
                        <span className="truncate max-w-[80px]">{new URL(s.url).hostname}</span>
                    </div>
                ))}
            </div>
        </div>
    );

    return (
        <ExpandableCard
            isOpen={isOpen}
            onToggle={() => setIsOpen(!isOpen)}
            header={header}
            isPulsing={isPulsing}
            headerClassName="p-4"
        >
            <div className="mt-4 space-y-4">
                <div className="space-y-2">
                    <span className="text-[9px] font-bold text-muted-foreground tracking-widest uppercase">Supporting Snippets</span>
                    <div className="space-y-2">
                        {item.snippets.map((s, i) => (
                            <div key={i} className="p-2.5 rounded-lg bg-muted/40 border-l-2 border-primary/40 text-[11px] italic text-muted-foreground leading-relaxed">
                                "{s}"
                            </div>
                        ))}
                    </div>
                </div>

                <div className="space-y-2">
                    <span className="text-[9px] font-bold text-muted-foreground tracking-widest uppercase">Full Sources</span>
                    <div className="grid gap-2">
                        {item.sources.map((s, i) => (
                            <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-secondary/30 border border-border/40 group/s">
                                <div className="flex flex-col min-w-0">
                                    <span className="text-[10px] font-bold text-foreground truncate">{s.title}</span>
                                    <span className="text-[9px] text-muted-foreground font-mono truncate">{s.url}</span>
                                </div>
                                <a
                                    href={s.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-1 px-2 rounded-md bg-background border border-border text-[9px] font-bold text-muted-foreground hover:text-primary transition-all ml-4"
                                >
                                    VISIT
                                </a>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </ExpandableCard>
    );
}
