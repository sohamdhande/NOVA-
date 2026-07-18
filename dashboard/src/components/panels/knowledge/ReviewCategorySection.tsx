import React from "react";
import { MarkdownRenderer } from "../../MarkdownRenderer";

interface SuggestionItem {
    id: string;
    op: string;
    dialect: string;
    content: string;
    semantic_category?: string;
    semantic_type?: string;
    evidence_span?: string;
    confidence?: number;
    approved: boolean;
    raw_payload?: any;
}

interface Props {
    title: string;
    items: { obs: SuggestionItem; index: number }[];
    onToggle: (index: number) => void;
}

function renderNaturalContent(obs: SuggestionItem): React.ReactNode {
    let data: Record<string, any> | null = null;
    if (obs.raw_payload && typeof obs.raw_payload === "object") {
        data = obs.raw_payload;
    } else if (typeof obs.content === "string") {
        const trimmed = obs.content.trim();
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            try {
                data = JSON.parse(trimmed);
            } catch {
                data = null;
            }
        }
    }

    if (!data || typeof data !== "object") {
        return (
            <div className="mt-1">
                <MarkdownRenderer content={obs.content} />
            </div>
        );
    }

    // 1. Decisions
    if (data.title && (data.summary || data.rationale)) {
        return (
            <div className="font-sans space-y-2 mt-1.5">
                <div className="font-semibold text-sm text-[var(--nova-accent)] leading-snug">
                    {data.title}
                </div>
                {data.summary && (
                    <div className="text-xs text-[var(--nova-text)] leading-relaxed">
                        {data.summary}
                    </div>
                )}
                {(data.rationale || data.reasoning) && (
                    <div className="flex items-start gap-2 text-xs text-[var(--nova-muted)] leading-relaxed bg-[var(--nova-surface)] p-2.5 rounded border border-[var(--nova-border)]/50">
                        <span className="text-[#a78bfa] font-mono text-[10px] font-bold uppercase tracking-wider shrink-0 mt-0.5">Rationale:</span>
                        <span className="text-[var(--nova-text)]/90">{data.rationale || data.reasoning}</span>
                    </div>
                )}
                {Array.isArray(data.participants) && data.participants.length > 0 && (
                    <div className="text-[11px] text-[var(--nova-muted)] font-mono flex items-center gap-1.5 pt-0.5">
                        <span className="text-[var(--nova-amber)]">👥 Participants:</span>
                        <span>{data.participants.join(", ")}</span>
                    </div>
                )}
            </div>
        );
    }

    // 2. Alternatives
    if (data.topic) {
        return (
            <div className="font-sans space-y-2 mt-1.5">
                <div className="font-semibold text-sm text-[var(--nova-accent)] leading-snug">
                    Topic: {data.topic}
                </div>
                {data.chosen_option && (
                    <div className="text-xs text-[#34d399] leading-relaxed font-medium">
                        ✓ Chosen Option: <span className="text-white font-semibold">{data.chosen_option}</span>
                    </div>
                )}
                {Array.isArray(data.rejected_options) && data.rejected_options.length > 0 && (
                    <div className="text-xs text-[#f87171] leading-relaxed">
                        ✗ Rejected Options: <span className="text-[var(--nova-muted)] font-normal">{data.rejected_options.join(", ")}</span>
                    </div>
                )}
                {!data.chosen_option && Array.isArray(data.options) && data.options.length > 0 && (
                    <div className="text-xs text-[var(--nova-text)] leading-relaxed">
                        Options: {data.options.join(", ")}
                    </div>
                )}
                {data.reasoning && (
                    <div className="flex items-start gap-2 text-xs text-[var(--nova-muted)] leading-relaxed bg-[var(--nova-surface)] p-2.5 rounded border border-[var(--nova-border)]/50">
                        <span className="text-[#a78bfa] font-mono text-[10px] font-bold uppercase tracking-wider shrink-0 mt-0.5">Reasoning:</span>
                        <span className="text-[var(--nova-text)]/90">{data.reasoning}</span>
                    </div>
                )}
            </div>
        );
    }

    // 3. Tradeoffs
    if (data.side_a && data.side_b) {
        return (
            <div className="font-sans space-y-2 mt-1.5">
                <div className="font-semibold text-sm text-[#facc15] leading-snug flex items-center gap-2 flex-wrap">
                    <span>{data.side_a}</span>
                    <span className="text-[10px] font-mono text-[var(--nova-muted)] uppercase bg-[var(--nova-surface)] px-2 py-0.5 rounded border border-[var(--nova-border)]/40">vs</span>
                    <span>{data.side_b}</span>
                </div>
                {data.description && (
                    <div className="text-xs text-[var(--nova-text)] leading-relaxed">
                        {data.description}
                    </div>
                )}
            </div>
        );
    }

    // 4. Questions
    if (data.question) {
        return (
            <div className="font-sans space-y-1.5 mt-1">
                <div className="font-semibold text-xs text-[#60a5fa] leading-relaxed">
                    ❓ {data.question}
                </div>
                {data.status && (
                    <div className="text-[10px] font-mono text-[var(--nova-muted)]">
                        Status: <span className="text-[var(--nova-amber)] uppercase font-bold">{data.status}</span>
                    </div>
                )}
            </div>
        );
    }

    // 5. Principles
    if (data.statement) {
        return (
            <div className="font-sans space-y-2 mt-1.5">
                <div className="font-semibold text-xs text-[var(--nova-accent)] leading-relaxed">
                    ✦ {data.statement}
                </div>
                {data.rationale && (
                    <div className="flex items-start gap-2 text-xs text-[var(--nova-muted)] leading-relaxed bg-[var(--nova-surface)] p-2.5 rounded border border-[var(--nova-border)]/50">
                        <span className="text-[#a78bfa] font-mono text-[10px] font-bold uppercase tracking-wider shrink-0 mt-0.5">Rationale:</span>
                        <span className="text-[var(--nova-text)]/90">{data.rationale}</span>
                    </div>
                )}
            </div>
        );
    }

    // 6. Risks, Action Items, Goals, Assumptions, Constraints, Notes, and general structured objects
    const mainText = data.description || data.content || data.summary || data.name || data.text;
    const hasMainText = typeof mainText === "string" && mainText.trim().length > 0;

    return (
        <div className="font-sans space-y-2 mt-1.5">
            {hasMainText && (
                <div className="text-xs text-[var(--nova-text)] font-medium leading-relaxed">
                    {mainText}
                </div>
            )}
            <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono pt-0.5">
                {data.category && (
                    <span className="px-2 py-0.5 bg-[#a78bfa]/10 text-[#a78bfa] border border-[#a78bfa]/30 rounded">
                        Category: {data.category}
                    </span>
                )}
                {data.probability && (
                    <span className="px-2 py-0.5 bg-[#60a5fa]/10 text-[#60a5fa] border border-[#60a5fa]/30 rounded">
                        Probability: {data.probability}
                    </span>
                )}
                {(data.impact || data.severity) && (
                    <span className="px-2 py-0.5 bg-[var(--nova-amber)]/10 text-[var(--nova-amber)] border border-[var(--nova-amber)]/30 rounded">
                        Impact: {data.impact || data.severity}
                    </span>
                )}
                {data.owner && (
                    <span className="px-2 py-0.5 bg-[#60a5fa]/10 text-[#60a5fa] border border-[#60a5fa]/30 rounded font-semibold">
                        👤 Owner: {data.owner}
                    </span>
                )}
                {data.status && (
                    <span className="px-2 py-0.5 bg-[var(--nova-amber)]/10 text-[var(--nova-amber)] border border-[var(--nova-amber)]/30 rounded uppercase font-bold">
                        Status: {data.status}
                    </span>
                )}
                {data.scope && (
                    <span className="px-2 py-0.5 bg-white/10 text-white border border-white/20 rounded">
                        Scope: {data.scope}
                    </span>
                )}
            </div>
            {data.supporting_evidence &&
                typeof data.supporting_evidence === "string" &&
                data.supporting_evidence.trim() !== "" &&
                data.supporting_evidence !== obs.evidence_span && (
                    <div className="text-[11px] text-[var(--nova-muted)] leading-relaxed mt-1 bg-[var(--nova-surface)]/60 p-2 rounded border border-[var(--nova-border)]/40">
                        <span className="text-[var(--nova-amber)] font-mono text-[10px] uppercase font-bold mr-1.5">Supporting Evidence:</span>
                        <span>{data.supporting_evidence}</span>
                    </div>
                )}
        </div>
    );
}

export function ReviewCategorySection({ title, items, onToggle }: Props) {
    if (items.length === 0) return null;

    return (
        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-3 space-y-2">
            <div className="flex justify-between items-center border-b border-[var(--nova-border)]/40 pb-1.5">
                <h3 className="text-[10px] font-mono tracking-widest text-[var(--nova-accent)] uppercase">
                    {title} ({items.length})
                </h3>
                <span className="text-[9px] font-mono text-[var(--nova-muted)]">AI Suggestion</span>
            </div>

            <div className="space-y-2">
                {items.map(({ obs, index }) => (
                    <label
                        key={index}
                        className="flex items-start gap-3 p-2.5 rounded bg-[var(--nova-surface2)] border border-[var(--nova-border)]/50 cursor-pointer hover:border-[var(--nova-accent)]/40 transition-colors"
                    >
                        <input
                            type="checkbox"
                            checked={obs.approved}
                            onChange={() => onToggle(index)}
                            className="mt-1.5 accent-[var(--nova-accent)] shrink-0"
                        />
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1 flex-wrap font-mono">
                                <span className="text-[9px] text-[#60a5fa] font-bold">
                                    {obs.semantic_type || obs.dialect}:{obs.op}
                                </span>
                                {obs.evidence_span && (
                                    <span className="text-[9px] px-1.5 py-0.5 bg-[var(--nova-amber)]/10 text-[var(--nova-amber)] border border-[var(--nova-amber)]/30 rounded">
                                        Evidence: {obs.evidence_span}
                                    </span>
                                )}
                                {obs.confidence !== undefined && (
                                    <span className="text-[9px] text-[var(--nova-muted)]">
                                        Conf: {obs.confidence}
                                    </span>
                                )}
                            </div>
                            {renderNaturalContent(obs)}
                        </div>
                    </label>
                ))}
            </div>
        </div>
    );
}
