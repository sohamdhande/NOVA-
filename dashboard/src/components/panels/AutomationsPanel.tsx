import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";

function Skeleton() { return <div className="nova-card animate-pulse h-28" />; }
function ErrorCard({ msg, onRetry }: { msg: string; onRetry: () => void }) {
    return <div className="nova-card border-[var(--nova-red)] text-xs font-mono text-[var(--nova-red)]">{msg}<button onClick={onRetry} className="ml-3 underline cursor-pointer">RETRY</button></div>;
}

interface Automation { id: string; name: string; category: string; enabled: boolean; last_run: string; schedule?: string; }

type Tab = "ALL" | "SYSTEM" | "PRODUCTIVITY";

export function AutomationsPanel() {
    const { get, post, patch } = useApi();
    const { addToast } = useNovaStore();
    const [automations, setAutomations] = useState<Automation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [tab, setTab] = useState<Tab>("ALL");
    const [runningId, setRunningId] = useState("");

    const fetchAutomations = useCallback(async () => {
        try {
            const d = await get<any>("/api/automations");
            setAutomations(Array.isArray(d) ? d : d?.automations ?? []);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) { setError(e.message ?? "Fetch failed"); }
        finally { setLoading(false); }
    }, [get]);

    useEffect(() => { fetchAutomations(); const iv = setInterval(fetchAutomations, 30000); return () => clearInterval(iv); }, [fetchAutomations]);

    const toggleAutomation = async (id: string) => {
        try {
            await patch(`/api/automations/${id}/toggle`, {});
            setAutomations((prev) => prev.map((a) => a.id === id ? { ...a, enabled: !a.enabled } : a));
        } catch { /* ignore */ }
    };

    const runAutomation = async (id: string, name: string) => {
        setRunningId(id);
        try {
            await post(`/api/automations/${id}/run`);
            addToast({ id: crypto.randomUUID(), message: `Automation triggered: ${name}`, type: "success" });
        } catch {
            addToast({ id: crypto.randomUUID(), message: `Failed to run: ${name}`, type: "error" });
        }
        setTimeout(() => setRunningId(""), 2000);
    };

    const filtered = tab === "ALL" ? automations : automations.filter((a) => a.category.toUpperCase() === tab);

    const quickActions = [
        { label: "CLEAN DOWNLOADS", id: "a1" },
        { label: "START FOCUS MODE", id: "a4" },
        { label: "OPEN WORKSPACE", id: "a6" },
    ];

    if (loading) return <div className="p-6 grid grid-cols-2 gap-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />)}</div>;
    if (error) return <div className="p-6"><ErrorCard msg={error} onRetry={fetchAutomations} /></div>;

    return (
        <div className="p-6 h-full overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-sm font-mono tracking-[0.3em] uppercase text-[var(--nova-accent)]">AUTOMATION LIBRARY</h1>
                <div className="flex items-center gap-3">
                    <span className="text-[9px] font-mono text-[var(--nova-muted)]">UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchAutomations} className="text-[var(--nova-muted)] hover:text-[var(--nova-accent)] text-xs cursor-pointer">⟳</button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-5">
                {(["ALL", "SYSTEM", "PRODUCTIVITY"] as Tab[]).map((t) => (
                    <button key={t} onClick={() => setTab(t)}
                        className={`text-[10px] font-mono tracking-wider px-3 py-1.5 rounded transition-colors cursor-pointer ${tab === t
                                ? "bg-[var(--nova-accent)]/10 text-[var(--nova-accent)] border border-[var(--nova-accent)]/30"
                                : "text-[var(--nova-muted)] border border-transparent hover:text-[var(--nova-text)]"
                            }`}>
                        {t}
                    </button>
                ))}
            </div>

            {/* Automation Grid */}
            {filtered.length === 0 ? (
                <div className="text-[10px] font-mono text-[var(--nova-muted)] text-center py-12">No automations in this category</div>
            ) : (
                <div className="grid grid-cols-2 gap-4 mb-6">
                    {filtered.map((a) => (
                        <div key={a.id} className={`nova-card relative transition-opacity ${!a.enabled ? "opacity-60" : ""} ${a.enabled ? "border-l-2 border-l-[var(--nova-accent)]" : ""}`}>
                            <div className="flex items-start justify-between mb-2">
                                <div>
                                    <span className="text-xs font-mono text-[var(--nova-accent)]">{a.name}</span>
                                    <span className={`ml-2 text-[8px] font-mono px-1.5 py-0.5 rounded ${a.category === "system" ? "bg-blue-500/20 text-blue-400" : "bg-[var(--nova-green)]/20 text-[var(--nova-green)]"}`}>
                                        {a.category.toUpperCase()}
                                    </span>
                                </div>

                                {/* Toggle switch */}
                                <button onClick={() => toggleAutomation(a.id)}
                                    className={`w-8 h-4 rounded-full relative transition-colors cursor-pointer ${a.enabled ? "bg-[var(--nova-accent)]/30" : "bg-[var(--nova-surface2)]"}`}>
                                    <div className={`absolute top-0.5 w-3 h-3 rounded-full transition-all ${a.enabled ? "left-4 bg-[var(--nova-accent)]" : "left-0.5 bg-[var(--nova-muted)]"}`} />
                                </button>
                            </div>

                            <div className="text-[8px] font-mono text-[var(--nova-muted)] mb-3">Last run: {a.last_run}</div>

                            <button onClick={() => runAutomation(a.id, a.name)}
                                disabled={runningId === a.id}
                                className="text-[9px] font-mono tracking-wider px-3 py-1 rounded border border-[var(--nova-accent)]/30 text-[var(--nova-accent)] hover:bg-[var(--nova-accent)]/10 transition-colors cursor-pointer disabled:opacity-50">
                                {runningId === a.id ? "⟳ RUNNING..." : "▶ RUN NOW"}
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Quick Actions */}
            <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] mb-3 uppercase">QUICK ACTIONS</h3>
            <div className="grid grid-cols-3 gap-3">
                {quickActions.map((qa) => (
                    <button key={qa.id} onClick={() => runAutomation(qa.id, qa.label)}
                        className="nova-card text-center text-[10px] font-mono tracking-wider text-[var(--nova-accent)] hover:bg-[var(--nova-accent)]/5 transition-colors cursor-pointer !py-3">
                        {qa.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
