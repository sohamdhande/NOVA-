import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../../hooks/useApi";

interface TimelineEvent {
    timestamp: string;
    type: string;
    id: string;
    full_id: string;
    summary: string;
}

interface Props {
    onInspect: (id: string) => void;
}

export function TimelineView({ onInspect }: Props) {
    const { get } = useApi();
    const [events, setEvents] = useState<TimelineEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("");

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await get<TimelineEvent[]>("/api/knowledge/timeline");
            setEvents(data.reverse()); // newest first
        } catch { /* ignore */ }
        finally { setLoading(false); }
    }, [get]);

    useEffect(() => { load(); }, [load]);

    const filtered = filter
        ? events.filter(e => e.type.toLowerCase().includes(filter.toLowerCase()) || e.summary.toLowerCase().includes(filter.toLowerCase()))
        : events;

    if (loading) return <div className="p-4 text-xs font-mono text-[var(--nova-muted)] animate-pulse">Loading timeline...</div>;

    return (
        <div className="flex flex-col h-full">
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase">Activity Timeline</h2>
                <button onClick={load} className="text-[9px] font-mono text-[var(--nova-muted)] hover:text-[var(--nova-accent)] transition-colors px-2 py-1 border border-[var(--nova-border)] rounded">⟳ Refresh</button>
            </div>

            <input
                value={filter}
                onChange={e => setFilter(e.target.value)}
                placeholder="Filter events..."
                className="mb-3 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-3 py-1.5 text-xs font-mono text-[var(--nova-text)] focus:outline-none focus:border-[var(--nova-accent)] placeholder:text-[var(--nova-muted)]"
            />

            <div className="flex-1 overflow-y-auto">
                {filtered.length === 0 ? (
                    <div className="text-xs font-mono text-[var(--nova-muted)] text-center mt-8">No activity recorded.</div>
                ) : (
                    <div className="relative pl-4 border-l border-[var(--nova-border)]/50 space-y-1">
                        {filtered.map((ev, i) => (
                            <button
                                key={i}
                                onClick={() => onInspect(ev.full_id)}
                                className="w-full text-left relative p-2.5 rounded hover:bg-[var(--nova-accent)]/5 transition-colors group"
                            >
                                <div className="absolute -left-[21px] top-3.5 w-2 h-2 rounded-full bg-[var(--nova-accent)]/40 group-hover:bg-[var(--nova-accent)] transition-colors" />
                                <div className="flex items-center gap-3 mb-0.5">
                                    <span className="text-[10px] font-mono text-[var(--nova-muted)]">{new Date(ev.timestamp).toLocaleString()}</span>
                                    <span className="text-[9px] font-mono tracking-wider text-[var(--nova-accent)] uppercase bg-[var(--nova-accent)]/10 px-1.5 py-0.5 rounded">{ev.type}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-mono text-[var(--nova-accent)]">{ev.id}</span>
                                    <span className="text-xs font-mono text-[var(--nova-text)]">{ev.summary}</span>
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
