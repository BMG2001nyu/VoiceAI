import { useCallback, useEffect, useRef } from "react";
import { useMissionStore } from "../store";
import { useThrottledStore } from "./useThrottledStore";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export function useWebSocket(missionId: string | null) {
  const wsMissionRef = useRef<WebSocket | null>(null);
  const wsVoiceRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const connectionStatusRef = useRef<string>("closed");
  const { setConnectionStatus } = useMissionStore();
  const { enqueue } = useThrottledStore();

  const connectMission = useCallback(() => {
    if (!missionId) return;

    if (connectionStatusRef.current !== "connecting") {
      connectionStatusRef.current = "connecting";
      setConnectionStatus("connecting");
    }

    const ws = new WebSocket(`${WS_URL}/ws/mission/${missionId}`);
    wsMissionRef.current = ws;

    ws.onopen = () => {
      attemptsRef.current = 0;
      if (connectionStatusRef.current !== "open") {
        connectionStatusRef.current = "open";
        setConnectionStatus("open");
      }
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        enqueue(msg);
      } catch (err) {
        console.error("Failed to parse mission message:", err);
      }
    };

    ws.onerror = () => {
      if (connectionStatusRef.current !== "error") {
        connectionStatusRef.current = "error";
        setConnectionStatus("error");
      }
    };

    ws.onclose = () => {
      if (connectionStatusRef.current !== "closed") {
        connectionStatusRef.current = "closed";
        setConnectionStatus("closed");
      }
      const delay =
        Math.min(1000 * 2 ** attemptsRef.current, 30_000) +
        Math.random() * 500;
      attemptsRef.current++;
      setTimeout(connectMission, delay);
    };
  }, [missionId, setConnectionStatus, enqueue]);

  const connectVoice = useCallback(() => {
    const ws = new WebSocket(`${WS_URL}/ws/voice`);
    wsVoiceRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "start" }));
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        enqueue(msg);
      } catch (err) {
        console.error("Failed to parse voice message:", err);
      }
    };

    ws.onclose = () => {
      // Reconnect voice after 2s if it drops
      setTimeout(connectVoice, 2000);
    };
  }, [enqueue]);

  useEffect(() => {
    connectMission();
    connectVoice();

    return () => {
      wsMissionRef.current?.close();
      if (wsVoiceRef.current?.readyState === WebSocket.OPEN) {
        wsVoiceRef.current.send(JSON.stringify({ type: "stop" }));
      }
      wsVoiceRef.current?.close();
    };
  }, [connectMission, connectVoice]);
}
