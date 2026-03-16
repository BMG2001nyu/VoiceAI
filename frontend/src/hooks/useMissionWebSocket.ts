import { useEffect, useRef, useCallback } from "react";
import { useLiveMissionStore } from "../store/missionStore";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const MAX_RECONNECT_DELAY_MS = 30_000;

/**
 * Connects to /ws/mission/{id} when missionId is set in the live mission store.
 * Dispatches incoming events to the store's handlers.
 * Reconnects with exponential backoff + jitter on disconnect.
 */
export function useMissionWebSocket(): void {
  const missionId = useLiveMissionStore((s) => s.missionId);
  const setConnected = useLiveMissionStore((s) => s.setConnected);
  const handleMissionStatus = useLiveMissionStore((s) => s.handleMissionStatus);
  const handleAgentUpdate = useLiveMissionStore((s) => s.handleAgentUpdate);
  const handleEvidenceFound = useLiveMissionStore((s) => s.handleEvidenceFound);
  const handleTimelineEvent = useLiveMissionStore((s) => s.handleTimelineEvent);

  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const closedIntentionallyRef = useRef(false);

  const connect = useCallback(() => {
    if (!missionId) return;

    closedIntentionallyRef.current = false;
    const ws = new WebSocket(`${WS_URL}/ws/mission/${missionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      attemptsRef.current = 0;
      setConnected(true);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        switch (msg.type) {
          case "MISSION_STATUS":
            handleMissionStatus(msg.payload);
            break;
          case "AGENT_UPDATE":
            handleAgentUpdate(msg.payload);
            break;
          case "EVIDENCE_FOUND":
            handleEvidenceFound(msg.payload);
            break;
          case "TIMELINE_EVENT":
            handleTimelineEvent(msg.payload);
            break;
          default:
            // Unknown message type — ignore silently
            break;
        }
      } catch (err) {
        console.error("[useMissionWebSocket] Failed to parse message:", err);
      }
    };

    ws.onerror = () => {
      setConnected(false);
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;

      if (closedIntentionallyRef.current) return;

      // Exponential backoff with jitter
      const delay =
        Math.min(1000 * 2 ** attemptsRef.current, MAX_RECONNECT_DELAY_MS) +
        Math.random() * 500;
      attemptsRef.current += 1;
      setTimeout(connect, delay);
    };
  }, [
    missionId,
    setConnected,
    handleMissionStatus,
    handleAgentUpdate,
    handleEvidenceFound,
    handleTimelineEvent,
  ]);

  useEffect(() => {
    if (!missionId) return;

    connect();

    return () => {
      closedIntentionallyRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
      setConnected(false);
    };
  }, [missionId, connect, setConnected]);
}
