interface Stats {
    commits: number;
    artifacts: number;
    entities: number;
    observations: number;
    compiler_status: string;
}

interface Snapshot {
    snapshot_id: string;
    generated_at: string;
    report_hash: string;
}

interface Props {
    stats: Stats;
    snapshot?: Snapshot;
    onNavigate: (view: string) => void;
}

function StatCard({ label, val, color }: { label: string; val: number | string; color: string }) {
    return (
        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-3 flex flex-col justify-between">
            <span className="text-[9px] font-mono tracking-widest text-[var(--nova-muted)] uppercase">{label}</span>
            <span className={`text-xl font-mono font-bold mt-1 ${color}`}>{val}</span>
        </div>
    );
}

export function ChronicleOverview({ stats, snapshot, onNavigate }: Props) {
    return (
        <div className="flex flex-col space-y-4 shrink-0">
            {/* Compiler Status & Header */}
            <div className="bg-[rgba(0,255,204,0.03)] border border-[var(--nova-accent)]/30 rounded-lg p-3 flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-2">
                        <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase">Personal Knowledge Machine</h2>
                        {snapshot && (
                            <span className="bg-[var(--nova-surface2)] text-[9px] font-mono px-2 py-0.5 rounded border border-[var(--nova-accent)]/40 text-[var(--nova-accent)]" title={`SHA256: ${snapshot.report_hash}`}>
                                {snapshot.snapshot_id}
                            </span>
                        )}
                    </div>
                    <p className="text-[10px] font-mono text-[var(--nova-muted)] mt-0.5">Every organizational artifact compiled into trusted, immutable knowledge commits.</p>
                </div>
                <div className="flex items-center gap-2 bg-[var(--nova-surface)] px-2.5 py-1 rounded border border-[var(--nova-border)]">
                    <span className="w-2 h-2 rounded-full bg-[var(--nova-accent)] animate-pulse" />
                    <span className="text-[9px] font-mono text-[var(--nova-text)]">{stats.compiler_status}</span>
                </div>
            </div>

            {/* Statistics Grid */}
            <div className="grid grid-cols-4 gap-3">
                <StatCard label="Knowledge Commits" val={stats.commits} color="text-[var(--nova-accent)]" />
                <StatCard label="Compiled Artifacts" val={stats.artifacts} color="text-[var(--nova-amber)]" />
                <StatCard label="Discovered Entities" val={stats.entities} color="text-[#a78bfa]" />
                <StatCard label="KIR Observations" val={stats.observations} color="text-[#60a5fa]" />
            </div>

            {/* Quick Action Banner */}
            <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-3 flex items-center justify-between">
                <span className="text-xs font-mono text-[var(--nova-text)]">Ready to ingest new documents or Slack exports?</span>
                <button
                    onClick={() => onNavigate("new_artifact")}
                    className="bg-[var(--nova-accent)] text-black font-bold px-3 py-1.5 rounded text-[10px] font-mono uppercase tracking-wider hover:brightness-110 transition-all"
                >
                    + New Artifact
                </button>
            </div>
        </div>
    );
}
