import { create } from "zustand";

export interface Toast {
    id: string;
    message: string;
    type: "info" | "warning" | "error" | "success";
    duration?: number;
}

interface NovaStore {
    // System
    systemStatus: "online" | "offline" | "paused";
    autonomy: boolean;
    sessionMinutes: number;
    metrics: {
        cpu: number;
        ram: number;
        disk: number;
        battery: number;
        batteryCharging: boolean;
    };

    // Navigation
    activePanel: string;
    setActivePanel: (panel: string) => void;

    // Notifications
    toasts: Toast[];
    addToast: (toast: Toast) => void;
    removeToast: (id: string) => void;

    // Approvals
    pendingApprovals: number;

    // Actions
    setMetrics: (metrics: Partial<NovaStore["metrics"]>) => void;
    setSystemStatus: (status: NovaStore["systemStatus"]) => void;
    setAutonomy: (val: boolean) => void;
    setPendingApprovals: (count: number) => void;
}

export const useNovaStore = create<NovaStore>((set) => ({
    // Defaults
    systemStatus: "online",
    autonomy: true,
    sessionMinutes: 30,
    metrics: {
        cpu: 0,
        ram: 0,
        disk: 0,
        battery: 100,
        batteryCharging: false,
    },

    activePanel: "hq",
    setActivePanel: (panel) => set({ activePanel: panel }),

    toasts: [],
    addToast: (toast) =>
        set((s) => ({ toasts: [...s.toasts.slice(-4), toast] })),
    removeToast: (id) =>
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

    pendingApprovals: 0,

    setMetrics: (metrics) =>
        set((s) => ({ metrics: { ...s.metrics, ...metrics } })),
    setSystemStatus: (status) => set({ systemStatus: status }),
    setAutonomy: (val) => set({ autonomy: val }),
    setPendingApprovals: (count) => set({ pendingApprovals: count }),
}));
