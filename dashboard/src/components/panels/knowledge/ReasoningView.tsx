import { useState } from "react";
import { useApi } from "../../../hooks/useApi";
import { MarkdownRenderer } from "../../MarkdownRenderer";

export function ReasoningView() {
    const { get, apiFetch } = useApi();
    const [intent, setIntent] = useState("");
    const [result, setResult] = useState<{ intent: string; context: unknown; answer?: string } | null>(null);
    const [streamedAnswer, setStreamedAnswer] = useState("");
    const [loading, setLoading] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const [error, setError] = useState("");
    const [showContext, setShowContext] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        const displayAnswer = streamedAnswer || (result?.answer && !isMockAnswer(result?.answer) ? result.answer : "");
        if (!displayAnswer) return;
        try {
            await navigator.clipboard.writeText(displayAnswer);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (e) {
            console.error("Failed to copy text", e);
        }
    };

    const MOCK_SIGNATURE = "Based strictly on the compiled context, the conclusion holds for intent";

    const isMockAnswer = (text: string | undefined): boolean => {
        if (!text) return true;
        return text.includes(MOCK_SIGNATURE) || text.includes("MOCK INFERENCE");
    };

    const submit = async () => {
        if (!intent.trim()) return;
        setLoading(true);
        setStreaming(false);
        setStreamedAnswer("");
        setResult(null);
        setError("");
        setShowContext(false);
        try {
            // Synchronous fallback/context load
            const data = await get<{ intent: string; context: unknown; answer?: string }>(`/api/knowledge/reason?q=${encodeURIComponent(intent)}`);
            setResult(data);
            setLoading(false);

            // If the sync call already returned a real (non-mock) answer, use it directly — skip streaming
            if (data.answer && !isMockAnswer(data.answer)) {
                setStreamedAnswer(data.answer);
                return;
            }

            // Trigger streaming inference (only if sync answer was missing or mock)
            setStreaming(true);
            setStreamedAnswer("");
            const res = await apiFetch(`/api/knowledge/reason/stream?q=${encodeURIComponent(intent)}`);
            if (!res.body) return;
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = "";
            let abortedAsMock = false;
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n");
                for (const l of lines) {
                    if (l.startsWith("data:")) {
                        const payload = l.slice(5).trim();
                        if (payload === "[DONE]") break;
                        try {
                            const parsed = JSON.parse(payload);
                            if (parsed.token) {
                                accumulated += parsed.token;
                                // Detect mock answer early and abort streaming
                                if (isMockAnswer(accumulated)) {
                                    abortedAsMock = true;
                                    reader.cancel();
                                    break;
                                }
                                setStreamedAnswer(prev => prev + parsed.token);
                            }
                            if (parsed.error) {
                                setError(`Groq inference error: ${parsed.error}`);
                                reader.cancel();
                                break;
                            }
                        } catch { /* ignore partial json */ }
                    }
                }
                if (abortedAsMock) break;
            }

            if (abortedAsMock) {
                setStreamedAnswer("");
                setError("LLM inference returned a mock/fallback response — Groq API keys may be rate-limited or unreachable. Compiled context is still shown below. Try again in ~60 seconds.");
                setShowContext(true);
            }
        } catch (e: any) {
            setError(e.message ?? "Reasoning failed");
        } finally {
            setLoading(false);
            setStreaming(false);
        }
    };

    return (
        <div className="flex flex-col h-full space-y-4 pr-1 overflow-y-auto">
            <div>
                <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase">Probabilistic Reasoning Engine</h2>
                <p className="text-[10px] font-mono text-[var(--nova-muted)]">Groq Llama-3.1-8B inference strictly confined to compiled context from deterministic Knowledge Commits.</p>
            </div>

            <div className="flex gap-2">
                <input
                    value={intent}
                    onChange={e => setIntent(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && submit()}
                    placeholder="Why did we switch our primary database to SQLite?"
                    className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-3 py-2 text-xs font-mono text-[var(--nova-text)] focus:outline-none focus:border-[var(--nova-accent)] placeholder:text-[var(--nova-muted)]"
                />
                <button
                    onClick={submit}
                    disabled={!intent.trim() || loading || streaming}
                    className="bg-[var(--nova-accent)] text-black font-bold px-4 py-2 rounded text-xs font-mono uppercase tracking-wider hover:brightness-110 disabled:opacity-40 transition-all shadow-[0_0_10px_rgba(0,255,204,0.2)]"
                >
                    {loading ? "Compiling Context..." : streaming ? "Streaming..." : "⚡ Reason"}
                </button>
            </div>

            {error && <div className="text-xs font-mono text-[var(--nova-red)] p-3 bg-[var(--nova-red)]/10 border border-[var(--nova-red)]/30 rounded">{error}</div>}

            <div className="flex-1 space-y-4">
                {!result && !loading && !streaming && (
                    <div className="text-xs font-mono text-[var(--nova-muted)] text-center my-16 border border-dashed border-[var(--nova-border)]/50 rounded-lg p-8">
                        Submit an inquiry above. The reasoning compiler will construct immutable facts, and Groq will inference the explanation.
                    </div>
                )}

                {loading && <div className="text-xs font-mono text-[var(--nova-muted)] animate-pulse text-center mt-12">Compiling deterministic knowledge graph projection...</div>}

                {/* Streamed LLM Answer Block — only show real (non-mock) answers */}
                {(() => {
                    const displayAnswer = streamedAnswer || (result?.answer && !isMockAnswer(result.answer) ? result.answer : "");
                    return displayAnswer ? (
                    <div className="bg-[var(--nova-surface)] border border-[var(--nova-accent)]/40 rounded-lg p-5 shadow-[0_4px_20px_rgba(0,255,204,0.05)]">
                        <div className="flex items-center justify-between mb-3 border-b border-[var(--nova-border)]/50 pb-2.5">
                            <div className="flex items-center gap-4">
                                <span className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase flex items-center gap-2 font-bold">
                                    <span className="w-2.5 h-2.5 rounded-full bg-[var(--nova-accent)] animate-pulse" />
                                    Authoritative AI Answer
                                </span>
                                <button
                                    onClick={handleCopy}
                                    className="px-2 py-1 text-[9px] font-mono border border-[var(--nova-border)] rounded hover:border-[var(--nova-accent)] hover:text-[var(--nova-accent)] transition-all flex items-center gap-1 uppercase text-[var(--nova-muted)]"
                                    title="Copy Analysis"
                                >
                                    {copied ? "✓ Copied" : "❏ Copy"}
                                </button>
                            </div>
                            <span className="text-[10px] font-mono text-[var(--nova-muted)]">Groq Read-Only Inference</span>
                        </div>
                        <div className="pt-2 select-text">
                            <MarkdownRenderer content={displayAnswer} className="text-[15px] leading-relaxed font-sans" />
                        </div>
                    </div>
                    ) : null;
                })()}

                {/* Compiled Context Block */}
                {result && (
                    <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg overflow-hidden transition-all shadow-md">
                        <button
                            onClick={() => setShowContext(!showContext)}
                            className="w-full p-3.5 flex items-center justify-between text-xs font-mono tracking-widest text-[var(--nova-muted)] uppercase hover:text-[var(--nova-text)] hover:bg-[var(--nova-surface2)]/40 transition-colors text-left font-semibold"
                        >
                            <span className="flex items-center gap-2">
                                <span className="text-[var(--nova-accent)] text-sm">{showContext ? "▼" : "▶"}</span>
                                <span>Compiled Ground-Truth Context (NAS-001..011)</span>
                            </span>
                            <span className="text-[10px] text-[var(--nova-muted)] font-normal lowercase">click to {showContext ? "hide" : "expand"}</span>
                        </button>
                        {showContext && (
                            <div className="p-3.5 pt-1 border-t border-[var(--nova-border)]/30">
                                <pre className="text-xs font-mono text-[var(--nova-text)] whitespace-pre-wrap bg-[var(--nova-surface2)] p-3 rounded border border-[var(--nova-border)]/50 overflow-x-auto max-h-[350px] leading-relaxed select-text">
                                    {typeof result.context === "string" ? result.context : JSON.stringify(result.context, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
