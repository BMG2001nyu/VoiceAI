"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface TokenStreamProps {
    tokens: string[];
    isSpeaking?: boolean;
}

export function TokenStream({ tokens, isSpeaking }: TokenStreamProps) {
    const containerRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom as tokens arrive
    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [tokens]);

    return (
        <div
            ref={containerRef}
            className="w-full max-w-3xl h-32 overflow-y-auto scrollbar-none flex flex-wrap gap-x-1.5 gap-y-1 content-start justify-center px-4"
        >
            <AnimatePresence mode="popLayout">
                {tokens.map((token, i) => (
                    <motion.span
                        key={`${token}-${i}`}
                        initial={{ opacity: 0, y: 5, filter: "blur(4px)" }}
                        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                        transition={{ duration: 0.2, ease: "easeOut" }}
                        className="text-lg md:text-xl font-medium tracking-tight text-foreground/90 selection:bg-primary/30"
                    >
                        {token}
                    </motion.span>
                ))}
            </AnimatePresence>

            {isSpeaking && (
                <motion.span
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                    className="w-2 h-6 bg-primary/60 rounded-sm mt-1 ml-1"
                />
            )}
        </div>
    );
}
