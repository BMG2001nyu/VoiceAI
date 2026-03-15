import { useRef, useEffect, useCallback } from "react";
import { useMissionStore } from "../store";
import type {
  MissionRecord,
  AgentState,
  EvidenceRecord,
  TimelineEvent,
  TranscriptEntry,
} from "../types/api";

interface WSMessage {
  type: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: any;
}

const FLUSH_INTERVAL_MS = 150;
const BURST_THRESHOLD = 100;

/**
 * Batched WebSocket event dispatcher.
 *
 * Collects incoming WS messages in a queue and flushes them to the Zustand
 * store every 150ms. Collapses duplicate AGENT_UPDATE events (same agent_id)
 * and applies rate limiting during bursts.
 */
export function useThrottledStore() {
  const queueRef = useRef<WSMessage[]>([]);
  const store = useMissionStore();

  const enqueue = useCallback(
    (msg: WSMessage) => {
      // MISSION_STATUS is critical — dispatch immediately, never queue
      if (msg.type === "MISSION_STATUS") {
        store.setMission(msg.payload as MissionRecord);
        return;
      }
      queueRef.current.push(msg);
    },
    [store],
  );

  useEffect(() => {
    const interval = setInterval(() => {
      const queue = queueRef.current;
      if (queue.length === 0) return;

      // Drain the queue (immutable swap)
      const batch = [...queue];
      queueRef.current = [];

      const isBurst = batch.length > BURST_THRESHOLD;

      // Collapse AGENT_UPDATE: keep only latest per agent_id
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const agentUpdates = new Map<string, any>();
      const otherEvents: WSMessage[] = [];

      for (const msg of batch) {
        if (msg.type === "AGENT_UPDATE") {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const p = msg.payload as any;
          const agentId = p?.agent_id ?? p?.id;
          if (agentId) {
            agentUpdates.set(agentId, {
              ...agentUpdates.get(agentId),
              ...msg.payload,
            });
          }
        } else {
          otherEvents.push(msg);
        }
      }

      // Always dispatch collapsed agent updates
      for (const payload of agentUpdates.values()) {
        store.updateAgent(payload as Partial<AgentState> & { agent_id: string });
      }

      // Dispatch other events (skip EVIDENCE_FOUND during burst)
      for (const msg of otherEvents) {
        if (isBurst && msg.type === "EVIDENCE_FOUND") {
          continue; // Drop during burst to protect UI
        }

        switch (msg.type) {
          case "EVIDENCE_FOUND": {
            const evidence = msg.payload?.evidence || msg.payload;
            if (evidence) store.addEvidence(evidence as EvidenceRecord);
            break;
          }
          case "TIMELINE_EVENT":
            store.addTimelineEvent(msg.payload as TimelineEvent);
            break;
          case "VOICE_TRANSCRIPT":
            store.addTranscriptEntry(msg.payload as TranscriptEntry);
            break;
        }
      }
    }, FLUSH_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [store]);

  return { enqueue };
}
