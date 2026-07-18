import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../../hooks/useApi";

interface ExploreGraph {
    artifacts: { id: string; adjacent_observation: string }[];
    observations: { id: string; op: string; dialect: string; content: string; semantic_type?: string; adjacent_commit: string; adjacent_artifact: string; adjacent_entity: string }[];
    entities: { id: string; adjacent_observations: string[] }[];
    commits: { id: string; short_id: string; timestamp: string; adjacent_observations: string[] }[];
}

interface Props {
    onInspect: (id: string) => void;
}

function ColumnHeader({ title, count }: { title: string; count: number }) {
    return (
        <div className="p-2 border-b border-[var(--nova-border)]/50 bg-[var(--nova-surface2)]/50 flex justify-between items-center">
            <h3 className="text-[9px] font-mono tracking-[0.2em] text-[var(--nova-accent)] uppercase">{title}</h3>
            <span className="text-[9px] font-mono text-[var(--nova-muted)]">{count}</span>
        </div>
    );
}

export function ExplorerView({ onInspect }: Props) {
    const { get } = useApi();
    const [graph, setGraph] = useState<ExploreGraph | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [filter, setFilter] = useState("ALL");

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await get<ExploreGraph>("/api/knowledge/explore");
            setGraph(data);
            setError("");
        } catch (e: any) {
            setError(e.message ?? "Failed to load graph");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => { load(); }, [load]);

    if (loading) return <div className="p-4 text-xs font-mono text-[var(--nova-muted)] animate-pulse">Loading knowledge graph...</div>;
    if (error) return <div className="p-4 text-xs font-mono text-[var(--nova-red)]">{error} <button onClick={load} className="ml-2 text-[var(--nova-accent)] hover:underline">Retry</button></div>;
    if (!graph) return null;

    return (
        <div className="flex flex-col h-full">
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase">Hierarchical Knowledge Browser</h2>
                <button onClick={load} className="text-[9px] font-mono text-[var(--nova-muted)] hover:text-[var(--nova-accent)] transition-colors px-2 py-1 border border-[var(--nova-border)] rounded">⟳ Refresh</button>
            </div>
            <p className="text-[10px] font-mono text-[var(--nova-muted)] mb-2">Navigate: Artifact → Knowledge → Entity → Commit. Click any object to inspect.</p>
            <div className="flex gap-1 overflow-x-auto pb-2 mb-2">
                {["ALL", "DECISION", "ASSUMPTION", "RISK", "GOAL", "QUESTION", "PRINCIPLE", "TRADEOFF", "ALTERNATIVE", "CONSTRAINT", "ACTION_ITEM"].map(st => (
                    <button key={st} onClick={() => setFilter(st)}
                        className={`px-2 py-0.5 rounded text-[9px] font-mono whitespace-nowrap border ${filter === st ? "bg-[var(--nova-accent)]/20 text-[var(--nova-accent)] border-[var(--nova-accent)] font-bold" : "bg-[var(--nova-surface2)] text-[var(--nova-muted)] border-[var(--nova-border)] hover:text-[var(--nova-text)]"}`}>
                        {st}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-4 gap-2 flex-1 min-h-0">
                {/* Artifacts */}
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg flex flex-col overflow-hidden">
                    <ColumnHeader title="Artifacts" count={graph.artifacts.length} />
                    <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                        {graph.artifacts.length === 0 && <div className="text-[10px] text-[var(--nova-muted)] p-2 text-center">No artifacts</div>}
                        {graph.artifacts.map((a) => (
                            <button key={a.id} onClick={() => onInspect(a.id)}
                                className="w-full text-left p-2 rounded text-[10px] font-mono text-[var(--nova-text)] hover:bg-[var(--nova-accent)]/5 hover:text-[var(--nova-accent)] border border-transparent hover:border-[var(--nova-accent)]/20 transition-colors truncate">
                                {a.id}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Observations */}
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg flex flex-col overflow-hidden">
                    {(() => {
                        const obsList = filter === "ALL" ? graph.observations : graph.observations.filter(o => (o.semantic_type || "OBSERVATION").toUpperCase() === filter);
                        return (
                            <>
                                <ColumnHeader title="Knowledge" count={obsList.length} />
                                <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                                    {obsList.length === 0 && <div className="text-[10px] text-[var(--nova-muted)] p-2 text-center">No matching objects</div>}
                                    {obsList.map((o) => (
                                        <button key={o.id} onClick={() => onInspect(o.id)}
                                            className="w-full text-left p-2 rounded text-[10px] font-mono hover:bg-[#60a5fa]/5 border border-transparent hover:border-[#60a5fa]/20 transition-colors">
                                            <div className="text-[#60a5fa] truncate">{o.id}</div>
                                            <div className="text-[var(--nova-muted)] truncate mt-0.5">{o.semantic_type || o.dialect}:{o.op}</div>
                                        </button>
                                    ))}
                                </div>
                            </>
                        );
                    })()}
                </div>

                {/* Entities */}
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg flex flex-col overflow-hidden">
                    <ColumnHeader title="Entities" count={graph.entities.length} />
                    <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                        {graph.entities.length === 0 && <div className="text-[10px] text-[var(--nova-muted)] p-2 text-center">No entities</div>}
                        {graph.entities.map((e) => (
                            <button key={e.id} onClick={() => onInspect(e.id)}
                                className="w-full text-left p-2 rounded text-[10px] font-mono text-[#a78bfa] hover:bg-[#a78bfa]/5 border border-transparent hover:border-[#a78bfa]/20 transition-colors">
                                <div className="truncate">{e.id}</div>
                                <div className="text-[var(--nova-muted)] mt-0.5">{e.adjacent_observations.length} obs</div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Commits */}
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg flex flex-col overflow-hidden">
                    <ColumnHeader title="Commits" count={graph.commits.length} />
                    <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                        {graph.commits.length === 0 && <div className="text-[10px] text-[var(--nova-muted)] p-2 text-center">No commits</div>}
                        {graph.commits.map((c) => (
                            <button key={c.id} onClick={() => onInspect(c.id)}
                                className="w-full text-left p-2 rounded text-[10px] font-mono text-[var(--nova-accent)] hover:bg-[var(--nova-accent)]/5 border border-transparent hover:border-[var(--nova-accent)]/20 transition-colors">
                                <div className="truncate">{c.short_id}</div>
                                <div className="text-[var(--nova-muted)] mt-0.5">{c.adjacent_observations.length} nodes</div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
