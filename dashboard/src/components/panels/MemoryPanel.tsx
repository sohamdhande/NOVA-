import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function MemoryPanel() {
    const { get } = useApi();
    const [activeTab, setActiveTab] = useState<'EVENTS' | 'DECISIONS' | 'REFLECTIONS'>('EVENTS');
    const [events, setEvents] = useState<any[]>([]);
    const [decisions, setDecisions] = useState<any[]>([]);
    const [reflections, setReflections] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [searchFilter, setSearchFilter] = useState("");

    // Expanded row state for events
    const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

    const fetchMemory = useCallback(async () => {
        try {
            // Memory endpoint typically returns a mix or relies on query params
            // Adjust to your actual backend logic as necessary
            const res = await get<any>('/api/memory').catch(() => ({ events: [], decisions: [], reflections: [] }));
            setEvents(res.events || []);
            setDecisions(res.decisions || []);
            setReflections(res.reflections || []);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch memory data");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchMemory();
        const iv = setInterval(fetchMemory, 30000);
        return () => clearInterval(iv);
    }, [fetchMemory]);

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    const filteredEvents = events.filter(e =>
        (e.type || '').toLowerCase().includes(searchFilter.toLowerCase()) ||
        (e.source || '').toLowerCase().includes(searchFilter.toLowerCase())
    );

    const todayDecisions = decisions.filter(d => new Date(d.timestamp).toDateString() === new Date().toDateString()).length;
    const avgScore = reflections.length > 0 ? Math.round(reflections.reduce((acc, r) => acc + (r.score || 0), 0) / reflections.length) : 0;

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">MEMORY VIEWER</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchMemory} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            {/* STATS BAR */}
            <div className="grid grid-cols-3 gap-4">
                <div className="nova-card flex flex-col items-center justify-center p-3">
                    <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">TOTAL EVENTS</span>
                    <span className="text-xl text-[var(--nova-accent)]">{events.length}</span>
                </div>
                <div className="nova-card flex flex-col items-center justify-center p-3">
                    <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">DECISIONS TODAY</span>
                    <span className="text-xl text-[var(--nova-green)]">{todayDecisions || 0}</span>
                </div>
                <div className="nova-card flex flex-col items-center justify-center p-3">
                    <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">AVG SCORE</span>
                    <span className={`text-xl ${avgScore >= 80 ? 'text-[var(--nova-green)]' : avgScore >= 60 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-red)]'}`}>{avgScore || '--'}</span>
                </div>
            </div>

            {/* TAB BAR */}
            <div className="flex gap-6 border-b border-[var(--nova-border)] text-xs font-bold tracking-widest mt-2">
                {['EVENTS', 'DECISIONS', 'REFLECTIONS'].map(t => (
                    <button
                        key={t}
                        onClick={() => setActiveTab(t as any)}
                        className={`pb-2 transition-colors cursor-pointer ${activeTab === t ? 'text-[var(--nova-accent)] border-b-2 border-[var(--nova-accent)]' : 'text-[var(--nova-muted)] hover:text-[#fff]'}`}
                    >
                        {t}
                    </button>
                ))}
            </div>

            {/* TAB CONTENT */}
            <div className="flex-1 flex flex-col gap-4">
                {activeTab === 'EVENTS' && (
                    <>
                        <input
                            value={searchFilter}
                            onChange={e => setSearchFilter(e.target.value)}
                            placeholder="Filter by type, source..."
                            className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-3 py-2 text-xs font-mono outline-none focus:border-[var(--nova-accent)] w-full transition-colors"
                        />
                        <div className="nova-card overflow-hidden flex flex-col flex-1">
                            <div className="grid grid-cols-[140px_100px_1fr_80px] text-[10px] text-[var(--nova-muted)] bg-[var(--nova-surface2)] p-3 tracking-widest uppercase border-b border-[var(--nova-border)]">
                                <span>TIMESTAMP</span>
                                <span>SOURCE</span>
                                <span>TYPE</span>
                                <span>PRIORITY</span>
                            </div>
                            <div className="overflow-y-auto max-h-[400px]">
                                {filteredEvents.map((evt, i) => {
                                    const pColor = evt.priority >= 7 ? 'text-[var(--nova-red)]' : evt.priority >= 4 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-muted)]';
                                    const isExpanded = expandedEventId === evt.id;
                                    return (
                                        <div key={evt.id || i} className="flex flex-col border-b border-[var(--nova-border)] last:border-0 hover:bg-[var(--nova-bg)] transition-colors">
                                            <div
                                                className={`grid grid-cols-[140px_100px_1fr_80px] text-xs p-3 cursor-pointer items-center ${i % 2 === 0 ? 'bg-transparent' : 'bg-[var(--nova-surface)]'}`}
                                                onClick={() => setExpandedEventId(isExpanded ? null : evt.id)}
                                            >
                                                <span className="text-[var(--nova-muted)]">{new Date(evt.timestamp).toLocaleString()}</span>
                                                <span className="text-[var(--nova-text)] truncate">{evt.source}</span>
                                                <span className="text-[var(--nova-accent)] truncate">{evt.type}</span>
                                                <span className={`font-bold ${pColor}`}>{evt.priority || 0}</span>
                                            </div>
                                            {isExpanded && (
                                                <div className="p-3 bg-black/60 text-[10px] text-[var(--nova-green)] overflow-x-auto border-t border-[var(--nova-border)]/50">
                                                    <pre>{JSON.stringify(evt.payload || evt, null, 2)}</pre>
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}
                                {filteredEvents.length === 0 && <div className="p-6 text-center text-xs text-[var(--nova-muted)]">No events match</div>}
                            </div>
                        </div>
                    </>
                )}

                {activeTab === 'DECISIONS' && (
                    <div className="grid grid-cols-2 gap-4">
                        {decisions.map((d, i) => {
                            const badgeColor = d.outcome === 'success' ? 'text-[var(--nova-green)]' : d.outcome === 'failed' ? 'text-[var(--nova-red)]' : 'text-[var(--nova-amber)]';
                            return (
                                <div key={i} className="nova-card p-4 border-[rgba(0,255,204,0.1)] flex flex-col gap-2">
                                    <div className="flex justify-between border-b border-[rgba(0,255,204,0.1)] pb-2">
                                        <span className="text-[10px] text-[var(--nova-muted)]">┌─ DECISION</span>
                                        <span className="text-[10px] text-[var(--nova-text)]">{new Date(d.timestamp).toLocaleString()}</span>
                                    </div>
                                    <div className="text-xs text-[var(--nova-text)] mt-1 opacity-90">{d.description || d.action}</div>
                                    <div className={`text-[10px] mt-2 font-bold ${badgeColor} self-end tracking-wider uppercase`}>
                                        Outcome: {d.outcome || 'PENDING'} {d.outcome === 'success' ? '✓' : d.outcome === 'failed' ? '✗' : '●'}
                                    </div>
                                </div>
                            )
                        })}
                        {decisions.length === 0 && <div className="col-span-2 text-center text-xs text-[var(--nova-muted)] py-6">No decisions logged.</div>}
                    </div>
                )}

                {activeTab === 'REFLECTIONS' && (
                    <div className="flex flex-col gap-4">
                        {reflections.map((r, i) => {
                            const score = r.score || 0;
                            const scoreColor = score >= 80 ? 'text-[var(--nova-green)]' : score >= 60 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-red)]';
                            return (
                                <div key={i} className="nova-card p-4 border-[rgba(0,255,204,0.1)] flex flex-col gap-3">
                                    <div className="flex justify-between border-b border-[rgba(0,255,204,0.1)] pb-2 items-center">
                                        <span className="text-[10px] text-[var(--nova-accent)] tracking-widest">┌─ DAILY REFLECTION</span>
                                        <span className={`text-xs font-bold ${scoreColor}`}>Score: {score}</span>
                                    </div>
                                    <div className="text-[10px] text-[var(--nova-muted)] font-bold">{new Date(r.date || r.timestamp).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}</div>
                                    <div className="text-xs text-[var(--nova-text)] whitespace-pre-wrap leading-relaxed opacity-90">{r.summary || r.text}</div>
                                </div>
                            )
                        })}
                        {reflections.length === 0 && <div className="text-center text-xs text-[var(--nova-muted)] py-6">No reflections logged.</div>}
                    </div>
                )}
            </div>
        </div>
    );
}
