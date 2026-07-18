import { useState } from "react";
import { useApi } from "../../../hooks/useApi";

interface Props {
    onInspect: (id: string) => void;
    initialFactId?: string;
}

export function ExplainView({ onInspect, initialFactId = "" }: Props) {
    const { get } = useApi();
    const [factId, setFactId] = useState(initialFactId);
    const [chain, setChain] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [searched, setSearched] = useState(false);

    const explain = async () => {
        if (!factId.trim()) return;
        setLoading(true);
        try {
            const data = await get<{ fact_id: string; chain: string[] }>(`/api/knowledge/explain/${encodeURIComponent(factId)}`);
            setChain(data.chain);
            setSearched(true);
        } catch { setChain([]); }
        finally { setLoading(false); }
    };

    return (
        <div className="flex flex-col h-full">
            <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase mb-3">Provenance Explorer</h2>
            <p className="text-[10px] font-mono text-[var(--nova-muted)] mb-4">Enter a fact or observation ID to trace its provenance chain.</p>

            <div className="flex gap-2 mb-4">
                <input
                    value={factId}
                    onChange={e => setFactId(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && explain()}
                    placeholder="kir_obs_abc123 or obs_abc123"
                    className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-3 py-2 text-sm font-mono text-[var(--nova-text)] focus:outline-none focus:border-[var(--nova-accent)] placeholder:text-[var(--nova-muted)]"
                />
                <button
                    onClick={explain}
                    disabled={!factId.trim() || loading}
                    className="bg-[var(--nova-accent)] text-black font-bold px-4 py-2 rounded text-xs font-mono uppercase tracking-wider hover:brightness-110 disabled:opacity-40 transition-all"
                >
                    {loading ? "..." : "Explain"}
                </button>
            </div>

            <div className="flex-1 overflow-y-auto">
                {!searched && (
                    <div className="text-xs font-mono text-[var(--nova-muted)] text-center mt-12">
                        Provenance chain will appear here.
                    </div>
                )}
                {searched && chain.length === 0 && (
                    <div className="text-xs font-mono text-[var(--nova-muted)] text-center mt-12">
                        No provenance found for "{factId}".
                    </div>
                )}
                {chain.length > 0 && (
                    <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-4">
                        <h3 className="text-[10px] font-mono tracking-widest text-[var(--nova-muted)] uppercase mb-3">
                            Provenance Chain ({chain.length} step{chain.length !== 1 ? "s" : ""})
                        </h3>
                        <div className="relative pl-6 border-l-2 border-[var(--nova-accent)]/30 space-y-3">
                            {chain.map((step, i) => (
                                <div key={i} className="relative">
                                    <div className="absolute -left-[25px] top-1 w-3 h-3 rounded-full bg-[var(--nova-accent)]/20 border-2 border-[var(--nova-accent)] flex items-center justify-center">
                                        <div className="w-1 h-1 rounded-full bg-[var(--nova-accent)]" />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[9px] font-mono text-[var(--nova-muted)] bg-[var(--nova-surface2)] px-1.5 py-0.5 rounded">
                                            {i === 0 ? "ROOT" : `STEP ${i}`}
                                        </span>
                                        <button
                                            onClick={() => onInspect(step)}
                                            className="text-xs font-mono text-[var(--nova-accent)] hover:underline break-all text-left"
                                        >
                                            {step}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
