import { create } from "zustand";

interface FocusStore {
    selectedAgentId: string | null;
    isFocusOpen: boolean;
    openFocus: (agentId: string) => void;
    closeFocus: () => void;
}

export const useFocusStore = create<FocusStore>((set) => ({
    selectedAgentId: null,
    isFocusOpen: false,
    openFocus: (agentId) => set({ selectedAgentId: agentId, isFocusOpen: true }),
    closeFocus: () => set({ isFocusOpen: false, selectedAgentId: null }),
}));
