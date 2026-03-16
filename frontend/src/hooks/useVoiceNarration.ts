import { useEffect, useRef } from "react";
import { useLiveMissionStore } from "../store/missionStore";

const hasSpeechSynthesis =
  typeof window !== "undefined" && "speechSynthesis" in window;

/**
 * Narrates mission events aloud using the browser's SpeechSynthesis API.
 *
 * When enabled, watches the live mission store for:
 *   - New evidence (EVIDENCE_FOUND) → speaks the claim
 *   - Agent status changes (BROWSING) → announces what the agent is investigating
 *   - Mission completion → reads the briefing summary
 *
 * Uses a queue to avoid overlapping speech and drops stale utterances.
 */
export function useVoiceNarration(enabled: boolean) {
  const prevEvidenceCountRef = useRef(0);
  const prevAgentStatesRef = useRef<Record<string, string>>({});
  const prevStatusRef = useRef<string>("");
  const speechQueueRef = useRef<string[]>([]);
  const isSpeakingRef = useRef(false);

  // Process the speech queue sequentially
  const processQueue = () => {
    if (!hasSpeechSynthesis) return;
    if (isSpeakingRef.current || speechQueueRef.current.length === 0) return;

    const text = speechQueueRef.current.shift();
    if (!text) return;

    isSpeakingRef.current = true;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Pick a natural-sounding voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(
      (v) =>
        v.lang.startsWith("en") &&
        (v.name.includes("Daniel") ||
          v.name.includes("Samantha") ||
          v.name.includes("Google") ||
          v.name.includes("Microsoft"))
    );
    if (preferred) utterance.voice = preferred;

    utterance.onend = () => {
      isSpeakingRef.current = false;
      processQueue();
    };
    utterance.onerror = () => {
      isSpeakingRef.current = false;
      processQueue();
    };

    window.speechSynthesis.speak(utterance);
  };

  const speak = (text: string) => {
    if (!enabled || !hasSpeechSynthesis) return;
    // Cap queue at 5 to avoid piling up during bursts
    if (speechQueueRef.current.length < 5) {
      speechQueueRef.current.push(text);
    }
    processQueue();
  };

  // Cancel all speech when narration is disabled
  useEffect(() => {
    if (!enabled && hasSpeechSynthesis) {
      window.speechSynthesis.cancel();
      speechQueueRef.current = [];
      isSpeakingRef.current = false;
    }
  }, [enabled]);

  // Watch store for changes
  useEffect(() => {
    if (!enabled || !hasSpeechSynthesis) return;

    const unsub = useLiveMissionStore.subscribe((state) => {
      // ── New evidence ───────────────────────────────────────────
      if (state.evidence.length > prevEvidenceCountRef.current) {
        const newItems = state.evidence.slice(
          0,
          state.evidence.length - prevEvidenceCountRef.current
        );
        for (const ev of newItems) {
          const agentLabel = ev.sources?.[0]?.title
            ? `from ${ev.sources[0].title}`
            : "";
          const tagStr = ev.tags?.length ? `under ${ev.tags[0]}` : "";
          speak(`New finding ${agentLabel} ${tagStr}: ${ev.title}`);
        }
        prevEvidenceCountRef.current = state.evidence.length;
      }

      // ── Agent status changes ───────────────────────────────────
      for (const agent of state.agents) {
        const prevMode = prevAgentStatesRef.current[agent.id];
        const currentMode = agent.mode;

        if (prevMode !== currentMode) {
          if (currentMode === "Browsing" && agent.targetDomain) {
            speak(`${agent.name} is now browsing ${agent.targetDomain}`);
          } else if (currentMode === "Reporting") {
            speak(
              `${agent.name} finished research and is compiling a report`
            );
          } else if (currentMode === "Analyzing" && agent.task) {
            speak(
              `${agent.name} assigned to investigate: ${agent.task.slice(0, 80)}`
            );
          }
          prevAgentStatesRef.current[agent.id] = currentMode ?? "";
        }
      }

      // ── Mission status change ──────────────────────────────────
      if (state.status !== prevStatusRef.current) {
        if (state.status === "SYNTHESIZING") {
          speak(
            "All agents have completed their research. Synthesizing the intelligence briefing now."
          );
        } else if (state.status === "COMPLETE" && state.briefing) {
          speak("Mission complete. Here is the briefing.");
          // Split briefing into sentences for natural delivery
          const sentences = state.briefing
            .replace(/[#*_-]/g, "")
            .split(/[.!?]+/)
            .map((s) => s.trim())
            .filter((s) => s.length > 10);
          for (const sentence of sentences.slice(0, 8)) {
            speak(sentence + ".");
          }
        } else if (state.status === "COMPLETE" && !state.briefing) {
          speak("Mission complete. The briefing is available on your screen.");
        }
        prevStatusRef.current = state.status;
      }
    });

    return () => {
      unsub();
    };
  }, [enabled]);

  // Preload voices (some browsers load them asynchronously)
  useEffect(() => {
    if (!hasSpeechSynthesis) return;
    window.speechSynthesis.getVoices();
    const handleVoicesChanged = () => window.speechSynthesis.getVoices();
    window.speechSynthesis.addEventListener("voiceschanged", handleVoicesChanged);
    return () =>
      window.speechSynthesis.removeEventListener(
        "voiceschanged",
        handleVoicesChanged
      );
  }, []);
}
