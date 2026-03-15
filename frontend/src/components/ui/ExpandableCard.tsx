import React, { ReactNode } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExpandableCardProps {
    isOpen: boolean;
    onToggle: () => void;
    header: ReactNode;
    children: ReactNode;
    className?: string;
    headerClassName?: string;
    isPulsing?: boolean;
}

export function ExpandableCard({
    isOpen,
    onToggle,
    header,
    children,
    className,
    headerClassName,
    isPulsing,
}: ExpandableCardProps) {
    const shouldReduceMotion = useReducedMotion();

    return (
        <div
            className={cn(
                "group h-fit flex flex-col rounded-xl border border-border bg-card/40 transition-all overflow-hidden",
                isPulsing && "ring-1 ring-primary/40 bg-primary/[0.03] border-primary/30 shadow-[0_0_15px_rgba(34,197,94,0.1)]",
                !isPulsing && "hover:bg-card/60 hover:border-muted-foreground/30",
                className
            )}
        >
            <button
                onClick={onToggle}
                aria-expanded={isOpen}
                className={cn(
                    "w-full text-left p-3 flex flex-col gap-2 focus:outline-none focus:ring-1 focus:ring-primary/40",
                    headerClassName
                )}
            >
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">{header}</div>
                    <ChevronDown
                        size={16}
                        className={cn(
                            "shrink-0 mt-1 text-muted-foreground transition-transform duration-300",
                            isOpen && "rotate-180"
                        )}
                    />
                </div>
            </button>

            <AnimatePresence initial={false}>
                {isOpen && (
                    <motion.div
                        initial={shouldReduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
                        animate={shouldReduceMotion ? { opacity: 1 } : { height: "auto", opacity: 1 }}
                        exit={shouldReduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
                        transition={{
                            type: "spring",
                            stiffness: 300,
                            damping: 30,
                            opacity: { duration: 0.2 },
                        }}
                    >
                        <div className="px-3 pb-3 pt-0 border-t border-border/50 bg-muted/20">
                            {children}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
