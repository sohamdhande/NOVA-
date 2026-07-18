import { useState } from "react";
import { useApi } from "../../../hooks/useApi";
import { ReviewCategorySection } from "./ReviewCategorySection";
import { ChronicleExportSection } from "./ChronicleExportSection";

const SOURCE_TYPES = [
    { key: "chronicle_export", label: "Chronicle Export" },
    { key: "plaintext", label: "Plain Text" },
    { key: "markdown", label: "Markdown" },
    { key: "pdf", label: "PDF Document" },
    { key: "git", label: "Git Commit" },
    { key: "slack", label: "Slack Export" },
    { key: "email", label: "Email Message" },
    { key: "json", label: "JSON Payload" },
    { key: "csv", label: "CSV Dataset" },
];

interface PreviewData {
    observations: { id: string; op: string; dialect: string; content: string; semantic_category?: string; type?: string; evidence_span?: string; confidence?: number; approved: boolean; raw_payload?: any }[];
    suggested_entities: { id: string; name: string; evidence_span?: string; confidence?: number; approved: boolean }[];
    suggested_relationships: { source: string; target: string; relation: string; evidence_span?: string; confidence?: number; approved: boolean }[];
    diagnostics: { level: string; message: string }[];
    warnings: string[];
    partial_extraction?: boolean;
    failed_groups?: string[];
    failed_categories?: string[];
}

interface Props {
    onInspect: (id: string) => void;
    onNavigate: (view: string) => void;
}

export function NewArtifactView({ onInspect, onNavigate }: Props) {
    const { post } = useApi();
    const [sourceType, setSourceType] = useState("chronicle_export");
    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [step, setStep] = useState<"input" | "review" | "compiled">("input");
    const [preview, setPreview] = useState<PreviewData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [compiledHash, setCompiledHash] = useState("");
    const [acknowledgedPartial, setAcknowledgedPartial] = useState(false);
    const [retrying, setRetrying] = useState(false);

    const handlePreview = async () => {
        if (!content.trim()) return;
        setLoading(true);
        setError("");
        try {
            const res = await post<PreviewData>("/api/knowledge/preview", { source_type: sourceType, content, title });
            setPreview(res);
            setAcknowledgedPartial(false);
            setStep("review");
        } catch (e: any) {
            setError(e.message ?? "Extraction preview failed");
        } finally {
            setLoading(false);
        }
    };

    const handleCompile = async () => {
        if (!preview) return;
        const approvedObs = preview.observations.filter(o => o.approved);
        if (approvedObs.length === 0) {
            setError("You must approve at least one suggestion to compile.");
            return;
        }
        setLoading(true);
        setError("");
        try {
            const res = await post<{ commit_hash: string }>("/api/knowledge/compile", {
                source_type: sourceType, content, title,
                approved_observation_ids: approvedObs.map(o => o.id),
                approved_observations: approvedObs.map(o => o.raw_payload || { id: o.id, type: o.type || "OBSERVATION", content: o.content })
            });
            setCompiledHash(res.commit_hash);
            setStep("compiled");
        } catch (e: any) {
            setError(e.message ?? "Compilation failed");
        } finally {
            setLoading(false);
        }
    };

    const handleRetry = async () => {
        if (!preview || !preview.failed_groups || preview.failed_groups.length === 0) return;
        setRetrying(true);
        setError("");
        try {
            const res = await post<PreviewData>("/api/knowledge/preview/retry", {
                source_type: sourceType,
                content,
                title,
                retry_groups: preview.failed_groups
            });
            setPreview({
                ...preview,
                observations: [...preview.observations, ...res.observations],
                suggested_entities: [...preview.suggested_entities, ...res.suggested_entities],
                suggested_relationships: [...preview.suggested_relationships, ...res.suggested_relationships],
                partial_extraction: false,
                failed_categories: [],
                failed_groups: []
            });
            setAcknowledgedPartial(true);
        } catch (e: any) {
            setError(e.message ?? "Retry failed");
        } finally {
            setRetrying(false);
        }
    };

    const toggleObs = (i: number) => {
        if (!preview) return;
        const obs = [...preview.observations];
        obs[i].approved = !obs[i].approved;
        setPreview({ ...preview, observations: obs });
    };

    return (
        <div className="flex flex-col h-full overflow-y-auto pr-1 space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--nova-border)]/50 pb-3">
                <div>
                    <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase">Artifact Ingestion Pipeline</h2>
                    <p className="text-[10px] font-mono text-[var(--nova-muted)]">Journey: New Artifact → Extraction Review → Trusted Compilation</p>
                </div>
                {step !== "input" && (
                    <button onClick={() => { setStep("input"); setError(""); }} className="text-[9px] font-mono text-[var(--nova-muted)] hover:text-[var(--nova-text)] px-2 py-1 border border-[var(--nova-border)] rounded">
                        ← Back to Editor
                    </button>
                )}
            </div>

            {error && <div className="p-3 bg-[var(--nova-red)]/10 border border-[var(--nova-red)]/30 rounded text-xs font-mono text-[var(--nova-red)]">{error}</div>}

            {/* STEP 1: INPUT */}
            {step === "input" && (
                <div className="flex flex-col gap-4 flex-1">
                    {sourceType === "chronicle_export" && <ChronicleExportSection />}
                    
                    <div className="grid grid-cols-4 gap-2">
                        {SOURCE_TYPES.map(st => (
                            <button
                                key={st.key}
                                onClick={() => setSourceType(st.key)}
                                className={`p-2 rounded border text-left font-mono transition-all ${
                                    sourceType === st.key
                                        ? "border-[var(--nova-accent)] bg-[var(--nova-accent)]/10 text-[var(--nova-accent)] font-bold"
                                        : "border-[var(--nova-border)] bg-[var(--nova-surface)] text-[var(--nova-muted)] hover:text-[var(--nova-text)]"
                                }`}
                            >
                                <div className="text-[10px] uppercase">{st.label}</div>
                            </button>
                        ))}
                    </div>

                    <input
                        value={title}
                        onChange={e => setTitle(e.target.value)}
                        placeholder="Artifact identifier, document title, or source path (e.g. spec/auth_v2.md)"
                        className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-3 py-2 text-xs font-mono text-[var(--nova-text)] focus:outline-none focus:border-[var(--nova-accent)] placeholder:text-[var(--nova-muted)]"
                    />

                    <textarea
                        value={content}
                        onChange={e => setContent(e.target.value)}
                        placeholder={sourceType === "chronicle_export" ? "Paste Chronicle Export..." : "Paste raw payload, unstructured text, or artifact contents..."}
                        className="flex-1 min-h-[260px] bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-3 text-xs font-mono text-[var(--nova-text)] focus:outline-none focus:border-[var(--nova-accent)] placeholder:text-[var(--nova-muted)] resize-none"
                    />

                    <button
                        onClick={handlePreview}
                        disabled={!content.trim() || loading}
                        className="w-full py-2.5 bg-[var(--nova-accent)] text-black font-mono font-bold text-xs uppercase tracking-wider rounded hover:brightness-110 disabled:opacity-40 transition-all"
                    >
                        {loading ? "Running Deterministic Extraction..." : "Preview Extraction →"}
                    </button>
                </div>
            )}

            {/* STEP 2: REVIEW */}
            {step === "review" && preview && (
                <div className="flex flex-col space-y-4 flex-1">
                    {preview.partial_extraction && !acknowledgedPartial && (
                        <div className="bg-[var(--nova-surface2)] border-2 border-[var(--nova-red)] p-5 rounded">
                            <div className="flex items-center gap-2 mb-3">
                                <span className="text-xl">⚠️</span>
                                <h3 className="text-sm font-bold text-[var(--nova-red)]">Partial Extraction Detected</h3>
                            </div>
                            <p className="text-xs text-[var(--nova-text)] mb-2 leading-relaxed">
                                Extraction failed for the following categories: <span className="font-bold text-white">{preview.failed_categories?.join(", ")}</span>.
                            </p>
                            <p className="text-xs text-[var(--nova-muted)] mb-5">
                                Want to retry extracting the missing data, or proceed with what was successfully captured?
                            </p>
                            <div className="flex justify-end gap-3">
                                <button onClick={() => setAcknowledgedPartial(true)} className="px-4 py-2 border border-[var(--nova-red)] text-[var(--nova-red)] font-bold text-[10px] rounded uppercase tracking-wider hover:bg-[var(--nova-red)]/10 transition-colors">
                                    Accept What Was Captured
                                </button>
                                <button onClick={handleRetry} disabled={retrying} className="px-4 py-2 bg-[var(--nova-red)] border border-[var(--nova-red)] text-white font-bold text-[10px] rounded uppercase tracking-wider hover:brightness-110 disabled:opacity-50 transition-all shadow-[0_0_10px_rgba(255,50,50,0.3)]">
                                    {retrying ? "Retrying..." : "Retry Failed Categories"}
                                </button>
                            </div>
                        </div>
                    )}

                    <div className={`space-y-3 transition-opacity ${preview.partial_extraction && !acknowledgedPartial ? "opacity-50 pointer-events-none" : ""}`}>
                        <div className="flex justify-between items-center px-1">
                            <h3 className="text-[10px] font-mono tracking-widest text-[var(--nova-accent)] uppercase">Review Extracted Organizational Knowledge</h3>
                            <div className="flex items-center gap-3">
                                <button 
                                    onClick={() => {
                                        if (preview) navigator.clipboard.writeText(JSON.stringify(preview, null, 2));
                                    }} 
                                    className="text-[9px] font-mono px-2 py-1 bg-[var(--nova-surface2)] border border-[var(--nova-border)] text-[var(--nova-muted)] hover:text-[var(--nova-text)] rounded hover:border-[var(--nova-accent)] transition-all flex items-center gap-1"
                                    title="Copy raw JSON payload to clipboard"
                                >
                                    📋 Copy JSON
                                </button>
                                <span className="text-[9px] font-mono text-[var(--nova-muted)]">Independent Human Approval</span>
                            </div>
                        </div>
                        {["decisions", "risks", "assumptions", "constraints", "goals", "action_items", "questions", "principles", "tradeoffs", "alternatives", "observations"].map((cat) => {
                            const items = preview.observations
                                .map((obs, index) => ({ obs, index }))
                                .filter(({ obs }) => (obs.semantic_category || "observations") === cat);
                            const titles: Record<string, string> = {
                                decisions: "Decisions", risks: "Risks", assumptions: "Assumptions",
                                constraints: "Constraints", goals: "Goals", action_items: "Action Items",
                                questions: "Questions", principles: "Principles", tradeoffs: "Trade-offs",
                                alternatives: "Alternatives", observations: "Generic Observations"
                            };
                            return <ReviewCategorySection key={cat} title={titles[cat] || cat} items={items} onToggle={toggleObs} />;
                        })}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-3">
                            <h4 className="text-[9px] font-mono text-[#a78bfa] uppercase tracking-wider mb-2">Suggested Entities ({preview.suggested_entities.length})</h4>
                            {preview.suggested_entities.map((e, i) => (
                                <div key={i} className="text-[10px] font-mono text-[var(--nova-text)] py-0.5">✓ {e.name}</div>
                            ))}
                        </div>
                        <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-3">
                            <h4 className="text-[9px] font-mono text-[var(--nova-amber)] uppercase tracking-wider mb-2">Diagnostics</h4>
                            {preview.diagnostics.map((d, i) => (
                                <div key={i} className="text-[10px] font-mono text-[var(--nova-muted)] py-0.5">ℹ {d.message}</div>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleCompile}
                        disabled={loading || (preview.partial_extraction && !acknowledgedPartial)}
                        className="w-full py-3 bg-[var(--nova-accent)] text-black font-mono font-bold text-xs uppercase tracking-wider rounded hover:brightness-110 shadow-[0_0_15px_rgba(0,255,204,0.3)] transition-all disabled:opacity-40 disabled:shadow-none"
                    >
                        {loading ? "Compiling Cryptographic Commit..." : "⚡ Approve & Compile Knowledge"}
                    </button>
                </div>
            )}

            {/* STEP 3: COMPILED */}
            {step === "compiled" && (
                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-6 text-center space-y-4 my-auto">
                    <div className="w-12 h-12 rounded-full bg-[var(--nova-accent)]/20 border-2 border-[var(--nova-accent)] text-[var(--nova-accent)] flex items-center justify-center mx-auto text-xl font-bold">✓</div>
                    <h3 className="text-sm font-mono font-bold tracking-widest text-[var(--nova-accent)] uppercase">Knowledge Commit Created</h3>
                    <p className="text-xs font-mono text-[var(--nova-text)]">Immutable Hash: <span className="text-[var(--nova-accent)] select-all">{compiledHash}</span></p>

                    <div className="flex justify-center gap-3 pt-2">
                        <button onClick={() => onInspect(compiledHash)} className="px-4 py-2 bg-[var(--nova-accent)] text-black font-mono font-bold text-xs rounded uppercase tracking-wider">
                            ⌕ Inspect Commit
                        </button>
                        <button onClick={() => onNavigate("explorer")} className="px-4 py-2 bg-[var(--nova-surface2)] border border-[var(--nova-border)] text-xs font-mono text-[var(--nova-text)] rounded uppercase tracking-wider hover:border-[var(--nova-accent)]">
                            ◈ View in Explorer
                        </button>
                        <button onClick={() => { setContent(""); setTitle(""); setStep("input"); }} className="px-4 py-2 border border-[var(--nova-border)] text-xs font-mono text-[var(--nova-muted)] rounded uppercase tracking-wider hover:text-[var(--nova-text)]">
                            + Ingest Another
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
