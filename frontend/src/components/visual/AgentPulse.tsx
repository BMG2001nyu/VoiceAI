import React, { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Zap, Brain } from "lucide-react";

interface AgentPulseProps {
    status: "IDLE" | "ACTIVE" | "FAILED";
    isSpeaking?: boolean;
    isThinking?: boolean;
    color: string;
    icon?: React.ReactNode;
}

export function AgentPulse({ status, isSpeaking, isThinking, color, icon }: AgentPulseProps) {
    // Determine animation variant based on state
    const state = useMemo(() => {
        if (status === "FAILED") return "failed";
        if (isSpeaking) return "speaking";
        if (isThinking) return "thinking";
        return "idle";
    }, [status, isSpeaking, isThinking]);

    const variants = {
        idle: {
            scale: [1, 1.05, 1],
            opacity: [0.3, 0.5, 0.3],
            transition: { duration: 4, repeat: Infinity, ease: "easeInOut" as const }
        },
        thinking: {
            rotate: [0, 360],
            scale: [1, 1.1, 1],
            opacity: [0.4, 0.7, 0.4],
            transition: {
                rotate: { duration: 10, repeat: Infinity, ease: "linear" as const },
                scale: { duration: 2, repeat: Infinity, ease: "easeInOut" as const }
            }
        },
        speaking: {
            scale: [1, 1.2, 0.9, 1.1, 1],
            opacity: [0.6, 1, 0.8, 1, 0.6],
            transition: { duration: 0.8, repeat: Infinity, ease: "easeInOut" as const }
        },
        failed: {
            scale: [1, 0.95, 1],
            opacity: 0.2,
            transition: { duration: 2, repeat: Infinity }
        }
    };

    return (
        <div className="relative flex items-center justify-center w-64 h-64 md:w-80 md:h-80">
            {/* Outer Layered Rings */}
            <AnimatePresence mode="popLayout">
                {[0.4, 0.7, 1].map((scale, i) => (
                    <motion.div
                        key={`${state}-${i}`}
                        className="absolute inset-0 rounded-full border border-current pointer-events-none"
                        style={{ color }}
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={variants[state]}
                        custom={i}
                        transition={{
                            delay: i * 0.2,
                            duration: state === "speaking" ? 0.5 : 2
                        }}
                    />
                ))}
            </AnimatePresence>

            {/* Glow Field */}
            <motion.div
                className="absolute inset-4 rounded-full blur-3xl opacity-20 pointer-events-none"
                style={{ backgroundColor: color }}
                animate={{
                    scale: state === "speaking" ? [1, 1.5, 1] : 1,
                    opacity: state === "speaking" ? [0.2, 0.4, 0.2] : 0.2
                }}
            />

            {/* Center Avatar Hexagon/Circle */}
            <div className="relative z-10 w-24 h-24 md:w-32 md:h-32 rounded-3xl bg-card border-2 border-border flex items-center justify-center shadow-2xl overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-50" />

                {/* State Icon overlay */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={state}
                        initial={{ opacity: 0, scale: 0.5 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.5 }}
                        className="text-foreground"
                    >
                        {state === "thinking" && <Brain size={48} className="animate-pulse" />}
                        {state === "speaking" && <Zap size={48} className="text-primary" />}
                        {state === "failed" && <Bot size={48} className="text-destructive" />}
                        {state === "idle" && (icon || <Bot size={48} className="text-muted-foreground opacity-50" />)}
                    </motion.div>
                </AnimatePresence>

                {/* Inner Scanning Line (for thinking state) */}
                {state === "thinking" && (
                    <motion.div
                        className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/20 to-transparent h-1/2 w-full"
                        animate={{ y: ["-100%", "200%"] }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    />
                )}
            </div>

            {/* Particle Orbit (Simplified) */}
            {!["failed", "idle"].includes(state) && (
                <div className="absolute inset-[-20%] pointer-events-none">
                    {[...Array(6)].map((_, i) => (
                        <motion.div
                            key={i}
                            className="absolute w-1 h-1 rounded-full"
                            style={{ backgroundColor: color }}
                            animate={{
                                rotate: 360,
                                x: [0, Math.cos(i) * 100, 0],
                                y: [0, Math.sin(i) * 100, 0],
                                opacity: [0, 0.8, 0]
                            }}
                            transition={{
                                duration: 3 + i,
                                repeat: Infinity,
                                ease: "linear",
                                delay: i * 0.5
                            }}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
