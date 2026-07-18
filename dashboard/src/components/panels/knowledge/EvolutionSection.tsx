interface Commit { hash: string; short_hash: string; timestamp: string; summary: string }
interface Entity { id: string; name: string }

interface Props {
    evolution?: Record<string, number>;
    recent_commits: Commit[];
    recent_entities: Entity[];
    onInspect: (id: string) => void;
    onNavigate: (view: string) => void;
}

export function EvolutionSection({ evolution, recent_commits, recent_entities, onInspect, onNavigate }: Props) {
    return (
        <div className="space-y-3 shrink-0 pb-4">
            {/* Memory Evolution Strip */}
            {evolution && (
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-3">
                    <h3 className="text-[10px] font-mono tracking-wider text-[var(--nova-muted)] uppercase font-bold mb-2">Memory Evolution (Since Previous Window)</h3>
                    <div className="grid grid-cols-5 gap-2 text-center font-mono">
                        <div className="bg-[var(--nova-surface2)]/50 p-1.5 rounded"><span className="text-[8px] text-[var(--nova-muted)] block uppercase">Added</span><span className="text-xs font-bold text-[var(--nova-accent)]">+{evolution.knowledge_added ?? 0}</span></div>
                        <div className="bg-[var(--nova-surface2)]/50 p-1.5 rounded"><span className="text-[8px] text-[var(--nova-muted)] block uppercase">Updated</span><span className="text-xs font-bold text-[var(--nova-amber)]">~{evolution.knowledge_updated ?? 0}</span></div>
                        <div className="bg-[var(--nova-surface2)]/50 p-1.5 rounded"><span className="text-[8px] text-[var(--nova-muted)] block uppercase">Superseded</span><span className="text-xs font-bold text-[#60a5fa]">{evolution.knowledge_superseded ?? 0}</span></div>
                        <div className="bg-[var(--nova-surface2)]/50 p-1.5 rounded"><span className="text-[8px] text-[var(--nova-muted)] block uppercase">Archived</span><span className="text-xs font-bold text-[#a78bfa]">{evolution.knowledge_archived ?? 0}</span></div>
                        <div className="bg-[var(--nova-surface2)]/50 p-1.5 rounded"><span className="text-[8px] text-[var(--nova-muted)] block uppercase">Invalidated</span><span className="text-xs font-bold text-[var(--nova-red)]">-{evolution.knowledge_invalidated ?? 0}</span></div>
                    </div>
                </div>
            )}

            {/* Two column recent lists */}
            <div className="grid grid-cols-2 gap-3 min-h-[200px]">
                {/* Recent Commits */}
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-3 flex flex-col overflow-hidden">
                    <div className="flex justify-between items-center mb-2 pb-1 border-b border-[var(--nova-border)]/50">
                        <h3 className="text-[10px] font-mono tracking-wider text-[var(--nova-accent)] uppercase font-bold">Recent Commits</h3>
                        <button onClick={() => onNavigate("commits")} className="text-[9px] font-mono text-[var(--nova-muted)] hover:text-[var(--nova-accent)]">View All →</button>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-1.5 max-h-[160px]">
                        {recent_commits.map((c, i) => (
                            <button key={i} onClick={() => onInspect(c.hash)} className="w-full text-left p-2 rounded bg-[var(--nova-surface2)]/50 hover:bg-[var(--nova-accent)]/5 border border-transparent hover:border-[var(--nova-accent)]/20 transition-all">
                                <div className="flex justify-between text-[10px] font-mono text-[var(--nova-accent)]">
                                    <span>{c.short_hash}</span>
                                    <span className="text-[9px] text-[var(--nova-muted)]">{c.timestamp ? c.timestamp.split(" ")[1] : ""}</span>
                                </div>
                                <div className="text-[10px] font-mono text-[var(--nova-text)] truncate mt-0.5">{c.summary}</div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Recently Discovered Entities */}
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-3 flex flex-col overflow-hidden">
                    <div className="flex justify-between items-center mb-2 pb-1 border-b border-[var(--nova-border)]/50">
                        <h3 className="text-[10px] font-mono tracking-wider text-[#a78bfa] uppercase font-bold">Recent Entities</h3>
                        <button onClick={() => onNavigate("explorer")} className="text-[9px] font-mono text-[var(--nova-muted)] hover:text-[#a78bfa]">Explore →</button>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-1.5 max-h-[160px]">
                        {recent_entities.map((e, i) => (
                            <button key={i} onClick={() => onInspect(e.id)} className="w-full text-left p-2 rounded bg-[var(--nova-surface2)]/50 hover:bg-[#a78bfa]/5 border border-transparent hover:border-[#a78bfa]/20 transition-all flex items-center justify-between">
                                <span className="text-[10px] font-mono text-[#a78bfa] truncate">{e.name}</span>
                                <span className="text-[9px] font-mono text-[var(--nova-muted)]">entity</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
