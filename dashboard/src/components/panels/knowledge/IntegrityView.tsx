import { useState, useEffect } from "react";
import { useApi } from "../../../hooks/useApi";

function Skeleton({ className = "" }: { className?: string }) {
    return <div className={`bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg animate-pulse ${className}`} />;
}

function ErrorCard({ msg, onRetry }: { msg: string; onRetry?: () => void }) {
    return (
        <div className="bg-[var(--nova-red)]/10 border border-[var(--nova-red)]/30 rounded p-4 text-center">
            <p className="text-[var(--nova-red)] font-mono text-sm mb-3">{msg}</p>
            {onRetry && (
                <button onClick={onRetry} className="text-xs bg-[var(--nova-red)]/20 text-[var(--nova-red)] px-3 py-1.5 rounded hover:bg-[var(--nova-red)]/30 transition-colors">
                    RETRY
                </button>
            )}
        </div>
    );
}

interface IntegritySnapshot {
    snapshot_id: string;
    generated_at: string;
    commit_range: string[];
    snapshot_hash: string;
    health_score: number;
    evidence_coverage: number;
    freshness: number;
    consistency: number;
    contradictions: Array<{
        type: string;
        objects_involved: string[];
        supporting_evidence: string;
        timeline: string[];
        confidence: number | null;
    }>;
    profiles: Record<string, {
        node_id: string;
        type: string;
        evidence_strength: number;
        evidence_count: number;
        provenance_depth: number;
        temporal_freshness: string;
        review_status: string;
        compiler_confidence: number | null;
        knowledge_status: string;
        integrity_flags: string[];
    }>;
    lonely_knowledge: Array<{
        id: string;
        type: string;
        title: string;
        reason: string;
        timestamp: string;
    }>;
}

export function IntegrityView({ onInspect }: { onInspect?: (id: string) => void }) {
    const { get } = useApi();
    const [snap, setSnap] = useState<IntegritySnapshot | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        get<IntegritySnapshot>("/api/knowledge/integrity/snapshot")
            .then(data => { setSnap(data); setError(""); })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, [get]);

    if (loading) return <div className="p-4 flex flex-col gap-4">{[1, 2, 3].map(i => <Skeleton key={i} className="h-32" />)}</div>;
    if (error || !snap) return <div className="p-4"><ErrorCard msg={error || "Failed to load snapshot"} /></div>;

    const issues: any[] = [];
    Object.values(snap.profiles || {}).forEach(p => {
        p.integrity_flags.forEach(f => {
            if (!f.startsWith("Lonely")) {
                issues.push({ ...p, flag: f });
            }
        });
    });

    return (
        <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-mono text-[var(--nova-accent)] tracking-widest uppercase">Knowledge Integrity Engine</h2>
                    <p className="text-[10px] font-mono text-[var(--nova-muted)] uppercase tracking-wider mt-1">
                        SNAPSHOT: {snap.snapshot_id} • EVALUATED COMMITS: {snap.commit_range[0].substring(0, 8)}...{snap.commit_range[1].substring(0, 8)}
                    </p>
                </div>
                <div className={`px-4 py-2 rounded border font-mono tracking-widest uppercase flex flex-col items-end ${
                    snap.health_score >= 80 ? 'bg-[var(--nova-green)]/10 text-[var(--nova-green)] border-[var(--nova-green)]' :
                    snap.health_score >= 50 ? 'bg-[var(--nova-amber)]/10 text-[var(--nova-amber)] border-[var(--nova-amber)]' :
                    'bg-[var(--nova-red)]/10 text-[var(--nova-red)] border-[var(--nova-red)]'
                }`}>
                    <span className="text-[10px] opacity-70">Global Health</span>
                    <span className="text-2xl font-bold">{snap.health_score.toFixed(1)}</span>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-4">
                    <span className="text-[10px] font-mono text-[var(--nova-muted)] uppercase tracking-widest block mb-2">Evidence Coverage</span>
                    <span className="text-xl font-mono text-[var(--nova-text)]">{snap.evidence_coverage.toFixed(1)}</span>
                </div>
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-4">
                    <span className="text-[10px] font-mono text-[var(--nova-muted)] uppercase tracking-widest block mb-2">Temporal Freshness</span>
                    <span className="text-xl font-mono text-[var(--nova-text)]">{snap.freshness.toFixed(1)}</span>
                </div>
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-4">
                    <span className="text-[10px] font-mono text-[var(--nova-muted)] uppercase tracking-widest block mb-2">Consistency Index</span>
                    <span className="text-xl font-mono text-[var(--nova-text)]">{snap.consistency.toFixed(1)}</span>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
                <div className="flex flex-col gap-4">
                    <h3 className="text-xs font-mono text-[var(--nova-muted)] tracking-widest uppercase border-b border-[var(--nova-border)] pb-2">Contradiction Report</h3>
                    {snap.contradictions.length === 0 ? (
                        <div className="text-[10px] font-mono text-[var(--nova-green)] bg-[var(--nova-green)]/10 p-3 rounded border border-[var(--nova-green)]/30">
                            Zero explicit cross-type contradictions detected.
                        </div>
                    ) : (
                        <div className="flex flex-col gap-3">
                            {snap.contradictions.map((c, i) => (
                                <div key={i} className="bg-[var(--nova-red)]/5 border border-[var(--nova-red)]/30 rounded p-3 text-xs font-mono">
                                    <div className="text-[var(--nova-red)] font-bold mb-2">{c.type}</div>
                                    <div className="flex gap-2 mb-2">
                                        {c.objects_involved.map(oid => (
                                            <button key={oid} onClick={() => onInspect?.(oid)} className="text-left text-[10px] bg-[var(--nova-surface2)] px-2 py-1 rounded border border-[var(--nova-border)] hover:border-[var(--nova-accent)] transition-colors">
                                                {oid}
                                            </button>
                                        ))}
                                    </div>
                                    <div className="text-[10px] text-[var(--nova-muted)]">Confidence: {c.confidence != null ? (c.confidence * 100).toFixed(0) + '%' : 'Not recorded'}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="flex flex-col gap-4">
                    <h3 className="text-xs font-mono text-[var(--nova-muted)] tracking-widest uppercase border-b border-[var(--nova-border)] pb-2">Lonely Knowledge</h3>
                    {snap.lonely_knowledge.length === 0 ? (
                        <div className="text-[10px] font-mono text-[var(--nova-green)] bg-[var(--nova-green)]/10 p-3 rounded border border-[var(--nova-green)]/30">
                            All goals, decisions, and risks are properly linked to execution nodes.
                        </div>
                    ) : (
                        <div className="flex flex-col gap-2">
                            {snap.lonely_knowledge.map((lk, i) => (
                                <div key={i} className="bg-[var(--nova-amber)]/5 border border-[var(--nova-amber)]/30 rounded p-3 text-xs font-mono flex items-start justify-between group">
                                    <div>
                                        <div className="text-[var(--nova-amber)] font-bold mb-1">{lk.type}</div>
                                        <div className="text-[var(--nova-text)] opacity-90">{lk.title}</div>
                                        <div className="text-[10px] text-[var(--nova-muted)] mt-1">{lk.reason}</div>
                                    </div>
                                    <button onClick={() => onInspect?.(lk.id)} className="text-[10px] text-[var(--nova-accent)] opacity-0 group-hover:opacity-100 transition-opacity">
                                        Inspect
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex flex-col gap-4 mt-4">
                <h3 className="text-xs font-mono text-[var(--nova-muted)] tracking-widest uppercase border-b border-[var(--nova-border)] pb-2">Evidence & Quality Profiler</h3>
                <div className="grid grid-cols-2 gap-4">
                    {/* Weak Evidence */}
                    <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded flex flex-col max-h-[300px]">
                        <div className="p-3 border-b border-[var(--nova-border)] text-[10px] font-mono text-[var(--nova-amber)] uppercase font-bold bg-[var(--nova-amber)]/5">
                            Weak Evidence / Integrity Flags ({issues.length})
                        </div>
                        <div className="overflow-y-auto p-2 flex flex-col gap-2">
                            {issues.map((iss, i) => (
                                <div key={i} className="flex flex-col p-2 bg-[var(--nova-surface2)] rounded border border-[var(--nova-border)]">
                                    <div className="flex items-center justify-between">
                                        <span className="text-[10px] font-mono text-[var(--nova-accent)]">{iss.type}</span>
                                        <span className="text-[9px] font-mono text-[var(--nova-muted)]">STR: {iss.evidence_strength}</span>
                                    </div>
                                    <span className="text-xs font-mono text-[var(--nova-text)] mt-1">{iss.flag}</span>
                                    <button onClick={() => onInspect?.(iss.node_id)} className="text-[9px] font-mono text-[var(--nova-accent)] text-left mt-2 hover:underline">
                                        {iss.node_id}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                    {/* Knowledge Status Distribution */}
                    <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-4 flex flex-col gap-3">
                        <div className="text-[10px] font-mono text-[var(--nova-muted)] uppercase font-bold tracking-widest mb-2">Knowledge Status Ledger</div>
                        {["Verified", "EvidenceStrong", "Supported", "Emerging", "Stale", "Superseded", "Conflicted", "Deprecated", "Archived"].map(st => {
                            const count = Object.values(snap.profiles).filter(p => p.knowledge_status === st).length;
                            if (count === 0) return null;
                            return (
                                <div key={st} className="flex items-center justify-between text-xs font-mono">
                                    <div className="flex items-center gap-2">
                                        <span className={`w-2 h-2 rounded-full ${st === 'Verified' ? 'bg-[var(--nova-green)]' : st === 'EvidenceStrong' ? 'bg-[var(--nova-green)] opacity-70' : st === 'Stale' ? 'bg-[var(--nova-amber)]' : 'bg-[var(--nova-muted)]'}`} />
                                        <span className="text-[var(--nova-text)] opacity-80">{st}</span>
                                    </div>
                                    <span className="text-[var(--nova-muted)]">{count}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
