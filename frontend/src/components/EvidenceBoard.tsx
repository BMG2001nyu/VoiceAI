import { useState } from "react";
import { useMissionStore } from "../store";
import { EvidenceCard } from "./EvidenceCard";

export function EvidenceBoard() {
  const evidence = useMissionStore((s) => s.evidence);
  const [activeTheme, setActiveTheme] = useState<string | null>(null);

  const themes = Array.from(
    new Set(evidence.map((e) => e.theme).filter(Boolean) as string[])
  );

  const filtered = activeTheme
    ? evidence.filter((e) => e.theme === activeTheme)
    : evidence;

  return (
    <div className="flex flex-col h-full">
      {/* Section header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1e293b] shrink-0">
        <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-text-secondary">
          Evidence Board
        </span>
        <span className="text-[11px] font-mono text-text-secondary">
          {filtered.length} finding{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Theme filter pills */}
      {themes.length > 0 && (
        <div className="flex items-center gap-1.5 px-3 py-2 border-b border-[#1e293b] shrink-0 flex-wrap">
          <button
            onClick={() => setActiveTheme(null)}
            className={`px-2 py-0.5 rounded-full text-[10px] font-mono border transition-colors ${
              activeTheme === null
                ? "bg-slate-700 text-white border-slate-600"
                : "text-slate-500 border-slate-800 hover:border-slate-600"
            }`}
          >
            All
          </button>
          {themes.map((t) => (
            <button
              key={t}
              onClick={() => setActiveTheme(t === activeTheme ? null : t)}
              className={`px-2 py-0.5 rounded-full text-[10px] font-mono border transition-colors ${
                activeTheme === t
                  ? "bg-blue-900/60 text-accent-blue border-accent-blue/40"
                  : "text-slate-500 border-slate-800 hover:border-slate-600"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {/* Cards */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 flex flex-col gap-2.5">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-secondary text-xs font-mono gap-2 opacity-40">
            <span>No findings yet</span>
            <span className="text-[10px]">Agents are gathering intelligence…</span>
          </div>
        ) : (
          filtered.map((ev) => <EvidenceCard key={ev.id} evidence={ev} />)
        )}
      </div>
    </div>
  );
}
