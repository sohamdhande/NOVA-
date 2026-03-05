import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";
import { useEventBus } from "../../hooks/useEventBus";

function Skeleton() { return <div className="nova-card animate-pulse h-20" />; }
function ErrorCard({ msg, onRetry }: { msg: string; onRetry: () => void }) {
    return <div className="nova-card border-[var(--nova-red)] text-xs font-mono text-[var(--nova-red)]">{msg}<button onClick={onRetry} className="ml-3 underline cursor-pointer">RETRY</button></div>;
}

interface Metrics {
    cpu: number; ram: number; disk: number; battery: number;
    battery_charging: boolean;
    processes: { name: string; cpu: number; pid: number }[];
    network_up_kb?: number; network_down_kb?: number;
}

export function MonitorPanel() {
    const { get, post } = useApi();
    const { addToast } = useNovaStore();
    const { connected, lastEvent } = useEventBus();
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [events, setEvents] = useState<Array<{ time: string; source: string; type: string; priority: number }>>([]);
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [runningBtn, setRunningBtn] = useState("");

    const fetchMetrics = useCallback(async () => {
        try {
            const d = await get<Metrics>("/api/metrics");
            setMetrics(d);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message ?? "Fetch failed");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => { fetchMetrics(); const iv = setInterval(fetchMetrics, 5000); return () => clearInterval(iv); }, [fetchMetrics]);

    // Track live events
    useEffect(() => {
        if (lastEvent) {
            setEvents((prev) => [
                { time: new Date().toLocaleTimeString(), source: lastEvent.source, type: lastEvent.type, priority: lastEvent.priority },
                ...prev.slice(0, 19),
            ]);
        }
    }, [lastEvent]);

    const handleAction = async (label: string, endpoint: string) => {
        setRunningBtn(label);
        try {
            await post(endpoint);
            addToast({ id: crypto.randomUUID(), message: `${label} executed`, type: "success" });
        } catch { addToast({ id: crypto.randomUUID(), message: `${label} failed`, type: "error" }); }
        finally { setTimeout(() => setRunningBtn(""), 1500); }
    };

    function GaugeCard({ label, value, isCharging }: { label: string; value: number; isCharging?: boolean }) {
        const color = value > 85 ? "bg-[var(--nova-red)]" : value > 60 ? "bg-[var(--nova-amber)]" : "bg-[var(--nova-green)]";
        const textColor = value > 85 ? "text-[var(--nova-red)]" : value > 60 ? "text-[var(--nova-amber)]" : "text-[var(--nova-green)]";
        return (
            <div className="nova-card flex flex-col gap-2">
                <div className="flex items-center justify-between">
                    <span className="text-[9px] font-mono tracking-[0.2em] text-[var(--nova-muted)] uppercase">{label}</span>
                    {value > 85 && <span className="w-2 h-2 rounded-full bg-[var(--nova-red)] animate-pulse" />}
                </div>
                <div className="flex items-baseline gap-1">
                    <span className={`text-2xl font-mono font-bold ${textColor}`}>{value}</span>
                    <span className="text-xs font-mono text-[var(--nova-muted)]">%</span>
                    {isCharging && <span className="text-[var(--nova-green)] text-sm ml-1">⚡</span>}
                </div>
                <div className="w-full h-1.5 bg-[var(--nova-surface2)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${Math.min(value, 100)}%` }} />
                </div>
            </div>
        );
    }

    if (loading) return <div className="p-6 grid grid-cols-4 gap-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />)}</div>;
    if (error) return <div className="p-6"><ErrorCard msg={error} onRetry={fetchMetrics} /></div>;

    const m = metrics!;
    const procs = [...(m.processes || [])].sort((a, b) => b.cpu - a.cpu);

    return (
        <div className="p-6 h-full overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-sm font-mono tracking-[0.3em] uppercase text-[var(--nova-accent)]">SYSTEM MONITOR</h1>
                <div className="flex items-center gap-3">
                    <span className={`text-[9px] font-mono ${connected ? "text-[var(--nova-green)]" : "text-[var(--nova-red)]"}`}>
                        WS {connected ? "CONNECTED" : "DISCONNECTED"}
                    </span>
                    <span className="text-[9px] font-mono text-[var(--nova-muted)]">UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchMetrics} className="text-[var(--nova-muted)] hover:text-[var(--nova-accent)] text-xs cursor-pointer">⟳</button>
                </div>
            </div>

            {/* Gauge Cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
                <GaugeCard label="CPU" value={m.cpu} />
                <GaugeCard label="RAM" value={m.ram} />
                <GaugeCard label="DISK" value={m.disk} />
                <GaugeCard label="BATTERY" value={m.battery} isCharging={m.battery_charging} />
            </div>

            <div className="grid grid-cols-2 gap-6">
                {/* Left: Process Table + Network */}
                <div className="flex flex-col gap-4">
                    {/* Processes */}
                    <div>
                        <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] mb-3 uppercase">RUNNING PROCESSES</h3>
                        <div className="nova-card !p-0 overflow-hidden">
                            <table className="w-full text-[10px] font-mono">
                                <thead>
                                    <tr className="border-b border-[var(--nova-border)] text-[var(--nova-muted)]">
                                        <th className="text-left py-2 px-3">NAME</th>
                                        <th className="text-right py-2 px-3">CPU%</th>
                                        <th className="text-right py-2 px-3">PID</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {procs.map((p, i) => (
                                        <tr key={i} className={`border-b border-[var(--nova-border)]/50 hover:bg-[var(--nova-accent)]/5 transition-colors ${p.cpu > 10 ? "text-[var(--nova-amber)]" : "text-[var(--nova-text)]"}`}>
                                            <td className="py-1.5 px-3">{p.name}</td>
                                            <td className="py-1.5 px-3 text-right">{p.cpu}</td>
                                            <td className="py-1.5 px-3 text-right text-[var(--nova-muted)]">{p.pid}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Network */}
                    <div className="flex gap-4">
                        <div className="nova-card flex-1 flex items-center gap-2">
                            <span className="text-[var(--nova-accent)]">↑</span>
                            <span className="text-xs font-mono text-[var(--nova-accent)]">{m.network_up_kb ?? 0} KB/s</span>
                        </div>
                        <div className="nova-card flex-1 flex items-center gap-2">
                            <span className="text-[var(--nova-green)]">↓</span>
                            <span className="text-xs font-mono text-[var(--nova-green)]">{m.network_down_kb ?? 0} KB/s</span>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { label: "RUN CLEANUP", endpoint: "/api/nova/cleanup" },
                            { label: "PAUSE NOVA", endpoint: "/api/nova/pause" },
                            { label: "TRIGGER REASONING", endpoint: "/api/nova/reasoning-cycle" },
                            { label: "BIOMETRIC UNLOCK", endpoint: "/api/nova/biometric-unlock" },
                        ].map((a) => (
                            <button key={a.label} onClick={() => handleAction(a.label, a.endpoint)}
                                className="text-[10px] font-mono tracking-wider px-3 py-2 rounded border border-[var(--nova-accent)]/30 text-[var(--nova-accent)] hover:bg-[var(--nova-accent)]/10 transition-colors cursor-pointer disabled:opacity-50"
                                disabled={runningBtn === a.label}>
                                {runningBtn === a.label ? "..." : a.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Right: Live Event Feed */}
                <div>
                    <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] mb-3 uppercase">LIVE EVENT FEED</h3>
                    <div className="nova-card !p-0 max-h-[400px] overflow-y-auto">
                        {events.length === 0 ? (
                            <div className="text-[10px] font-mono text-[var(--nova-muted)] text-center py-8">Waiting for events...</div>
                        ) : (
                            events.map((ev, i) => {
                                const pColor = ev.priority >= 7 ? "text-[var(--nova-red)]" : ev.priority >= 4 ? "text-[var(--nova-amber)]" : "text-[var(--nova-muted)]";
                                return (
                                    <div key={i} className="flex items-center gap-2 px-3 py-1.5 border-b border-[var(--nova-border)]/30 text-[10px] font-mono">
                                        <span className="text-[var(--nova-muted)] shrink-0 w-16">{ev.time}</span>
                                        <span className="text-[var(--nova-text)] flex-1 truncate">{ev.source} → {ev.type}</span>
                                        <span className={`shrink-0 ${pColor}`}>P{ev.priority}</span>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
