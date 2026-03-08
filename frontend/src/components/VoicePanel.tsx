import { useState, useRef, useEffect } from "react";
import { Mic, MicOff, Square } from "lucide-react";
import { clsx } from "clsx";
import { useMissionStore } from "../store";

function Waveform({ active, speaking }: { active: boolean; speaking: boolean }) {
  const BAR_COUNT = 32;
  const bars = Array.from({ length: BAR_COUNT });

  return (
    <div className="flex items-center gap-[2px] h-8">
      {bars.map((_, i) => (
        <div
          key={i}
          className={clsx("w-[3px] rounded-full transition-all", {
            "bg-accent-green": speaking,
            "bg-accent-blue": active && !speaking,
            "bg-slate-800": !active,
          })}
          style={{
            height: active
              ? `${20 + Math.sin((Date.now() / 120 + i * 0.6)) * 14 + Math.random() * 8}px`
              : "4px",
            transition: active ? "height 80ms ease" : "height 300ms ease",
          }}
        />
      ))}
    </div>
  );
}

function AnimatedWaveform({ active, speaking }: { active: boolean; speaking: boolean }) {
  const [tick, setTick] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!active) return;
    const loop = () => {
      setTick((t) => t + 1);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [active]);

  void tick;
  return <Waveform active={active} speaking={speaking} />;
}

export function VoicePanel() {
  const [micActive, setMicActive] = useState(false);
  const transcript = useMissionStore((s) => s.transcript);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (transcriptEndRef.current?.scrollIntoView) {
      transcriptEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [transcript]);

  return (
    <div className="h-full flex items-stretch px-4 gap-4">
      {/* Mic button */}
      <div className="flex items-center justify-center w-16 shrink-0">
        <button
          onClick={() => setMicActive((v) => !v)}
          className={clsx(
            "relative w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 border-2",
            {
              "bg-accent-green/10 border-accent-green text-accent-green shadow-[0_0_16px_rgba(34,197,94,0.3)]":
                micActive,
              "bg-slate-900 border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300":
                !micActive,
            }
          )}
          aria-label={micActive ? "Stop recording" : "Start recording"}
        >
          {micActive ? (
            <>
              <span className="absolute inset-0 rounded-full border-2 border-accent-green animate-ping opacity-40" />
              <Square size={16} fill="currentColor" />
            </>
          ) : (
            <Mic size={16} />
          )}
        </button>
      </div>

      {/* Waveform */}
      <div className="flex items-center w-40 shrink-0">
        <AnimatedWaveform active={micActive} speaking={micActive} />
      </div>

      {/* Transcript feed */}
      <div className="flex-1 flex flex-col justify-end overflow-hidden py-2 gap-1.5">
        <div className="overflow-y-auto scrollbar-thin flex flex-col gap-1 max-h-full">
          {transcript.map((entry) => (
            <div
              key={entry.id}
              className={clsx("flex", {
                "justify-end": entry.role === "user",
                "justify-start": entry.role === "assistant",
              })}
            >
              <div
                className={clsx(
                  "max-w-[75%] px-2.5 py-1.5 rounded-lg text-xs leading-snug",
                  {
                    "bg-green-900/30 text-accent-green border border-accent-green/20":
                      entry.role === "user",
                    "bg-slate-800 text-text-secondary border border-[#1e293b]":
                      entry.role === "assistant",
                  }
                )}
              >
                {entry.text}
              </div>
            </div>
          ))}
          <div ref={transcriptEndRef} />
        </div>
      </div>

      {/* Status label */}
      <div className="flex items-center w-24 shrink-0 justify-end">
        <div className="flex flex-col items-end gap-1">
          <span
            className={clsx("text-[10px] font-mono uppercase tracking-wider", {
              "text-accent-green": micActive,
              "text-slate-600": !micActive,
            })}
          >
            {micActive ? "Recording" : "Push to talk"}
          </span>
          {!micActive && (
            <span className="text-[10px] text-slate-700 font-mono">
              <MicOff size={10} className="inline mr-1" />
              Muted
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
