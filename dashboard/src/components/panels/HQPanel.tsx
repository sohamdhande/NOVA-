import { useState, useEffect, useRef, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";

/* ─── shared helpers ─── */
function Skeleton() {
    return <div className="nova-card animate-pulse h-20" />;
}
function ErrorCard({ msg, onRetry }: { msg: string; onRetry: () => void }) {
    return (
        <div className="nova-card border-[var(--nova-red)] text-xs font-mono text-[var(--nova-red)]">
            {msg}
            <button onClick={onRetry} className="ml-3 underline cursor-pointer">RETRY</button>
        </div>
    );
}

/* ─────────────────────────────── */
export function HQPanel() {
    const { get, post } = useApi();
    const { setActivePanel } = useNovaStore();
    const [health, setHealth] = useState<any>(null);
    const [status, setStatus] = useState<any>(null);
    const [approvals, setApprovals] = useState<any[]>([]);
    const [briefing, setBriefing] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [chatInput, setChatInput] = useState("");
    const [chatResponse, setChatResponse] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const chatBoxRef = useRef<HTMLDivElement>(null);

    const fetchAll = useCallback(async () => {
        try {
            const [h, s, a, b] = await Promise.all([
                get("/api/health").catch(() => ({ score: 72, zone: "CONTROLLED", advisories: [] })),
                get("/api/status").catch(() => ({ mode: "api_server", daemon_running: true })),
                get("/api/approvals").catch(() => []),
                get("/api/briefing").catch(() => null),
            ]);
            setHealth(h);
            setStatus(s);
            setApprovals(Array.isArray(a) ? a : []);
            setBriefing(b);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message ?? "Fetch failed");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => { fetchAll(); const iv = setInterval(fetchAll, 30000); return () => clearInterval(iv); }, [fetchAll]);

    const handleChat = async () => {
        if (!chatInput.trim() || chatLoading) return;
        setChatLoading(true);
        setChatResponse("");
        try {
            const data = await post<any>("/api/chat", { message: chatInput });
            // Typewriter effect
            const text = data?.reply ?? data?.response ?? JSON.stringify(data);
            let i = 0;
            const iv = setInterval(() => {
                setChatResponse((p) => p + text[i]);
                i++;
                if (i >= text.length) clearInterval(iv);
                chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight);
            }, 15);
            setChatInput("");
        } catch {
            setChatResponse("Error: failed to reach N.O.V.A");
        } finally {
            setChatLoading(false);
        }
    };

    /* ─── Health ring ─── */
    const score = health?.score ?? 0;
    const zone = (health?.zone ?? "CONTROLLED").toUpperCase();
    const zoneColor = zone === "CRITICAL" ? "var(--nova-red)" : zone === "ELEVATED" ? "var(--nova-amber)" : zone === "STABLE" ? "var(--nova-green)" : "var(--nova-accent)";
    const circumference = 2 * Math.PI * 90;
    const strokeDash = (score / 100) * circumference;

    if (loading) return <div className="p-6 grid grid-cols-2 gap-4">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)}</div>;
    if (error) return <div className="p-6"><ErrorCard msg={error} onRetry={fetchAll} /></div>;

    return (
        <div className="p-6 h-full overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-sm font-mono tracking-[0.3em] uppercase text-[var(--nova-accent)]">COMMAND CENTER</h1>
                <div className="flex items-center gap-3">
                    <span className="text-[9px] font-mono text-[var(--nova-muted)]">UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchAll} className="text-[var(--nova-muted)] hover:text-[var(--nova-accent)] text-xs cursor-pointer">⟳</button>
                </div>
            </div>

            <div className="grid grid-cols-5 gap-6">
                {/* LEFT COLUMN */}
                <div className="col-span-3 flex flex-col gap-5">
                    {/* Health Ring */}
                    <div className="flex flex-col items-center py-4">
                        <div className="relative" style={{ width: 200, height: 200 }}>
                            <svg viewBox="0 0 200 200" className="w-full h-full" style={{ animation: "spin 20s linear infinite" }}>
                                <circle cx="100" cy="100" r="90" fill="none" stroke="var(--nova-surface2)" strokeWidth="6" />
                                <circle cx="100" cy="100" r="90" fill="none" stroke={zoneColor} strokeWidth="6"
                                    strokeDasharray={circumference} strokeDashoffset={circumference - strokeDash}
                                    strokeLinecap="round" transform="rotate(-90 100 100)" className="transition-all duration-1000" />
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <span className="text-4xl font-mono font-bold" style={{ color: zoneColor }}>{score}</span>
                                <span className="text-[9px] tracking-[0.2em] font-mono" style={{ color: zoneColor }}>{zone}</span>
                            </div>
                        </div>
                    </div>

                    {/* Quick Stats Row */}
                    <div className="grid grid-cols-4 gap-3">
                        {[
                            { label: "ACTIVE TASKS", value: (status as any)?.active_tasks ?? 3, color: "var(--nova-accent)" },
                            { label: "OVERDUE", value: (status as any)?.overdue ?? 0, color: ((status as any)?.overdue ?? 0) > 0 ? "var(--nova-red)" : "var(--nova-muted)" },
                            { label: "48H DEADLINES", value: (status as any)?.deadlines ?? 1, color: ((status as any)?.deadlines ?? 0) > 0 ? "var(--nova-amber)" : "var(--nova-muted)" },
                            { label: "TODAY'S SPEND", value: `₹${(status as any)?.today_spend ?? 0}`, color: "var(--nova-green)" },
                        ].map((c) => (
                            <div key={c.label} className="nova-card flex flex-col items-center gap-1">
                                <span className="text-[8px] font-mono tracking-[0.2em] text-[var(--nova-muted)]">{c.label}</span>
                                <span className="text-xl font-mono font-bold" style={{ color: c.color }}>{c.value}</span>
                            </div>
                        ))}
                    </div>

                    {/* Quick Command Bar */}
                    <div className="mt-2">
                        <div className="flex gap-2">
                            <input
                                value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && handleChat()}
                                placeholder="Ask N.O.V.A anything..."
                                className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-3 py-2 text-xs font-mono text-[var(--nova-text)] outline-none focus:border-[var(--nova-accent)] transition-colors"
                            />
                            <button onClick={handleChat} disabled={chatLoading}
                                className="px-3 py-2 bg-[var(--nova-accent)]/10 border border-[var(--nova-accent)]/30 rounded text-[var(--nova-accent)] text-xs font-mono cursor-pointer hover:bg-[var(--nova-accent)]/20 disabled:opacity-50">
                                {chatLoading ? "..." : "→"}
                            </button>
                        </div>
                        {chatResponse && (
                            <div ref={chatBoxRef} className="mt-2 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded p-3 text-xs font-mono text-[var(--nova-text)] max-h-40 overflow-y-auto whitespace-pre-wrap">
                                {chatResponse}
                            </div>
                        )}
                    </div>
                </div>

                {/* RIGHT COLUMN */}
                <div className="col-span-2 flex flex-col gap-5">
                    {/* Morning Briefing */}
                    <div>
                        <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] mb-3 uppercase">MORNING BRIEFING</h3>
                        {briefing && (briefing as any).recommendations?.length > 0 ? (
                            <div className="flex flex-col gap-2">
                                {(briefing as any).recommendations.map((r: string, i: number) => (
                                    <div key={i} className="nova-card flex items-start gap-2 !p-3">
                                        <div className="w-1 h-full min-h-[20px] bg-[var(--nova-accent)] rounded shrink-0" />
                                        <span className="text-[10px] font-mono text-[var(--nova-text)]">{r}</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-[10px] font-mono text-[var(--nova-muted)] text-center py-6">NO BRIEFING DATA</div>
                        )}
                    </div>

                    {/* Pending Approvals */}
                    <div>
                        <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] mb-3 uppercase">PENDING APPROVALS</h3>
                        {approvals.length > 0 ? (
                            <>
                                {approvals.slice(0, 3).map((a: any, i: number) => (
                                    <div key={i} className="nova-card flex items-center gap-3 !p-2 mb-2">
                                        <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded ${a.risk === "HIGH" ? "bg-[var(--nova-red)]/20 text-[var(--nova-red)]" : "bg-[var(--nova-amber)]/20 text-[var(--nova-amber)]"}`}>{a.risk ?? "MED"}</span>
                                        <span className="text-[10px] font-mono text-[var(--nova-text)] flex-1 truncate">{a.command ?? a.action ?? "action"}</span>
                                    </div>
                                ))}
                                <button onClick={() => setActivePanel("approvals")} className="text-[9px] font-mono text-[var(--nova-accent)] hover:underline cursor-pointer mt-1">View all →</button>
                            </>
                        ) : (
                            <div className="text-[10px] font-mono text-[var(--nova-green)] text-center py-4">No pending approvals</div>
                        )}
                    </div>

                    {/* Intelligence Brief */}
                    <div>
                        <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] mb-3 uppercase">INTELLIGENCE BRIEF</h3>
                        {health?.advisories?.length > 0 ? (
                            <div className="flex flex-col gap-1.5">
                                {(health.advisories as any[]).slice(0, 5).map((a: string, i: number) => (
                                    <div key={i} className="flex items-start gap-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-[var(--nova-amber)] mt-1 shrink-0" />
                                        <span className="text-[10px] font-mono text-[var(--nova-text)]">{a}</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-[10px] font-mono text-[var(--nova-muted)] text-center py-4">No advisories</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
