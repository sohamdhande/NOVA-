import { useState } from "react";

export interface ReportData {
    window: string;
    commit_range: string[];
    new_decisions: any[];
    new_goals: any[];
    new_risks: any[];
    assumption_changes: { new: any[]; validated: any[]; invalidated: any[]; superseded: any[] };
    questions: { new: any[]; answered: any[]; unresolved: any[] };
    action_items: { new: any[]; completed: any[]; outstanding: any[] };
    principles: any[];
    chronicle_growth: Record<string, number>;
}

interface Props {
    report: ReportData | null;
    window: string;
    onWindowChange: (w: string) => void;
    onInspect: (id: string) => void;
}

function SectionList({ title, items, color, onInspect }: { title: string; items: any[]; color: string; onInspect: (id: string) => void }) {
    const [open, setOpen] = useState(true);
    if (!items || items.length === 0) return null;

    return (
        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-2.5">
            <button onClick={() => setOpen(!open)} className="w-full flex justify-between items-center text-[10px] font-mono uppercase tracking-wider font-bold text-left">
                <span className={color}>{title} ({items.length})</span>
                <span className="text-[var(--nova-muted)]">{open ? "▼" : "▶"}</span>
            </button>
            {open && (
                <div className="mt-2 space-y-1.5">
                    {items.map((item, i) => (
                        <div key={i} onClick={() => onInspect(item.id)} className="p-2 rounded bg-[var(--nova-surface2)]/40 hover:bg-[var(--nova-surface2)] cursor-pointer border border-transparent hover:border-[var(--nova-border)] transition-all flex justify-between items-start">
                            <div>
                                <div className="text-[10px] font-mono text-[var(--nova-text)] font-semibold">{item.title}</div>
                                {item.rationale && <div className="text-[9px] font-mono text-[var(--nova-muted)] mt-0.5">{item.rationale}</div>}
                                {item.severity && <span className="inline-block mt-1 px-1.5 py-0.2 bg-[var(--nova-red)]/10 text-[var(--nova-red)] text-[8px] font-mono rounded uppercase">{item.severity}</span>}
                            </div>
                            <span className="text-[8px] font-mono text-[var(--nova-muted)] shrink-0 ml-2">{item.timestamp ? item.timestamp.split("T")[0] : ""}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export function DailyChronicleReport({ report, window, onWindowChange, onInspect }: Props) {
    const windows = [
        { key: "today", label: "Today" },
        { key: "yesterday", label: "Yesterday" },
        { key: "7d", label: "Last 7 Days" },
        { key: "30d", label: "Last 30 Days" },
        { key: "all", label: "All Time" }
    ];

    return (
        <div className="space-y-3 shrink-0">
            {/* Header & Window Pill Bar */}
            <div className="flex items-center justify-between border-b border-[var(--nova-border)] pb-2">
                <div>
                    <h3 className="text-xs font-mono tracking-wider text-[var(--nova-text)] uppercase font-bold">Compiled Memory Report</h3>
                    <p className="text-[9px] font-mono text-[var(--nova-muted)]">Deterministic extraction diffs. Zero LLM hallucination.</p>
                </div>
                <div className="flex gap-1 bg-[var(--nova-surface)] p-1 rounded-lg border border-[var(--nova-border)]">
                    {windows.map((w) => (
                        <button
                            key={w.key}
                            onClick={() => onWindowChange(w.key)}
                            className={`px-2.5 py-1 rounded text-[9px] font-mono uppercase transition-all ${
                                window === w.key ? "bg-[var(--nova-accent)] text-black font-bold" : "text-[var(--nova-muted)] hover:text-[var(--nova-text)]"
                            }`}
                        >
                            {w.label}
                        </button>
                    ))}
                </div>
            </div>

            {!report ? (
                <div className="p-4 text-xs font-mono text-[var(--nova-muted)] animate-pulse">Loading compiled window report...</div>
            ) : (
                <div className="space-y-2.5">
                    {/* Growth Stats Strip */}
                    <div className="grid grid-cols-6 gap-2 bg-[var(--nova-surface)] border border-[var(--nova-border)] p-2 rounded-lg text-center">
                        <div><span className="block text-[8px] font-mono text-[var(--nova-muted)] uppercase">Commits</span><span className="text-xs font-mono font-bold text-[var(--nova-accent)]">{report.chronicle_growth?.commits ?? 0}</span></div>
                        <div><span className="block text-[8px] font-mono text-[var(--nova-muted)] uppercase">Artifacts</span><span className="text-xs font-mono font-bold text-[var(--nova-amber)]">{report.chronicle_growth?.artifacts_added ?? 0}</span></div>
                        <div><span className="block text-[8px] font-mono text-[var(--nova-muted)] uppercase">Obs</span><span className="text-xs font-mono font-bold text-[#60a5fa]">{report.chronicle_growth?.observations_added ?? 0}</span></div>
                        <div><span className="block text-[8px] font-mono text-[var(--nova-muted)] uppercase">Semantic</span><span className="text-xs font-mono font-bold text-[#a78bfa]">{report.chronicle_growth?.semantic_objects_added ?? 0}</span></div>
                        <div><span className="block text-[8px] font-mono text-[var(--nova-muted)] uppercase">Entities</span><span className="text-xs font-mono font-bold text-[#f43f5e]">{report.chronicle_growth?.new_entities ?? 0}</span></div>
                        <div><span className="block text-[8px] font-mono text-[var(--nova-muted)] uppercase">Rels</span><span className="text-xs font-mono font-bold text-[#34d399]">{report.chronicle_growth?.relationships ?? 0}</span></div>
                    </div>

                    <SectionList title="New Decisions" items={report.new_decisions} color="text-[var(--nova-accent)]" onInspect={onInspect} />
                    <SectionList title="New Risks" items={report.new_risks} color="text-[var(--nova-red)]" onInspect={onInspect} />
                    <SectionList title="New Goals" items={report.new_goals} color="text-[var(--nova-amber)]" onInspect={onInspect} />
                    <SectionList title="New Principles" items={report.principles} color="text-[#a78bfa]" onInspect={onInspect} />
                    
                    {report.assumption_changes && (
                        <>
                            <SectionList title="Invalidated Assumptions" items={report.assumption_changes.invalidated} color="text-[var(--nova-red)]" onInspect={onInspect} />
                            <SectionList title="Superseded Assumptions" items={report.assumption_changes.superseded} color="text-[var(--nova-amber)]" onInspect={onInspect} />
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
