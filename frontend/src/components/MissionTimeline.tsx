import {
  Bot,
  FileText,
  ArrowRight,
  AlertTriangle,
  Sparkles,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { clsx } from "clsx";
import { useMissionStore } from "../store";
import type { TimelineEventType } from "../types/api";

type IconProps = { size?: number; className?: string };

const EVENT_CONFIG: Record<
  TimelineEventType,
  { Icon: React.ComponentType<IconProps>; color: string }
> = {
  agent_assigned: { Icon: Bot, color: "text-accent-amber" },
  evidence_found: { Icon: FileText, color: "text-accent-green" },
  agent_redirected: { Icon: ArrowRight, color: "text-accent-blue" },
  agent_timeout: { Icon: AlertTriangle, color: "text-accent-red" },
  synthesis_start: { Icon: Sparkles, color: "text-accent-purple" },
  mission_complete: { Icon: CheckCircle, color: "text-accent-green" },
  contradiction_detected: { Icon: AlertCircle, color: "text-accent-red" },
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function MissionTimeline() {
  const timeline = useMissionStore((s) => s.timeline);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-[#1e293b] shrink-0">
        <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-text-secondary">
          Mission Timeline
        </span>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-3 py-2 flex flex-col gap-1.5">
        {timeline.map((event) => {
          const config = EVENT_CONFIG[event.type];
          return (
            <div
              key={event.id}
              className="flex items-start gap-2 animate-fade-in"
            >
              <span className="text-[10px] font-mono text-slate-600 shrink-0 w-16 pt-px">
                {formatTime(event.timestamp)}
              </span>
              <config.Icon
                size={12}
                className={clsx("shrink-0 mt-0.5", config.color)}
              />
              <span className="text-[11px] text-text-secondary leading-snug">
                {event.description}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
