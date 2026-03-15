"use client";

import { useState, useEffect, useRef } from "react";

/**
 * usePulseOnUpdate
 * Returns a boolean that is true for a short duration when the 'trigger' value changes.
 */
export function usePulseOnUpdate(trigger: any, duration: number = 1000) {
    const [isPulsing, setIsPulsing] = useState(false);
    const isFirstRender = useRef(true);
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        // Skip pulse on first mount
        if (isFirstRender.current) {
            isFirstRender.current = false;
            return;
        }

        // Trigger pulse
        setIsPulsing(true);

        // Clear existing timeout if any
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
        }

        // Reset after duration
        timeoutRef.current = setTimeout(() => {
            setIsPulsing(false);
            timeoutRef.current = null;
        }, duration);

        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };
    }, [trigger, duration]);

    return isPulsing;
}
