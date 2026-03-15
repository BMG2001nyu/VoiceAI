import React, { useRef, useEffect } from "react";
import { useReducedMotion } from "framer-motion";

interface WaveformCanvasProps {
    activity: number; // 0-1
    color: string;
}

export function WaveformCanvas({ activity, color }: WaveformCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const shouldReduceMotion = useReducedMotion();

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let animationId: number;
        let time = 0;

        // Define multiple strands for a layered look
        const strands = [
            { freq: 0.015, amp: 40, speed: 0.02, alpha: 0.15, width: 4, drift: 0 },
            { freq: 0.025, amp: 30, speed: 0.035, alpha: 0.3, width: 2, drift: 2 },
            { freq: 0.012, amp: 50, speed: 0.015, alpha: 0.1, width: 6, drift: -2 },
            { freq: 0.035, amp: 20, speed: 0.05, alpha: 0.5, width: 1.5, drift: 1 },
        ];

        const resize = () => {
            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            ctx.scale(dpr, dpr);
        };

        window.addEventListener("resize", resize);
        resize();

        const render = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const rect = canvas.getBoundingClientRect();
            const { width, height } = rect;
            const centerY = height / 2;

            // Intensity affects both amplitude and speed
            const intensity = Math.max(0.05, activity); // Keep a small movement even when idle

            strands.forEach((s) => {
                ctx.beginPath();
                ctx.strokeStyle = color;
                ctx.globalAlpha = s.alpha;
                ctx.lineWidth = s.width;
                ctx.lineJoin = "round";

                // Add a subtle glow per strand
                ctx.shadowBlur = activity * 20;
                ctx.shadowColor = color;

                for (let x = 0; x < width; x += 2) {
                    const motionScale = shouldReduceMotion ? 0.1 : 1;
                    const wave1 = Math.sin(x * s.freq + time * s.speed * motionScale + s.drift);
                    const wave2 = Math.sin(x * s.freq * 0.5 - time * s.speed * 0.3 * motionScale);

                    // Combine waves for organic movement
                    const combinedWave = (wave1 + wave2) / 2;

                    const y = centerY + combinedWave * (s.amp * intensity * motionScale);

                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            });

            // Optional: Tiny particle specks for depth
            if (!shouldReduceMotion && activity > 0.3) {
                ctx.globalAlpha = 0.2;
                for (let i = 0; i < 5; i++) {
                    const px = (time + i * 100) % width;
                    const py = centerY + Math.sin(px * 0.01 + time * 0.01) * 30;
                    ctx.beginPath();
                    ctx.arc(px, py, 1, 0, Math.PI * 2);
                    ctx.fillStyle = color;
                    ctx.fill();
                }
            }

            time += 0.5;
            animationId = requestAnimationFrame(render);
        };

        render();

        return () => {
            cancelAnimationFrame(animationId);
            window.removeEventListener("resize", resize);
        };
    }, [activity, color, shouldReduceMotion]);

    return (
        <div className="w-full h-full flex items-center justify-center overflow-hidden">
            <canvas ref={canvasRef} className="w-full h-64 sm:h-80 md:h-96" />
        </div>
    );
}
