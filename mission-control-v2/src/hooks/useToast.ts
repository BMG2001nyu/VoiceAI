"use client";

import { useState, useCallback, useEffect } from "react";

export type ToastType = "success" | "error" | "info";

export interface Toast {
    id: string;
    message: string;
    type: ToastType;
}

let subscribers: ((toasts: Toast[]) => void)[] = [];
let toasts: Toast[] = [];

const notify = () => {
    subscribers.forEach((callback) => callback([...toasts]));
};

export const toast = {
    subscribe: (callback: (toasts: Toast[]) => void) => {
        subscribers.push(callback);
        callback([...toasts]);
        return () => {
            subscribers = subscribers.filter((s) => s !== callback);
        };
    },
    show: (message: string, type: ToastType = "success") => {
        const id = Math.random().toString(36).substring(2, 9);
        // Replace existing toast to prevent stacking as per requirements
        toasts = [{ id, message, type }];
        notify();
        setTimeout(() => {
            toast.dismiss(id);
        }, 2000);
    },
    success: (message: string) => toast.show(message, "success"),
    error: (message: string) => toast.show(message, "error"),
    dismiss: (id: string) => {
        toasts = toasts.filter((t) => t.id !== id);
        notify();
    },
};

export function useToasts() {
    const [currentToasts, setCurrentToasts] = useState<Toast[]>(toasts);

    useEffect(() => {
        return toast.subscribe(setCurrentToasts);
    }, []);

    return currentToasts;
}
