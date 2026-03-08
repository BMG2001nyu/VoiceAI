import { ExternalLink } from "lucide-react";
import { clsx } from "clsx";
import type { EvidenceRecord } from "../types/api";

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 rounded-full bg-slate-800 overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all", {
            "bg-accent-green": value >= 0.8,
            "bg-accent-amber": value >= 0.6 && value < 0.8,
            "bg-accent-red": value < 0.6,
          })}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={clsx("text-[10px] font-mono font-semibold shrink-0", {
          "text-accent-green": value >= 0.8,
          "text-accent-amber": value >= 0.6 && value < 0.8,
          "text-accent-red": value < 0.6,
        })}
      >
        {pct}%
      </span>
    </div>
  );
}

interface EvidenceCardProps {
  evidence: EvidenceRecord;
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  const relTime = formatRelTime(evidence.created_at);

  return (
    <div className="bg-surface border border-[#1e293b] rounded-lg p-3 flex flex-col gap-2 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        {evidence.theme && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-blue-900/30 text-accent-blue border border-accent-blue/20">
            {evidence.theme}
          </span>
        )}
        <span className="text-[10px] text-slate-600 font-mono ml-auto shrink-0">
          {relTime}
        </span>
      </div>

      {/* Claim */}
      <p className="text-sm font-medium text-text-primary leading-snug">
        {evidence.claim}
      </p>

      {/* Summary */}
      <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
        {evidence.summary}
      </p>

      {/* Confidence */}
      <ConfidenceMeter value={evidence.confidence} />

      {/* Footer */}
      <a
        href={evidence.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1 text-[11px] text-accent-blue hover:underline font-mono truncate"
      >
        <ExternalLink size={10} />
        <span className="truncate">{evidence.source_url}</span>
      </a>
    </div>
  );
}

function formatRelTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}
