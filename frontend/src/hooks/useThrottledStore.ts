import { useEffect, useRef, useCallback } from "react";
import { useMissionStore } from "../store";

/**
 * useThrottledStore
 * Batches incoming WebSocket events and flushes them to the Zustand store
 * every 150ms to maintain 60fps UI performance during bursts.
 */
export function useThrottledStore() {
    const store = useMissionStore();
    const queueRef = useRef<any[]>([]);

    const flush = useCallback(() => {
        if (queueRef.current.length === 0) return;

        // Grab the current batch and clear the queue
        const batch = [...queueRef.current];
        queueRef.current = [];

        // 1. Collapse AGENT_UPDATEs (only keep latest per agent_id)
        const agentUpdates = new Map<string, any>();
        const otherEvents: any[] = [];

        batch.forEach((msg) => {
            if (msg.type === "AGENT_UPDATE") {
                agentUpdates.set(msg.payload.agent_id, {
                    ...agentUpdates.get(msg.payload.agent_id),
                    ...msg.payload,
                });
            } else {
                otherEvents.push(msg);
            }
        });

        // 2. Dispatch to store
        agentUpdates.forEach((update) => store.updateAgent(update));

        otherEvents.forEach((msg) => {
            switch (msg.type) {
                case "MISSION_STATUS":
                    store.setMission(msg.payload);
                    break;
                case "EVIDENCE_FOUND":
                    // The event structure often has payload.evidence or just is the payload
                    const evidence = msg.payload?.evidence || msg.payload;
                    if (evidence) store.addEvidence(evidence);
                    break;
                case "TIMELINE_EVENT":
                    store.addTimelineEvent(msg.payload);
                    break;
                case "VOICE_TRANSCRIPT":
                    store.addTranscriptEntry(msg.payload);
                    break;
                default:
                    console.warn("Unknown WS message type:", msg.type);
            }
        });
    }, [store]);

    useEffect(() => {
        const interval = setInterval(flush, 150);
        return () => clearInterval(interval);
    }, [flush]);

    const enqueue = useCallback((msg: any) => {
        queueRef.current.push(msg);
    }, []);

    return { enqueue };
}
