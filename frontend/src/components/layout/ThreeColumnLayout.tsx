import React, { ReactNode } from "react";

interface ThreeColumnLayoutProps {
    left: ReactNode;
    center: ReactNode;
    right: ReactNode;
    bottom: ReactNode;
    drawer?: ReactNode;
}

export function ThreeColumnLayout({ left, center, right, bottom, drawer }: ThreeColumnLayoutProps) {
    return (
        <div className="h-screen w-screen flex flex-col pt-14 pb-20 overflow-hidden bg-background">
            <main className="flex-1 flex overflow-hidden">
                {/* Left Column: Agent Fleet */}
                <aside className="w-[300px] xl:w-[350px] border-r border-border flex flex-col bg-background/40">
                    {left}
                </aside>

                {/* Center Column: Workbench */}
                <section className="flex-1 border-r border-border flex flex-col min-w-0 bg-background">
                    {center}
                </section>

                {/* Right Column: Evidence Board */}
                <aside className="w-[380px] xl:w-[450px] flex flex-col bg-background/40">
                    {right}
                </aside>
            </main>

            {/* Bottom Sticky Command Bar */}
            <footer className="fixed bottom-0 left-0 right-0 h-20 border-t border-border bg-background/95 backdrop-blur-sm z-40 flex items-center justify-center">
                {bottom}
            </footer>

            {/* Timeline Drawer (slide-up) */}
            {drawer}
        </div>
    );
}
