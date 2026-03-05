import { useEffect } from "react";
import { useNovaStore, type Toast } from "../../store/novaStore";

const TYPE_STYLES: Record<Toast["type"], { border: string; icon: string; bar: string }> = {
    info: { border: "border-[var(--nova-accent)]", icon: "ℹ", bar: "bg-[var(--nova-accent)]" },
    success: { border: "border-[var(--nova-green)]", icon: "✓", bar: "bg-[var(--nova-green)]" },
    warning: { border: "border-[var(--nova-amber)]", icon: "⚠", bar: "bg-[var(--nova-amber)]" },
    error: { border: "border-[var(--nova-red)]", icon: "✕", bar: "bg-[var(--nova-red)]" },
};

function ToastCard({ toast }: { toast: Toast }) {
    const { removeToast } = useNovaStore();
    const s = TYPE_STYLES[toast.type];

    useEffect(() => {
        const t = setTimeout(() => removeToast(toast.id), toast.duration ?? 4000);
        return () => clearTimeout(t);
    }, [toast.id, toast.duration, removeToast]);

    return (
        <div
            className={`flex items-stretch gap-0 rounded overflow-hidden border ${s.border} bg-[var(--nova-surface)] animate-slide-in-right min-w-[280px] max-w-[360px]`}
        >
            {/* Color bar */}
            <div className={`w-1 shrink-0 ${s.bar}`} />

            {/* Content */}
            <div className="flex-1 flex items-center gap-3 px-3 py-2.5">
                <span className="text-sm">{s.icon}</span>
                <span className="text-xs font-mono text-[var(--nova-text)] leading-tight">{toast.message}</span>
            </div>

            {/* Close */}
            <button
                onClick={() => removeToast(toast.id)}
                className="px-2 text-[var(--nova-muted)] hover:text-[var(--nova-text)] text-xs transition-colors"
            >
                ✕
            </button>
        </div>
    );
}

export function ToastContainer() {
    const { toasts } = useNovaStore();

    return (
        <div className="fixed bottom-4 right-4 z-[9998] flex flex-col-reverse gap-2">
            {toasts.map((t: Toast) => (
                <ToastCard key={t.id} toast={t} />
            ))}
        </div>
    );
}
