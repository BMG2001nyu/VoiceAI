import { useCallback, useEffect, useRef } from "react";
import { useMissionStore } from "../store";
import { useThrottledDispatch } from "./useThrottledStore";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export function useWebSocket(missionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const setConnectionStatus = useMissionStore((s) => s.setConnectionStatus);
  const enqueue = useThrottledDispatch();

  const connect = useCallback(() => {
    if (!missionId) return;

    setConnectionStatus("connecting");
    const ws = new WebSocket(`${WS_URL}/ws/mission/${missionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      attemptsRef.current = 0;
      setConnectionStatus("open");
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        enqueue(msg);
      } catch {
        // malformed message — ignore
      }
    };

    ws.onerror = () => setConnectionStatus("error");

    ws.onclose = () => {
      setConnectionStatus("closed");
      const delay =
        Math.min(1000 * 2 ** attemptsRef.current, 30_000) +
        Math.random() * 500;
      attemptsRef.current++;
      setTimeout(connect, delay);
    };
  }, [missionId, setConnectionStatus, enqueue]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);
}
