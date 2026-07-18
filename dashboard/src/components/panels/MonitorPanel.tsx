import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";
import { useEventBus } from "../../hooks/useEventBus";

function Skeleton() { return <div className="nova-card animate-pulse h-32" />; }
function ErrorCard({ msg, onRetry }: { msg: string; onRetry: () => void }) {
    return <div className="nova-card border-[var(--nova-red)] text-xs font-mono text-[var(--nova-red)] p-4 text-center">{msg}<button onClick={onRetry} className="block w-full mt-3 p-2 bg-[var(--nova-red)]/10 hover:bg-[var(--nova-red)]/20 transition-colors uppercase tracking-widest cursor-pointer rounded">Retry Diagnostics</button></div>;
}

interface Metrics {
    cpu: number; cpu_count: number; cpu_freq_mhz: number; load_avg: number[];
    ram: number; ram_used_gb: number; ram_total_gb: number;
    swap_percent: number; swap_used_gb: number;
    disk: number; disk_used_gb: number; disk_total_gb: number;
    battery: number; battery_charging: boolean; battery_mins_left: number | null;
    network_up_kb: number; network_down_kb: number; net_sent_gb: number; net_recv_gb: number;
    uptime: string; platform: string; hostname: string;
    processes: { name: string; cpu: number; pid: number; mem: number }[];
    temps: Record<string, number>;
}

export function MonitorPanel() {
    const { get, post } = useApi();
    const { addToast } = useNovaStore();
    const { connected, lastEvent } = useEventBus();
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [events, setEvents] = useState<Array<{ time: string; source: string; type: string; priority: number }>>([]);
    const [runningBtn, setRunningBtn] = useState("");

    const fetchMetrics = useCallback(async () => {
        try {
            const d = await get<Metrics>("/api/metrics");
            setMetrics(d);
            setError("");
        } catch (e: any) {
            setError(e.message ?? "Telemetry drop");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => { fetchMetrics(); const iv = setInterval(fetchMetrics, 2000); return () => clearInterval(iv); }, [fetchMetrics]);

    useEffect(() => {
        if (lastEvent) {
            setEvents((prev) => [
                { time: new Date().toLocaleTimeString('en-US', { hour12: false }), source: lastEvent.source, type: lastEvent.type, priority: lastEvent.priority },
                ...prev.slice(0, 24),
            ]);
        }
    }, [lastEvent]);

    const handleAction = async (label: string, endpoint: string) => {
        setRunningBtn(label);
        try {
            await post(endpoint);
            addToast({ id: crypto.randomUUID(), message: `Command Sent: ${label}`, type: "success" });
        } catch { addToast({ id: crypto.randomUUID(), message: `Command Failed: ${label}`, type: "error" }); }
        finally { setTimeout(() => setRunningBtn(""), 1000); }
    };

    function MetricGauge({ title, value, maxVal, unit, subtitle, alertThreshold = 85 }: { title: string, value: number, maxVal: number, unit: string, subtitle?: string, alertThreshold?: number }) {
        const percent = Math.min((value / maxVal) * 100, 100);
        const isAlert = percent >= alertThreshold;
        const colorClass = isAlert ? "bg-[var(--nova-red)]" : percent >= 65 ? "bg-[var(--nova-amber)]" : "bg-[var(--nova-accent)]";
        const textClass = isAlert ? "text-[var(--nova-red)]" : percent >= 65 ? "text-[var(--nova-amber)]" : "text-[var(--nova-text)]";
        const glowClass = isAlert ? "drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" : "drop-shadow-[0_0_8px_rgba(0,255,204,0.3)]";

        return (
            <div className="relative overflow-hidden bg-[var(--nova-surface)] border border-[var(--nova-border)] p-4 rounded-lg flex flex-col justify-between group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--nova-accent)] opacity-[0.02] rounded-full blur-2xl group-hover:opacity-[0.05] transition-opacity duration-700 -mr-10 -mt-10 pointer-events-none" />
                <div className="flex justify-between items-start mb-2 z-10">
                    <span className="text-[10px] font-mono tracking-widest text-[var(--nova-muted)] uppercase">{title}</span>
                    {isAlert && <span className="w-2 h-2 rounded-full bg-[var(--nova-red)] animate-pulse" />}
                </div>
                <div className="flex items-baseline gap-1.5 z-10">
                    <span className={`text-3xl font-mono font-bold tracking-tight ${textClass} ${glowClass}`}>{value.toFixed(1)}</span>
                    <span className="text-xs font-mono text-[var(--nova-muted)]">{unit}</span>
                </div>
                {subtitle && <span className="text-[10px] font-mono text-[var(--nova-muted)] mt-1 mb-3 z-10">{subtitle}</span>}
                {!subtitle && <div className="mb-3" />}
                
                <div className="w-full h-1 bg-[var(--nova-surface2)] rounded-full overflow-hidden mt-auto z-10">
                    <div className={`h-full transition-all duration-1000 ease-out ${colorClass}`} style={{ width: `${percent}%` }} />
                </div>
            </div>
        );
    }

    if (loading) return <div className="p-6 h-full grid grid-cols-4 gap-4 auto-rows-max">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} />)}</div>;
    if (error && !metrics) return <div className="p-6 h-full flex flex-col justify-center items-center"><div className="w-96"><ErrorCard msg={error} onRetry={fetchMetrics} /></div></div>;

    const m = metrics!;

    return (
        <div className="p-6 h-full flex flex-col hide-scrollbar overflow-y-auto relative">
            <style>{`.hide-scrollbar::-webkit-scrollbar { display: none; }`}</style>
            {/* Header */}
            <div className="flex shrink-0 items-center justify-between mb-8 pb-4 border-b border-[var(--nova-border)]/50">
                <div className="flex items-center gap-4">
                    <h1 className="text-lg font-mono tracking-[0.3em] text-[var(--nova-accent)] drop-shadow-[0_0_8px_rgba(0,255,204,0.4)]">TELEMETRY</h1>
                    <div className="flex items-center gap-2 bg-[var(--nova-surface2)] px-3 py-1 rounded-full border border-[var(--nova-border)]">
                        <span className={`w-2 h-2 rounded-full ${connected ? "bg-[var(--nova-green)] animate-pulse shadow-[0_0_5px_var(--nova-green)]" : "bg-[var(--nova-red)] font-bold"}`} />
                        <span className="text-[9px] font-mono tracking-widest text-[var(--nova-muted)]">UPLINK: {connected ? "SECURE" : "LOST"}</span>
                    </div>
                </div>
                <div className="flex items-center gap-4 text-[10px] font-mono text-[var(--nova-muted)] tracking-wider">
                    <div className="text-right">
                        <div>UPTIME: <span className="text-[var(--nova-text)]">{m.uptime}</span></div>
                        <div>NODE: <span className="text-[var(--nova-text)]">{m.hostname}</span></div>
                    </div>
                    <button onClick={fetchMetrics} className="p-2 bg-[var(--nova-surface2)] hover:bg-[var(--nova-accent)]/10 hover:text-[var(--nova-accent)] border border-[var(--nova-border)] rounded transition-all cursor-pointer">
                        ⟳ FORCE SYNC
                    </button>
                </div>
            </div>

            {/* Core Metrics Grid */}
            <div className="grid grid-cols-4 gap-4 mb-6 shrink-0">
                <MetricGauge title="Logical CPU" value={m.cpu} maxVal={100} unit="%" subtitle={`${m.cpu_count} Cores @ ${m.cpu_freq_mhz}MHz`} />
                <MetricGauge title="Physical RAM" value={m.ram_used_gb} maxVal={m.ram_total_gb} unit="GB" subtitle={`${m.ram.toFixed(1)}% Usage`} />
                <MetricGauge title="Solid State Disk" value={m.disk_used_gb} maxVal={m.disk_total_gb} unit="GB" subtitle={`${m.disk.toFixed(1)}% Allocated`} />
                <div className="relative bg-[var(--nova-surface)] border border-[var(--nova-border)] p-4 rounded-lg flex flex-col justify-between">
                    <div className="flex justify-between items-start mb-2">
                        <span className="text-[10px] font-mono tracking-widest text-[var(--nova-muted)] uppercase">POWER CELL</span>
                        {m.battery_charging && <span className="text-[var(--nova-green)] text-xs animate-pulse">⚡</span>}
                    </div>
                    <div className="flex items-baseline gap-1.5">
                        <span className={`text-3xl font-mono font-bold tracking-tight ${m.battery <= 20 && !m.battery_charging ? 'text-[var(--nova-red)] drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'text-[var(--nova-text)]'}`}>{m.battery}</span>
                        <span className="text-xs font-mono text-[var(--nova-muted)]">%</span>
                    </div>
                    <span className="text-[10px] font-mono text-[var(--nova-muted)] mt-1 mb-3">
                        {m.battery_charging ? 'Grid Connected' : (m.battery_mins_left ? `${m.battery_mins_left} mins remaining` : 'Discharging')}
                    </span>
                    <div className="w-full h-1 bg-[var(--nova-surface2)] rounded-full overflow-hidden mt-auto">
                        <div className={`h-full transition-all duration-1000 ${m.battery <= 20 && !m.battery_charging ? 'bg-[var(--nova-red)]' : 'bg-[var(--nova-green)]'}`} style={{ width: `${m.battery}%` }} />
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-12 gap-6 flex-1 min-h-0 pb-6">
                
                {/* Left col - Analysis */}
                <div className="col-span-8 flex flex-col gap-6 h-[500px]">
                    
                    {/* Process Table Container */}
                    <div className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg flex flex-col overflow-hidden relative">
                        <div className="absolute top-0 right-0 p-3 opacity-10 pointer-events-none">
                            <pre className="font-mono text-xs">SYS_PROCS_V2</pre>
                        </div>
                        <div className="p-3 border-b border-[var(--nova-border)]/50 flex justify-between items-center bg-[var(--nova-surface2)]/50">
                            <h3 className="text-[10px] font-mono tracking-[0.3em] text-[var(--nova-accent)] uppercase">Compute Ledger</h3>
                            <span className="text-[9px] font-mono text-[var(--nova-muted)]">TOP {m.processes.length} ALLOCATED</span>
                        </div>
                        <div className="flex-1 overflow-auto hide-scrollbar">
                            <table className="w-full text-xs font-mono tracking-wide relative">
                                <thead className="sticky top-0 bg-[var(--nova-surface)]/95 backdrop-blur z-10 shadow-[0_4px_10px_rgba(0,0,0,0.2)]">
                                    <tr className="text-[9px] tracking-wider text-[var(--nova-muted)]">
                                        <th className="text-left font-normal py-3 px-4 w-[50%]">IDENTIFIER</th>
                                        <th className="text-right font-normal py-3 px-4">PID</th>
                                        <th className="text-right font-normal py-3 px-4">MEM %</th>
                                        <th className="text-right font-normal py-3 px-4 text-[var(--nova-accent)]">CPU %</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {m.processes.map((p) => (
                                        <tr key={p.pid} className={`border-b border-[var(--nova-border)]/30 transition-colors ${p.cpu > 20 ? 'bg-[var(--nova-amber)]/5 hover:bg-[var(--nova-amber)]/10' : 'hover:bg-[var(--nova-surface2)]'}`}>
                                            <td className={`py-2.5 px-4 font-bold truncate max-w-[200px] ${p.cpu > 20 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-text)]'}`}>
                                                {p.name}
                                            </td>
                                            <td className="py-2.5 px-4 text-right text-[var(--nova-muted)]">{p.pid}</td>
                                            <td className="py-2.5 px-4 text-right text-[var(--nova-muted)]">{p.mem.toFixed(1)}</td>
                                            <td className="py-2.5 px-4 text-right text-[var(--nova-text)] glow-text">{p.cpu.toFixed(1)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Lower Left - Sub Metrics & Actions */}
                    <div className="h-40 shrink-0 grid grid-cols-2 gap-4">
                        {/* Network Subsystem */}
                        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-4 flex flex-col justify-between">
                            <h3 className="text-[10px] font-mono tracking-[0.3em] text-[var(--nova-muted)] uppercase mb-2">Network Layer</h3>
                            <div className="grid grid-cols-2 gap-4 flex-1 items-center">
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-[var(--nova-accent)] text-lg leading-none">↑</span>
                                        <span className="text-xl font-mono font-bold text-[var(--nova-text)]">{m.network_up_kb.toFixed(0)}</span>
                                    </div>
                                    <div className="text-[9px] font-mono text-[var(--nova-muted)]">KB/s UPLINK</div>
                                </div>
                                <div className="border-l border-[var(--nova-border)]/50 pl-4">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-[var(--nova-green)] text-lg leading-none">↓</span>
                                        <span className="text-xl font-mono font-bold text-[var(--nova-text)]">{m.network_down_kb.toFixed(0)}</span>
                                    </div>
                                    <div className="text-[9px] font-mono text-[var(--nova-muted)]">KB/s DOWNLINK</div>
                                </div>
                            </div>
                        </div>

                        {/* System Controls */}
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { label: "PURGE CACHE", endpoint: "/api/nova/cleanup" },
                                { label: "FORCE STANDBY", endpoint: "/api/nova/pause" },
                                { label: "LOGICAL REASONING", endpoint: "/api/nova/reasoning-cycle" },
                                { label: "SECURE OVERRIDE", endpoint: "/api/nova/biometric-unlock" },
                            ].map((a) => (
                                <button key={a.label} onClick={() => handleAction(a.label, a.endpoint)}
                                    className="bg-[var(--nova-surface)] hover:bg-[var(--nova-accent)]/10 border border-[var(--nova-accent)]/30 hover:border-[var(--nova-accent)] flex flex-col items-center justify-center rounded transition-all cursor-pointer group disabled:opacity-50 relative overflow-hidden"
                                    disabled={runningBtn === a.label}>
                                    <div className="absolute inset-0 bg-[var(--nova-accent)] opacity-0 group-hover:opacity-5 transition-opacity" />
                                    <span className="text-[9px] font-mono tracking-widest text-[var(--nova-accent)] text-center px-2">
                                        {runningBtn === a.label ? "EXECUTING..." : a.label}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right col - Logs & Aux */}
                <div className="col-span-4 h-[500px] flex flex-col gap-4">
                    {/* Aux Stats */}
                    <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-4 shrink-0 grid grid-cols-2 gap-x-4 gap-y-3">
                        <div>
                            <span className="block text-[9px] font-mono text-[var(--nova-muted)] tracking-wider">SWAP PAGING</span>
                            <span className="font-mono text-xs text-[var(--nova-text)]">{m.swap_used_gb} GB ({m.swap_percent}%)</span>
                        </div>
                        <div>
                            <span className="block text-[9px] font-mono text-[var(--nova-muted)] tracking-wider">LOAD AVG</span>
                            <span className="font-mono text-xs text-[var(--nova-text)]">{m.load_avg.join(', ')}</span>
                        </div>
                        {Object.keys(m.temps).length > 0 && (
                            <div className="col-span-2 border-t border-[var(--nova-border)]/30 mt-1 pt-2">
                                <span className="block text-[9px] font-mono text-[var(--nova-muted)] tracking-wider mb-1">THERMAL SENSORS</span>
                                <div className="flex flex-wrap gap-2">
                                    {Object.entries(m.temps).map(([k, v]) => (
                                        <span key={k} className="text-[10px] font-mono bg-[var(--nova-surface2)] px-2 py-0.5 rounded text-[var(--nova-text)]">{k.replace('core', 'C')}: {v}°C</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Event Feed */}
                    <div className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg flex flex-col overflow-hidden relative">
                        <div className="p-3 border-b border-[var(--nova-border)]/50 bg-[var(--nova-surface2)]/50 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 bg-[var(--nova-accent)] rounded-full animate-pulse" />
                                <h3 className="text-[10px] font-mono tracking-[0.3em] text-[var(--nova-accent)] uppercase">Event Stream</h3>
                            </div>
                            <span className="text-[9px] font-mono text-[var(--nova-muted)]">{events.length} CAPTURED</span>
                        </div>
                        <div className="flex-1 overflow-y-auto hide-scrollbar p-2">
                            {events.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center opacity-30 text-[var(--nova-accent)] font-mono text-xs">
                                    <span>[ LISTENING ]</span>
                                    <span className="mt-2 text-[10px]">&gt; NO INBOUND ANOMALIES</span>
                                </div>
                            ) : (
                                <div className="flex flex-col gap-1.5">
                                    {events.map((ev, i) => {
                                        const isHigh = ev.priority >= 7;
                                        const isMed = ev.priority >= 4;
                                        const color = isHigh ? "text-[var(--nova-red)]" : isMed ? "text-[var(--nova-amber)]" : "text-[var(--nova-text)]";
                                        const bg = isHigh ? "bg-[var(--nova-red)]/10" : isMed ? "bg-[var(--nova-amber)]/5" : "bg-[var(--nova-surface2)]";
                                        const border = isHigh ? "border-l-2 border-[var(--nova-red)]" : "border-l border-[var(--nova-border)]";
                                        
                                        return (
                                            <div key={i} className={`p-2 rounded-r ${bg} ${border} animate-fadeIn`}>
                                                <div className="flex justify-between items-start mb-1">
                                                    <span className={`text-[10px] font-mono font-bold tracking-wide ${color}`}>{ev.type.replace('_', ' ').toUpperCase()}</span>
                                                    <span className="text-[9px] font-mono text-[var(--nova-muted)]">{ev.time}</span>
                                                </div>
                                                <div className="text-[10px] font-mono text-[var(--nova-muted)] truncate max-w-full">SRC: {ev.source}</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
