import { Globe, Bot } from "lucide-react";
import { clsx } from "clsx";
import { StatusBadge } from "./StatusBadge";
import type { AgentState, AgentType } from "../types/api";
import { motion, AnimatePresence } from "framer-motion";

const AGENT_TYPE_LABELS: Record<AgentType, string> = {
  OFFICIAL_SITE: "Official Site",
  NEWS_BLOG: "News & Blog",
  REDDIT_HN: "Reddit / HN",
  GITHUB: "GitHub",
  FINANCIAL: "Financial",
  RECENT_NEWS: "Recent News",
};

interface AgentTileProps {
  agent: AgentState;
}

export function AgentTile({ agent }: AgentTileProps) {
  const isActive = agent.status === "BROWSING" || agent.status === "REPORTING";

  return (
    <motion.div
      layout
      className={clsx(
        "rounded-lg p-3 flex flex-col gap-2 border transition-colors duration-300",
        "bg-surface",
        {
          "border-accent-blue/30": agent.status === "BROWSING",
          "border-accent-green/30": agent.status === "REPORTING",
          "border-accent-amber/30": agent.status === "ASSIGNED",
          "border-[#1e293b]": agent.status === "IDLE",
        }
      )}
      animate={{
        scale: isActive ? 1.02 : 1,
        borderColor:
          agent.status === "BROWSING" ? "rgba(59, 130, 246, 0.4)" :
            agent.status === "REPORTING" ? "rgba(34, 197, 94, 0.4)" :
              agent.status === "ASSIGNED" ? "rgba(245, 158, 11, 0.4)" :
                "#1e293b"
      }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      {/* Top row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Bot
            size={13}
            className={clsx({
              "text-accent-blue": agent.status === "BROWSING",
              "text-accent-green": agent.status === "REPORTING",
              "text-accent-amber": agent.status === "ASSIGNED",
              "text-slate-500": agent.status === "IDLE",
            })}
          />
          <span className="font-mono text-xs text-text-secondary truncate">
            {agent.agent_id}
          </span>
          {agent.task_type && (
            <span className="text-[10px] text-slate-600 font-mono shrink-0">
              {AGENT_TYPE_LABELS[agent.task_type]}
            </span>
          )}
        </div>
        <StatusBadge status={agent.status} />
      </div>

      {/* Objective */}
      <p
        className={clsx("text-xs leading-snug line-clamp-2", {
          "text-text-primary": isActive,
          "text-text-secondary": !isActive,
        })}
      >
        {agent.objective ?? "Awaiting assignment…"}
      </p>

      {/* Footer */}
      <div className="flex items-center gap-1.5 mt-auto">
        {agent.site_url ? (
          <>
            <Globe size={11} className="text-accent-blue shrink-0" />
            <span className="text-[11px] font-mono text-accent-blue truncate">
              {agent.site_url}
            </span>
          </>
        ) : (
          <span className="text-[11px] text-slate-700 font-mono">—</span>
        )}
      </div>

      {/* Scanning placeholder when active */}
      <AnimatePresence>
        {isActive && !agent.screenshot_url && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 64 }}
            exit={{ opacity: 0, height: 0 }}
            className="rounded bg-slate-900 border border-[#1e293b] overflow-hidden relative"
          >
            <motion.div
              className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-accent-blue to-transparent opacity-60"
              animate={{ top: ["0%", "100%", "0%"] }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[10px] text-slate-700 font-mono">
                scanning…
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
