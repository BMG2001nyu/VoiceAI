import { clsx } from "clsx";
import type { AgentStatus } from "../types/api";

interface StatusBadgeProps {
  status: AgentStatus;
}

const STATUS_CONFIG: Record<
  AgentStatus,
  { label: string; className: string; pulse: boolean }
> = {
  IDLE: {
    label: "Idle",
    className: "bg-slate-800 text-slate-400 border-slate-700",
    pulse: false,
  },
  ASSIGNED: {
    label: "Assigned",
    className: "bg-amber-900/40 text-accent-amber border-accent-amber/40",
    pulse: false,
  },
  BROWSING: {
    label: "Browsing",
    className: "bg-blue-900/40 text-accent-blue border-accent-blue/40",
    pulse: true,
  },
  REPORTING: {
    label: "Reporting",
    className: "bg-green-900/40 text-accent-green border-accent-green/40",
    pulse: false,
  },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono font-medium border",
        config.className
      )}
    >
      <span
        className={clsx("w-1.5 h-1.5 rounded-full", {
          "bg-slate-400": status === "IDLE",
          "bg-accent-amber": status === "ASSIGNED",
          "bg-accent-blue animate-pulse": status === "BROWSING",
          "bg-accent-green": status === "REPORTING",
        })}
      />
      {config.label}
    </span>
  );
}
