import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function ProductivityPanel() {
    const { get } = useApi();
    const [prod, setProd] = useState<any>({});
    const [goals, setGoals] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    const fetchProductivity = useCallback(async () => {
        try {
            const [pRes, gRes] = await Promise.all([
                get<any>('/api/productivity').catch(() => ({})),
                get<any>('/api/goals').catch(() => [])
            ]);
            setProd(pRes);
            setGoals(Array.isArray(gRes) ? gRes : (gRes?.goals || []));
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch productivity data");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchProductivity();
        const iv = setInterval(fetchProductivity, 30000);
        return () => clearInterval(iv);
    }, [fetchProductivity]);

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    const score = prod.score_today || 0;
    const scoreColor = score > 80 ? 'var(--nova-green)' : score > 60 ? 'var(--nova-accent)' : score > 40 ? 'var(--nova-amber)' : 'var(--nova-red)';
    const circumference = 2 * Math.PI * 70;
    const strokeDash = (score / 100) * circumference;

    const codingHours = prod.coding_hours || 0;
    const deepWork = prod.deep_work_hours || 0;
    const tasks = prod.tasks_completed || 0;
    const distractions = prod.distractions || 0;

    const dailyScores = prod.daily_scores || [0, 0, 0, 0, 0, 0, 0];
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">PRODUCTIVITY INSIGHTS</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchProductivity} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            <div className="grid grid-cols-5 gap-6">
                {/* LEFT COLUMN */}
                <div className="col-span-3 flex flex-col gap-5">

                    {/* TOP SECTION: SCORE & STATS */}
                    <div className="grid grid-cols-[160px_1fr] gap-6">

                        {/* SCORE RING */}
                        <div className="flex flex-col items-center justify-center relative w-[160px] h-[160px]">
                            <svg viewBox="0 0 160 160" className="w-full h-full -rotate-90">
                                <circle cx="80" cy="80" r="70" fill="none" stroke="var(--nova-surface2)" strokeWidth="8" />
                                <circle cx="80" cy="80" r="70" fill="none" stroke={scoreColor} strokeWidth="8"
                                    strokeDasharray={circumference} strokeDashoffset={circumference - strokeDash}
                                    strokeLinecap="round" className="transition-all duration-1000" />
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center mt-1">
                                <span className="text-3xl font-bold" style={{ color: scoreColor }}>{score}</span>
                                <span className="text-[8px] tracking-[0.2em] font-bold" style={{ color: scoreColor }}>SCORE TODAY</span>
                            </div>
                        </div>

                        {/* STATS GRID */}
                        <div className="grid grid-cols-2 gap-3 h-full">
                            <div className="nova-card flex flex-col items-center justify-center p-2">
                                <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">CODING HOURS</span>
                                <span className="text-xl text-[var(--nova-text)]">{codingHours}h</span>
                            </div>
                            <div className="nova-card flex flex-col items-center justify-center p-2">
                                <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">DEEP WORK</span>
                                <span className="text-xl text-[var(--nova-accent)]">{deepWork}h</span>
                            </div>
                            <div className="nova-card flex flex-col items-center justify-center p-2">
                                <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">TASK COMPLETION</span>
                                <span className="text-xl text-[var(--nova-green)]">{tasks}</span>
                            </div>
                            <div className="nova-card flex flex-col items-center justify-center p-2">
                                <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">DISTRACTIONS</span>
                                <span className={`text-xl ${distractions > 5 ? 'text-[var(--nova-red)]' : 'text-[var(--nova-text)]'}`}>{distractions}</span>
                            </div>
                        </div>
                    </div>

                    {/* CHART */}
                    <div className="nova-card p-4 flex flex-col gap-4">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">PERFORMANCE TREND (LAST 7 DAYS)</div>
                        <div className="flex items-end justify-between h-32 px-4 gap-2 mt-4">
                            {dailyScores.map((s: number, i: number) => {
                                const hAttr = Math.max(5, s);
                                const bColor = s > 80 ? 'bg-[var(--nova-green)]' : s > 60 ? 'bg-[var(--nova-accent)]' : s > 40 ? 'bg-[var(--nova-amber)]' : 'bg-[var(--nova-red)]';
                                return (
                                    <div key={i} className="flex flex-col items-center gap-2 flex-1 group">
                                        <span className="text-[9px] text-[var(--nova-muted)] opacity-0 group-hover:opacity-100 transition-opacity">{s}</span>
                                        <div className={`w-full max-w-[30px] rounded-t-sm ${bColor} transition-all duration-500`} style={{ height: `${hAttr}%`, opacity: 0.8 }} />
                                        <span className="text-[9px] text-[var(--nova-muted)] uppercase">{days[i]}</span>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    {/* GOAL TRACKING */}
                    <div className="nova-card p-4 flex flex-col gap-3">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">GOAL TRACKING</div>
                        <div className="flex flex-col gap-4">
                            {goals.map((g, i) => (
                                <div key={i} className="flex flex-col gap-1.5">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-[var(--nova-text)] truncate">{g.title || g.name}</span>
                                        <div className="flex items-center gap-3">
                                            <span className="text-[10px] text-[var(--nova-muted)]">{g.progress}%</span>
                                            <span className={`text-[8px] font-bold px-1 py-0.5 rounded uppercase ${g.status === 'completed' ? 'bg-[var(--nova-green)] text-black' : g.status === 'at_risk' ? 'bg-[var(--nova-red)] text-white' : 'bg-[var(--nova-surface2)] text-[var(--nova-muted)]'}`}>{g.status || 'ACTIVE'}</span>
                                        </div>
                                    </div>
                                    <div className="w-full bg-black/50 h-1.5 rounded-full overflow-hidden">
                                        <div className="h-full bg-[var(--nova-accent)] rounded-full transition-all duration-500" style={{ width: `${g.progress || 0}%` }} />
                                    </div>
                                </div>
                            ))}
                            {goals.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-2">No active goals</div>}
                        </div>
                    </div>

                </div>

                {/* RIGHT COLUMN */}
                <div className="col-span-2 flex flex-col gap-5">

                    {/* DAILY REPORT CARD */}
                    <div className="nova-card border-[rgba(0,255,204,0.1)] p-4 flex flex-col gap-3">
                        <div className="flex justify-between border-b border-[rgba(0,255,204,0.1)] pb-2 items-center">
                            <span className="text-[10px] text-[var(--nova-muted)] tracking-widest">┌─ TODAY'S REPORT</span>
                            <span className="text-[10px] text-[var(--nova-text)]">{new Date().toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}</span>
                        </div>
                        <div className="text-xs text-[var(--nova-text)] whitespace-pre-wrap leading-relaxed opacity-90 mt-1">
                            {prod.report_text || "Awaiting daily summary..."}
                        </div>

                        {(prod.missed_goals && prod.missed_goals.length > 0) && (
                            <div className="mt-3">
                                <div className="text-[10px] text-[var(--nova-red)] font-bold mb-1">Missed Goals:</div>
                                {prod.missed_goals.map((mg: string, i: number) => (
                                    <div key={i} className="text-xs text-[var(--nova-red)] opacity-90">✗ {mg}</div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* WEEKLY REPORT CARD */}
                    <div className="nova-card border-[rgba(0,255,204,0.1)] p-4 flex flex-col gap-3 flex-1">
                        <div className="flex justify-between border-b border-[rgba(0,255,204,0.1)] pb-2 items-center">
                            <span className="text-[10px] text-[var(--nova-muted)] tracking-widest">┌─ WEEKLY OVERVIEW</span>
                            <span className="text-[10px] text-[var(--nova-text)]">Recent 7 Days</span>
                        </div>
                        <div className="flex flex-col gap-2 mt-2">
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-[var(--nova-muted)]">Avg Score:</span>
                                <span className={`font-bold text-[var(--nova-text)]`}>{prod.weekly_avg || 0}</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-[var(--nova-muted)]">Best Day:</span>
                                <span className="font-bold text-[var(--nova-green)]">{prod.weekly_best_day || 'None'}</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-[var(--nova-muted)]">Total Coding:</span>
                                <span className="font-bold text-[var(--nova-text)]">{prod.weekly_coding_hours || 0}h</span>
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
