import { Radio, Cpu, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import { useEffect } from "react";
import { useMissionStore } from "../../store";
import type { ConnectionStatus, MissionStatus } from "../../types/api";

function ConnectionDot({ status }: { status: ConnectionStatus }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={clsx("w-2 h-2 rounded-full", {
          "bg-accent-green animate-pulse": status === "open",
          "bg-accent-amber animate-pulse": status === "connecting",
          "bg-accent-red": status === "error" || status === "closed",
        })}
      />
      <span className="text-text-secondary text-xs font-mono uppercase tracking-wider">
        {status === "open" ? "Live" : status === "connecting" ? "Connecting" : "Offline"}
      </span>
    </div>
  );
}

function MissionStatusBadge({ status }: { status: MissionStatus }) {
  const label: Record<MissionStatus, string> = {
    PENDING: "Pending",
    ACTIVE: "Active",
    SYNTHESIZING: "Synthesizing",
    COMPLETE: "Complete",
    FAILED: "Failed",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-medium uppercase tracking-wider",
        {
          "bg-slate-800 text-slate-400": status === "PENDING",
          "bg-green-900/40 text-accent-green border border-accent-green/30":
            status === "ACTIVE",
          "bg-purple-900/40 text-accent-purple border border-accent-purple/30":
            status === "SYNTHESIZING",
          "bg-green-900/60 text-accent-green border border-accent-green/50":
            status === "COMPLETE",
          "bg-red-900/40 text-accent-red border border-accent-red/30":
            status === "FAILED",
        }
      )}
    >
      {status === "ACTIVE" && (
        <span className="w-1.5 h-1.5 rounded-full bg-accent-green mr-1.5 animate-pulse" />
      )}
      {label[status]}
    </span>
  );
}

export function Header() {
  const { mission, connectionStatus, dlqCount, setDlqCount } = useMissionStore();

  useEffect(() => {
    const pollDlq = async () => {
      try {
        const resp = await fetch("/api/internal/dlq/count");
        if (resp.ok) {
          const data = await resp.json();
          setDlqCount(data.count);
        }
      } catch (err) {
        // Silently fail polling
      }
    };

    const interval = setInterval(pollDlq, 10000);
    pollDlq();
    return () => clearInterval(interval);
  }, [setDlqCount]);

  return (
    <header className="border-b border-[#1e293b] flex items-center justify-between px-6 h-12 shrink-0 relative z-10">
      {/* Left — brand */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-accent-green">
          <Cpu size={16} strokeWidth={1.5} />
          <span className="font-mono font-semibold text-sm tracking-widest uppercase text-accent-green">
            Mission Control
          </span>
        </div>

        <div className="w-px h-4 bg-[#1e293b]" />

        {mission && (
          <div className="flex items-center gap-2">
            <span className="text-text-secondary text-xs font-mono truncate max-w-[340px]">
              {mission.objective.length > 60
                ? mission.objective.slice(0, 60) + "…"
                : mission.objective}
            </span>
            <MissionStatusBadge status={mission.status} />
          </div>
        )}
      </div>

      {/* Right — system status */}
      <div className="flex items-center gap-5">
        <button
          className={clsx(
            "flex items-center gap-1.5 transition-colors text-xs",
            dlqCount > 0
              ? "text-accent-amber animate-pulse"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          <AlertTriangle size={13} />
          <span className="font-mono">
            {dlqCount} {dlqCount === 1 ? "retry" : "retries"}
          </span>
        </button>

        <div className="flex items-center gap-1.5 text-text-secondary">
          <Radio size={13} />
          <ConnectionDot status={connectionStatus} />
        </div>
      </div>
    </header>
  );
}
