import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useEventBus } from "../../hooks/useEventBus";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function ReasoningPanel() {
    const { get, post } = useApi();
    const { lastEvent } = useEventBus();
    const [data, setData] = useState<any>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [triggering, setTriggering] = useState(false);

    // Maintain a local array for the live event feed
    const [liveEvents, setLiveEvents] = useState<any[]>([]);

    useEffect(() => {
        if (lastEvent) {
            setLiveEvents(prev => [lastEvent, ...prev].slice(0, 10));
        }
    }, [lastEvent]);

    const fetchReasoning = useCallback(async () => {
        try {
            const res = await get<any>('/api/reasoning').catch(() => ({
                plan: [],
                confidence: 0,
                model: 'llama3.2',
                last_inference: 0,
                recent_thoughts: []
            }));
            setData(res);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch reasoning data");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchReasoning();
        const iv = setInterval(fetchReasoning, 15000);
        return () => clearInterval(iv);
    }, [fetchReasoning]);

    const handleTrigger = async () => {
        if (triggering) return;
        setTriggering(true);
        try {
            await post('/api/nova/reasoning-cycle', {});
            setTimeout(() => {
                setTriggering(false);
                fetchReasoning();
            }, 3000);
        } catch (e: any) {
            setError(e.message || "Failed to trigger cycle");
            setTriggering(false);
        }
    };

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    const plan = data.plan || [];
    const confidence = data.confidence || 0;
    const model = data.model || 'llama3.2';
    const lastInference = data.last_inference || 0;
    const thoughts = data.recent_thoughts || [];

    const confColor = confidence > 75 ? 'text-[var(--nova-green)]' : confidence > 50 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-red)]';
    const confBars = Math.round((confidence / 100) * 10);
    const meterStr = '█'.repeat(Math.max(0, confBars)) + '░'.repeat(Math.max(0, 10 - confBars));

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">AI REASONING</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchReasoning} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            <div className="grid grid-cols-5 gap-6">
                {/* LEFT COLUMN */}
                <div className="col-span-3 flex flex-col gap-5">

                    {/* CONFIDENCE & MODEL INFO */}
                    <div className="nova-card p-4 flex flex-col gap-4">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-[var(--nova-muted)] tracking-widest uppercase">CONFIDENCE:</span>
                            <span className={`${confColor} tracking-[0.2em]`}>[{meterStr}] {confidence}%</span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] tracking-widest">
                            <div className="flex items-center gap-2">
                                <span className="text-[var(--nova-muted)] uppercase">MODEL:</span>
                                <span className="text-[var(--nova-accent)]">{model}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-[var(--nova-muted)] uppercase">LAST INFERENCE:</span>
                                <span>{lastInference}ms</span>
                            </div>
                        </div>
                    </div>

                    {/* CURRENT PLAN */}
                    <div className="nova-card p-4 flex flex-col gap-3">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2">┌─ CURRENT PLAN</div>
                        <div className="flex flex-col gap-2">
                            {plan.map((step: any, i: number) => {
                                const status = step.status || 'pending';
                                const color = status === 'completed' ? 'text-[var(--nova-green)]' : status === 'in_progress' ? 'text-[var(--nova-accent)]' : 'text-[var(--nova-muted)]';
                                const icon = status === 'completed' ? '✓' : status === 'in_progress' ? '◌' : '○';
                                const label = status.toUpperCase().replace('_', ' ');
                                return (
                                    <div key={i} className="flex justify-between items-center text-xs">
                                        <div className="flex items-center gap-2">
                                            <span className={color}>●</span>
                                            <span className="text-[var(--nova-text)] opacity-90">Step {i + 1}</span>
                                            <span className="text-[var(--nova-text)]">{step.action || step.name}</span>
                                        </div>
                                        <span className={`text-[10px] font-bold tracking-widest ${color}`}>[{label} {icon}]</span>
                                    </div>
                                )
                            })}
                            {plan.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-2">No active plan</div>}
                        </div>
                    </div>

                    {/* MANUAL TRIGGER */}
                    <button
                        onClick={handleTrigger}
                        disabled={triggering}
                        className={`nova-card !p-4 border ${triggering ? 'border-[var(--nova-accent)] text-[var(--nova-accent)] animate-pulse' : 'border-[rgba(0,255,204,0.3)] text-[var(--nova-text)] hover:bg-[var(--nova-surface2)]'} text-xs font-bold tracking-[0.2em] cursor-pointer transition-colors w-full text-left`}
                    >
                        {triggering ? 'REASONING IN PROGRESS...' : '▶ TRIGGER REASONING CYCLE'}
                    </button>

                </div>

                {/* RIGHT COLUMN */}
                <div className="col-span-2 flex flex-col gap-5">

                    {/* RECENT THOUGHTS */}
                    <div className="nova-card p-4 flex flex-col gap-3 flex-1">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">REASONING LOG</div>
                        <div className="flex-1 overflow-y-auto max-h-[250px] flex flex-col gap-2">
                            {thoughts.map((t: string, i: number) => (
                                <div key={i} className="flex items-start gap-2 animate-in fade-in duration-500">
                                    <span className="text-[var(--nova-accent)] text-[10px] mt-0.5">●</span>
                                    <span className="text-xs text-[var(--nova-muted)]">{t}</span>
                                </div>
                            ))}
                            {thoughts.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-4">Brain idle</div>}
                        </div>
                    </div>

                    {/* LIVE EVENT FEED */}
                    <div className="nova-card p-4 flex flex-col gap-3 flex-1">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">LIVE EVENT FEED</div>
                        <div className="flex-1 overflow-y-auto max-h-[200px] flex flex-col gap-1.5">
                            {liveEvents.map((evt, i) => (
                                <div key={i} className="flex items-center justify-between text-[10px] bg-black/40 px-2 py-1 rounded">
                                    <div className="flex items-center gap-2 truncate pr-2">
                                        <span className="text-[var(--nova-muted)]">{new Date().toLocaleTimeString(undefined, { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                                        <span className="text-[var(--nova-text)] uppercase">{evt.type}</span>
                                    </div>
                                    <span className="text-[var(--nova-accent)] shrink-0 opacity-70 truncate max-w-[80px]">{evt.source}</span>
                                </div>
                            ))}
                            {liveEvents.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-4">Waiting for telemetry...</div>}
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
