import { useState } from "react";
import { MarkdownRenderer } from "../../MarkdownRenderer";

interface NodeSummary {
    id: string;
    dialect?: string;
    op?: string;
    summary?: string;
    evidence_span?: string;
    confidence?: number;
    raw_payload?: unknown;
}

interface InspectData {
    object_type: string;
    id: string;
    summary: string;
    metadata: Record<string, unknown>;
    relationships?: { target: string; relation: string }[];
    timeline?: { timestamp: string; event: string }[];
    provenance?: string[];
    supporting_evidence?: string[];
    related_commits?: string[];
    commit_nodes?: NodeSummary[];
    sibling_nodes?: NodeSummary[];
}

interface Props {
    data: InspectData;
    onNavigate: (id: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
    Commit: "bg-[var(--nova-accent)]/20 text-[var(--nova-accent)] border border-[var(--nova-accent)]/30",
    Observation: "bg-[#60a5fa]/20 text-[#60a5fa] border border-[#60a5fa]/30",
    Artifact: "bg-[var(--nova-amber)]/20 text-[var(--nova-amber)] border border-[var(--nova-amber)]/30",
    Entity: "bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/30",
};

function formatNaturalText(val: unknown): string {
    if (!val) return "";
    if (typeof val === "string") {
        const trimmed = val.trim();
        if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
            try {
                return formatNaturalText(JSON.parse(trimmed));
            } catch {
                try {
                    const repaired = trimmed.replace(/("")([^"]*)("")/g, '"$2"');
                    return formatNaturalText(JSON.parse(repaired));
                } catch {
                    // fallthrough to regex
                }
            }
        }
        const matches = [...trimmed.matchAll(/\"(?:decision|goal|risk|action|principle|statement|summary|description|question)\"\s*:\s*\"([^\"]+)\"/g)].map(m => `• ${m[1].trim()}`).filter(Boolean);
        if (matches.length > 0) {
            return matches.join("\n");
        }
        return trimmed;
    }
    if (typeof val === "object" && val !== null) {
        if (Array.isArray(val)) {
            return val.map((item) => `• ${formatNaturalText(item)}`).filter(Boolean).join("\n");
        }
        const obj = val as Record<string, any>;
        if (obj.title && obj.summary) return `${obj.title}: ${obj.summary}`;
        if (obj.topic && obj.chosen_option) return `${obj.topic} (Chosen: ${obj.chosen_option})`;
        if (obj.side_a && obj.side_b) return `${obj.side_a} vs ${obj.side_b}: ${obj.description || ""}`;
        if (obj.question) return `Question: ${obj.question}`;
        if (obj.statement) return `Principle: ${obj.statement}`;

        for (const listKey of ["decisions", "observations", "risks", "action_items", "alternatives", "tradeoffs", "goals", "assumptions", "constraints", "questions", "principles", "notes", "items"]) {
            if (Array.isArray(obj[listKey])) {
                const lines = obj[listKey].map((item: any) => {
                    if (typeof item === "object" && item !== null) {
                        const itemText = item.decision || item.description || item.statement || item.summary || item.content || item.question || item.title || item.name || JSON.stringify(item);
                        return `• ${itemText}`;
                    }
                    return `• ${item}`;
                });
                if (lines.length > 0) return lines.join("\n");
            }
        }

        for (const key of ["decision", "description", "content", "summary", "name", "title", "text"]) {
            if (typeof obj[key] === "string" && obj[key].trim()) return obj[key].trim();
        }
        return JSON.stringify(obj, null, 2);
    }
    return String(val);
}

function ClickableId({ id, onNavigate }: { id: string; onNavigate: (id: string) => void }) {
    return (
        <button
            onClick={() => onNavigate(id)}
            className="text-[var(--nova-accent)] hover:underline font-mono text-xs break-all text-left transition-colors font-medium"
        >
            {id}
        </button>
    );
}

export function InspectorCard({ data, onNavigate }: Props) {
    const [showMeta, setShowMeta] = useState(false);
    const [showSiblings, setShowSiblings] = useState(false);
    const colorClass = TYPE_COLORS[data.object_type] || TYPE_COLORS.Entity;

    const relationships = data.relationships || [];
    const provenance = data.provenance || [];
    const supportingEvidence = data.supporting_evidence || [];
    const relatedCommits = data.related_commits || [];
    const timeline = data.timeline || [];
    const commitNodes = data.commit_nodes || [];
    const siblingNodes = data.sibling_nodes || [];

    return (
        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg overflow-hidden shadow-xl">
            {/* Header */}
            <div className="p-4 border-b border-[var(--nova-border)]/50 flex items-center justify-between bg-[var(--nova-surface2)]/40">
                <div className="flex items-center gap-3 min-w-0">
                    <span className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded shrink-0 ${colorClass}`}>
                        {data.object_type}
                    </span>
                    <span className="text-xs font-mono text-[var(--nova-text)] truncate font-semibold" title={data.id}>
                        {data.id}
                    </span>
                </div>
            </div>

            {/* Main Summary */}
            <div className="px-4 py-3.5 border-b border-[var(--nova-border)]/30 bg-[var(--nova-surface)]">
                <MarkdownRenderer content={formatNaturalText(data.summary)} className="text-[14px] leading-relaxed font-sans" />
            </div>

            {/* Rich Commit Dossier (For Commit objects) */}
            {data.object_type === "Commit" && commitNodes.length > 0 && (
                <div className="p-3.5 border-b border-[var(--nova-border)]/40 bg-[var(--nova-surface2)]/20">
                    <div className="flex items-center justify-between mb-2.5">
                        <h4 className="text-[10px] font-mono tracking-widest text-[var(--nova-accent)] uppercase font-semibold">
                            Compiled Knowledge Dossier ({commitNodes.length} Items)
                        </h4>
                        <span className="text-[9px] font-mono text-[var(--nova-muted)]">Batch Snapshot</span>
                    </div>
                    <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                        {commitNodes.map((n, i) => (
                            <div
                                key={i}
                                className="p-2.5 rounded bg-[var(--nova-surface)] border border-[var(--nova-border)]/60 hover:border-[var(--nova-accent)]/40 transition-colors space-y-1.5"
                            >
                                <div className="flex items-center justify-between gap-2 flex-wrap font-mono">
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-[9px] px-1.5 py-0.5 bg-[#60a5fa]/10 text-[#60a5fa] border border-[#60a5fa]/30 rounded font-bold">
                                            {n.dialect || "FACT"}:{n.op || "ASSERT"}
                                        </span>
                                        {n.confidence !== undefined && n.confidence !== null && (
                                            <span className="text-[9px] text-[var(--nova-muted)]">
                                                Conf: {n.confidence}
                                            </span>
                                        )}
                                    </div>
                                    <ClickableId id={n.id} onNavigate={onNavigate} />
                                </div>
                                <div className="pt-1">
                                    <MarkdownRenderer content={formatNaturalText(n.summary || n.raw_payload) || "No content."} />
                                </div>
                                {n.evidence_span && (
                                    <div className="text-[10px] font-mono text-[var(--nova-muted)] bg-[var(--nova-surface2)] px-2 py-1 rounded border border-[var(--nova-border)]/30 truncate">
                                        <span className="text-[var(--nova-amber)] mr-1">Evidence:</span>
                                        {n.evidence_span}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Inline Sibling Preview (For Observation objects) */}
            {data.object_type === "Observation" && siblingNodes.length > 0 && (
                <div className="border-b border-[var(--nova-border)]/40 bg-[var(--nova-surface2)]/20">
                    <button
                        onClick={() => setShowSiblings(!showSiblings)}
                        className="w-full p-3 flex items-center justify-between text-[10px] font-mono tracking-widest text-[var(--nova-accent)] uppercase hover:bg-[var(--nova-accent)]/5 transition-colors text-left"
                    >
                        <span className="font-semibold flex items-center gap-1.5">
                            <span>{showSiblings ? "▼" : "▶"}</span>
                            <span>Sibling Facts in Parent Commit (+{siblingNodes.length} Items)</span>
                        </span>
                        <span className="text-[9px] text-[var(--nova-muted)] lowercase font-normal">click to {showSiblings ? "hide" : "expand"}</span>
                    </button>
                    {showSiblings && (
                        <div className="p-3 pt-1 space-y-2 max-h-64 overflow-y-auto pr-1 border-t border-[var(--nova-border)]/20">
                            {siblingNodes.map((s, i) => (
                                <div
                                    key={i}
                                    className="p-2 rounded bg-[var(--nova-surface)] border border-[var(--nova-border)]/50 hover:border-[#60a5fa]/40 transition-colors space-y-1"
                                >
                                    <div className="flex items-center justify-between gap-2 font-mono">
                                        <span className="text-[9px] text-[#60a5fa] font-bold">
                                            {s.dialect}:{s.op}
                                        </span>
                                        <ClickableId id={s.id} onNavigate={onNavigate} />
                                    </div>
                                    <div className="pt-1">
                                        <MarkdownRenderer content={formatNaturalText(s.summary || s.raw_payload)} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Grid sections */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--nova-border)]/30">
                {/* Relationships */}
                <div className="p-3 bg-[var(--nova-surface)]">
                    <h4 className="text-[9px] font-mono tracking-widest text-[var(--nova-muted)] uppercase mb-2">Relationships</h4>
                    {relationships.length === 0 ? (
                        <span className="text-xs text-[var(--nova-muted)]">None</span>
                    ) : (
                        <div className="space-y-1">
                            {relationships.map((r, i) => (
                                <div key={i} className="flex items-center gap-2 text-xs">
                                    <span className="text-[var(--nova-muted)] font-mono">{r.relation}</span>
                                    <span className="text-[var(--nova-muted)]">→</span>
                                    <ClickableId id={r.target} onNavigate={onNavigate} />
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Provenance */}
                <div className="p-3 bg-[var(--nova-surface)]">
                    <h4 className="text-[9px] font-mono tracking-widest text-[var(--nova-muted)] uppercase mb-2">Provenance Chain</h4>
                    {provenance.length === 0 ? (
                        <span className="text-xs text-[var(--nova-muted)]">None</span>
                    ) : (
                        <div className="flex flex-wrap items-center gap-1">
                            {provenance.map((p, i) => (
                                <span key={i} className="flex items-center gap-1">
                                    {i > 0 && <span className="text-[var(--nova-muted)]">→</span>}
                                    <ClickableId id={p} onNavigate={onNavigate} />
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                {/* Supporting Evidence */}
                {data.object_type !== "Commit" && (
                    <div className="p-3 bg-[var(--nova-surface)]">
                        <h4 className="text-[9px] font-mono tracking-widest text-[var(--nova-muted)] uppercase mb-2">Supporting Evidence</h4>
                        {supportingEvidence.length === 0 ? (
                            <span className="text-xs text-[var(--nova-muted)]">None</span>
                        ) : (
                            <div className="space-y-1">
                                {supportingEvidence.map((e, i) => (
                                    <ClickableId key={i} id={e} onNavigate={onNavigate} />
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Related Commits */}
                <div className="p-3 bg-[var(--nova-surface)]">
                    <h4 className="text-[9px] font-mono tracking-widest text-[var(--nova-muted)] uppercase mb-2">Related Commits</h4>
                    {relatedCommits.length === 0 ? (
                        <span className="text-xs text-[var(--nova-muted)]">None</span>
                    ) : (
                        <div className="space-y-1">
                            {relatedCommits.map((c, i) => (
                                <ClickableId key={i} id={c} onNavigate={onNavigate} />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Timeline */}
            {timeline.length > 0 && (
                <div className="p-3 border-t border-[var(--nova-border)]/30 bg-[var(--nova-surface)]">
                    <h4 className="text-[9px] font-mono tracking-widest text-[var(--nova-muted)] uppercase mb-2">Timeline</h4>
                    <div className="space-y-1">
                        {timeline.map((t, i) => (
                            <div key={i} className="flex items-center gap-3 text-xs font-mono">
                                <span className="text-[var(--nova-muted)]">{t.timestamp}</span>
                                <span className="text-[var(--nova-text)]">{t.event}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Metadata toggle */}
            <div className="border-t border-[var(--nova-border)]/30 bg-[var(--nova-surface)]">
                <button
                    onClick={() => setShowMeta(!showMeta)}
                    className="w-full px-3 py-2 text-[9px] font-mono tracking-widest text-[var(--nova-muted)] uppercase hover:text-[var(--nova-accent)] hover:bg-[var(--nova-accent)]/5 transition-colors text-left flex items-center gap-1.5"
                >
                    <span>{showMeta ? "▼" : "▶"}</span>
                    <span>Raw Metadata</span>
                </button>
                {showMeta && (
                    <pre className="px-3 pb-3 text-[10px] font-mono text-[var(--nova-muted)] overflow-x-auto max-h-48 overflow-y-auto">
                        {JSON.stringify(data.metadata, null, 2)}
                    </pre>
                )}
            </div>
        </div>
    );
}
