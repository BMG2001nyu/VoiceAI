import React from "react";
import { useToasts, toast } from "@/hooks/useToast";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, AlertCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function ToastHost() {
    const toasts = useToasts();

    return (
        <div className="fixed bottom-24 right-6 z-[60] flex flex-col items-end gap-2 pointer-events-none">
            <AnimatePresence mode="popLayout">
                {toasts.map((t) => (
                    <motion.div
                        key={t.id}
                        layout
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.15 } }}
                        className={cn(
                            "pointer-events-auto flex items-center gap-2 px-3 py-2 rounded-full border shadow-xl bg-card/90 backdrop-blur-md",
                            "animate-in fade-in slide-in-from-right-4 duration-300",
                            t.type === "success" ? "border-primary/20 text-primary" : "border-destructive/20 text-destructive"
                        )}
                    >
                        {t.type === "success" ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                        <span className="text-[11px] font-bold tracking-tight uppercase">{t.message}</span>
                        <button
                            onClick={() => toast.dismiss(t.id)}
                            className="ml-1 p-0.5 rounded-full hover:bg-muted transition-colors opacity-60 hover:opacity-100"
                        >
                            <X size={10} />
                        </button>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
}
