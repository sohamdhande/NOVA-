import { useState } from "react";

export interface HealthData {
    health_score: number;
    health_zone: string;
    total_issues: number;
    unresolved_questions: any[];
    open_risks: any[];
    unsupported_decisions: any[];
    weak_evidence: any[];
    stale_assumptions: any[];
    goals_without_progress: any[];
    action_items_without_owners: any[];
}

interface Props {
    health: HealthData | null;
    onInspect: (id: string) => void;
}

function SignalCategory({ label, items, color, onInspect }: { label: string; items: any[]; color: string; onInspect: (id: string) => void }) {
    const [open, setOpen] = useState(false);
    if (!items || items.length === 0) return null;

    return (
        <div className="border border-[var(--nova-border)]/60 rounded p-2 bg-[var(--nova-surface2)]/20">
            <button onClick={() => setOpen(!open)} className="w-full flex justify-between items-center text-left">
                <span className={`text-[10px] font-mono uppercase font-bold ${color}`}>
                    ● {label} ({items.length})
                </span>
                <span className="text-[9px] font-mono text-[var(--nova-muted)]">{open ? "Hide" : "Review"}</span>
            </button>
            {open && (
                <div className="mt-2 space-y-1 pl-2 border-l border-[var(--nova-border)]">
                    {items.map((it, idx) => (
                        <div key={idx} onClick={() => onInspect(it.id)} className="text-[9px] font-mono text-[var(--nova-text)] hover:text-[var(--nova-accent)] cursor-pointer truncate flex justify-between">
                            <span>{it.title}</span>
                            {it.health_reason && <span className="text-[8px] text-[var(--nova-red)] ml-2 shrink-0">[{it.health_reason}]</span>}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export function KnowledgeHealthSection({ health, onInspect }: Props) {
    if (!health) return null;

    const zoneColors: Record<string, string> = {
        ROBUST: "text-[var(--nova-accent)] border-[var(--nova-accent)]/30 bg-[var(--nova-accent)]/5",
        STABLE: "text-[var(--nova-amber)] border-[var(--nova-amber)]/30 bg-[var(--nova-amber)]/5",
        DEGRADED: "text-[#fb923c] border-[#fb923c]/30 bg-[#fb923c]/5",
        CRITICAL: "text-[var(--nova-red)] border-[var(--nova-red)]/30 bg-[var(--nova-red)]/5"
    };

    const colorClass = zoneColors[health.health_zone] || zoneColors.STABLE;

    return (
        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-3 space-y-3 shrink-0">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-xs font-mono tracking-wider text-[var(--nova-text)] uppercase font-bold flex items-center gap-2">
                        <span>Knowledge Base Health</span>
                        <span className={`text-[9px] font-mono px-2 py-0.5 rounded border ${colorClass}`}>
                            {health.health_zone} ({health.health_score}%)
                        </span>
                    </h3>
                    <p className="text-[9px] font-mono text-[var(--nova-muted)] mt-0.5">Continuous compiler liveness checking. Monitoring unsupported decisions & weak evidence.</p>
                </div>
                <span className="text-[10px] font-mono font-bold text-[var(--nova-muted)]">{health.total_issues} Signals</span>
            </div>

            {health.total_issues === 0 ? (
                <div className="p-3 rounded bg-[var(--nova-accent)]/5 border border-[var(--nova-accent)]/20 text-[10px] font-mono text-[var(--nova-accent)] text-center">
                    ✓ All knowledge base health checks passing nominal. Zero stale assumptions or weak evidence spans.
                </div>
            ) : (
                <div className="grid grid-cols-2 gap-2">
                    <SignalCategory label="Unresolved Questions" items={health.unresolved_questions} color="text-[var(--nova-amber)]" onInspect={onInspect} />
                    <SignalCategory label="Open Risks" items={health.open_risks} color="text-[var(--nova-red)]" onInspect={onInspect} />
                    <SignalCategory label="Unsupported Decisions" items={health.unsupported_decisions} color="text-[#f43f5e]" onInspect={onInspect} />
                    <SignalCategory label="Weak Evidence Spans" items={health.weak_evidence} color="text-[#fb923c]" onInspect={onInspect} />
                    <SignalCategory label="Stale Assumptions (>30d)" items={health.stale_assumptions} color="text-[#a78bfa]" onInspect={onInspect} />
                    <SignalCategory label="Goals w/o Progress" items={health.goals_without_progress} color="text-[#60a5fa]" onInspect={onInspect} />
                    <SignalCategory label="Unassigned Actions" items={health.action_items_without_owners} color="text-[#34d399]" onInspect={onInspect} />
                </div>
            )}
        </div>
    );
}
