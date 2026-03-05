import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function BrowserPanel() {
    const { get, post } = useApi();
    const { addToast } = useNovaStore();

    const [status, setStatus] = useState<any>({});
    const [tasks, setTasks] = useState<any[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    // Action Form State
    const [activeAction, setActiveAction] = useState<string | null>(null);
    const [valUrl, setValUrl] = useState("");
    const [valSelector, setValSelector] = useState("");

    // Builder State
    const [bName, setBName] = useState("");
    const [bSteps, setBSteps] = useState("");
    const [bSchedule, setBSchedule] = useState("once");

    const fetchData = useCallback(async () => {
        try {
            const [statRes, autoRes, memRes] = await Promise.all([
                get<any>('/api/status').catch(() => ({ status: 'online' })), // using status as proxy for browser status for now
                get<any[]>('/api/automations').catch(() => []),
                get<any[]>('/api/memory').catch(() => [])
            ]);

            setStatus({
                playwright: 'READY',
                active_sessions: 0,
                last_action: 'Idle',
                last_action_time: new Date().toLocaleTimeString()
            });

            // Filter for browser
            const filteredAutos = Array.isArray(autoRes) ? autoRes.filter(a => a.category === 'browser') : [];
            setTasks(filteredAutos);

            const filteredHistory = Array.isArray(memRes) ? memRes.filter(m => m.source === 'browser') : [];
            setHistory(filteredHistory);

            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch browser data");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchData();
        const iv = setInterval(fetchData, 15000);
        return () => clearInterval(iv);
    }, [fetchData]);

    const handleExecuteAction = async () => {
        if (!valUrl) { addToast({ id: crypto.randomUUID(), type: 'error', message: 'URL required' }); return; }

        let msg = "";
        if (activeAction === "OPEN URL") msg = `open browser to ${valUrl}`;
        if (activeAction === "READ PAGE") msg = `read content from ${valUrl}`;
        if (activeAction === "SCREENSHOT") msg = `take screenshot of ${valUrl}`;
        if (activeAction === "SCRAPE DATA") msg = `scrape data from ${valUrl} using selector ${valSelector}`;

        try {
            await post('/api/chat', { message: msg });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Browser action dispatched' });
            setActiveAction(null);
            setValUrl("");
            setValSelector("");
        } catch (e) {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to dispatch action' });
        }
    };

    const handleSaveAutomation = async () => {
        if (!bName || !bSteps) { addToast({ id: crypto.randomUUID(), type: 'error', message: 'Name and steps required' }); return; }
        try {
            await post('/api/chat', { message: `Create browser automation named "${bName}" that does: ${bSteps} on schedule: ${bSchedule}` });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Automation mapped to HQ plan' });
            setBName(""); setBSteps("");
            fetchData();
        } catch (e) {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to save automation' });
        }
    };

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">BROWSER AUTOMATION</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchData} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            <div className="grid grid-cols-4 gap-4">
                {/* Status Card */}
                <div className="col-span-1 nova-card p-4 flex flex-col gap-3 justify-center">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-surface2)] pb-2 uppercase">ENGINE STATUS</div>
                    <div className="flex flex-col gap-2">
                        <div className="flex justify-between items-center text-xs">
                            <span className="text-[var(--nova-muted)]">Playwright:</span>
                            <span className="text-[var(--nova-green)] font-bold">{status.playwright}</span>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                            <span className="text-[var(--nova-muted)]">Active Sessions:</span>
                            <span className="text-[var(--nova-text)]">{status.active_sessions}</span>
                        </div>
                        <div className="flex flex-col gap-0.5 mt-2">
                            <span className="text-[10px] text-[var(--nova-muted)]">Last Action:</span>
                            <span className="text-xs text-[var(--nova-text)] truncate">{status.last_action}</span>
                            <span className="text-[9px] text-[var(--nova-muted)]">{status.last_action_time}</span>
                        </div>
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="col-span-3 nova-card p-4 flex flex-col justify-center border border-[rgba(0,255,204,0.1)] gap-4">
                    {activeAction ? (
                        <div className="flex flex-col gap-3 animate-in slide-in-from-right-4 duration-300">
                            <div className="flex items-center justify-between text-xs tracking-widest font-bold text-[var(--nova-accent)] border-b border-[var(--nova-surface2)] pb-2">
                                <span>{activeAction}</span>
                                <button onClick={() => setActiveAction(null)} className="text-[var(--nova-muted)] hover:text-white cursor-pointer">✕ CANCEL</button>
                            </div>
                            <input
                                type="text"
                                placeholder="Enter Target URL (https://...)"
                                className="bg-[var(--nova-surface2)] p-2 rounded outline-none text-xs w-full"
                                value={valUrl} onChange={e => setValUrl(e.target.value)} autoFocus
                            />
                            {activeAction === "SCRAPE DATA" && (
                                <input
                                    type="text"
                                    placeholder="CSS Selector (optional)"
                                    className="bg-[var(--nova-surface2)] p-2 rounded outline-none text-xs w-full"
                                    value={valSelector} onChange={e => setValSelector(e.target.value)}
                                />
                            )}
                            <button
                                onClick={handleExecuteAction}
                                className="bg-[var(--nova-accent)] text-black font-bold uppercase tracking-widest text-xs p-2 rounded hover:opacity-90 cursor-pointer w-32"
                            >
                                EXECUTE
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-4 gap-3">
                            {["OPEN URL", "READ PAGE", "SCREENSHOT", "SCRAPE DATA"].map(action => (
                                <button
                                    key={action}
                                    onClick={() => setActiveAction(action)}
                                    className="flex flex-col items-center justify-center gap-2 p-6 rounded border border-[var(--nova-surface2)] text-[10px] tracking-widest uppercase hover:text-[var(--nova-accent)] hover:border-[var(--nova-accent)] transition-all cursor-pointer bg-black/20"
                                >
                                    <span className="text-xl">🌐</span>
                                    <span>{action}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-6 flex-1 min-h-[350px]">
                {/* Left Col: Tasks & History */}
                <div className="flex flex-col gap-6">
                    <div className="nova-card p-4 flex flex-col gap-3 flex-1">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase text-center">ACTIVE BROWSER TASKS</div>
                        <div className="flex flex-col gap-2 overflow-y-auto">
                            {tasks.map((t, i) => (
                                <div key={i} className="flex items-center justify-between p-2 bg-[var(--nova-surface2)] rounded text-xs border border-[transparent] hover:border-[var(--nova-border)]">
                                    <div className="flex items-center gap-2 truncate">
                                        <span className={`w-2 h-2 rounded-full ${t.status === 'running' ? 'bg-[var(--nova-accent)] animate-pulse' : 'bg-gray-500'}`} />
                                        <span className="truncate">{t.name}</span>
                                    </div>
                                    <button className="text-[remove] hover:text-[var(--nova-red)] text-[10px] px-2 cursor-pointer transition-colors">CANCEL</button>
                                </div>
                            ))}
                            {tasks.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-6">No active browser tasks</div>}
                        </div>
                    </div>

                    <div className="nova-card p-4 flex flex-col gap-3 flex-1 h-[200px]">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase text-center">BROWSER HISTORY</div>
                        <div className="flex-1 overflow-y-auto flex flex-col gap-1.5 pr-1">
                            {history.slice(0, 10).map((h, i) => {
                                const payload = h.payload ? (typeof h.payload === 'string' ? JSON.parse(h.payload) : h.payload) : {};
                                const action = payload.action || 'Navigation';
                                const target = payload.url || payload.target || h.type;
                                const isSuccess = payload.success !== false;
                                return (
                                    <div key={i} className="flex items-center justify-between text-[10px] p-1.5 border-b border-[var(--nova-surface2)] last:border-0 hover:bg-black/20">
                                        <div className="flex items-center gap-2 truncate pr-2">
                                            <span className="text-[var(--nova-muted)] shrink-0">{new Date(h.timestamp || new Date()).toLocaleTimeString()}</span>
                                            <span className="text-[var(--nova-text)] truncate font-bold w-16 shrink-0">{action}</span>
                                            <span className="text-[var(--nova-muted)] truncate">{target}</span>
                                        </div>
                                        <span className={`shrink-0 font-bold ${isSuccess ? 'text-[var(--nova-green)]' : 'text-[var(--nova-red)]'}`}>
                                            {isSuccess ? 'YES' : 'FAIL'}
                                        </span>
                                    </div>
                                )
                            })}
                            {history.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-6">No historical records</div>}
                        </div>
                    </div>
                </div>

                {/* Right Col: Builder */}
                <div className="nova-card p-4 flex flex-col gap-4">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">AUTOMATION BUILDER</div>
                    <div className="flex flex-col gap-3 h-full">
                        <div className="flex flex-col gap-1">
                            <label className="text-[9px] text-[var(--nova-muted)] uppercase tracking-wider">Automation Name</label>
                            <input
                                type="text"
                                className="bg-[var(--nova-surface2)] text-xs text-[var(--nova-text)] p-2 rounded outline-none w-full border border-transparent focus:border-[var(--nova-accent)] transition-colors"
                                value={bName} onChange={e => setBName(e.target.value)}
                            />
                        </div>
                        <div className="flex flex-col gap-1 flex-1">
                            <label className="text-[9px] text-[var(--nova-muted)] uppercase tracking-wider">Sequential Steps</label>
                            <textarea
                                className="bg-[var(--nova-surface2)] text-xs text-[var(--nova-text)] p-2 rounded outline-none w-full border border-transparent focus:border-[var(--nova-accent)] transition-colors resize-none flex-1 font-mono leading-relaxed"
                                placeholder="1. Go to URL...&#10;2. Wait for selector...&#10;3. Click on..."
                                value={bSteps} onChange={e => setBSteps(e.target.value)}
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-[9px] text-[var(--nova-muted)] uppercase tracking-wider">Schedule Trigger</label>
                            <select
                                className="bg-[var(--nova-surface2)] text-xs text-[var(--nova-text)] p-2 rounded outline-none w-full cursor-pointer appearance-none border border-transparent focus:border-[var(--nova-accent)] transition-colors"
                                value={bSchedule} onChange={e => setBSchedule(e.target.value)}
                            >
                                <option value="once">Run Once Immediately</option>
                                <option value="hourly">Every Hour</option>
                                <option value="daily">Daily at 9:00 AM</option>
                                <option value="on_trigger">On specific trigger phrase</option>
                            </select>
                        </div>
                        <button
                            onClick={handleSaveAutomation}
                            className="bg-transparent border border-[var(--nova-accent)] text-[var(--nova-accent)] p-3 rounded font-bold tracking-[0.2em] uppercase text-xs hover:bg-[var(--nova-accent)] hover:text-black transition-colors mt-2 cursor-pointer"
                        >
                            SAVE AUTOMATION
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
