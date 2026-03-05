import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function ApprovalsPanel() {
    const { get, post } = useApi();
    const [pending, setPending] = useState<any[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [stats, setStats] = useState({ pending: 0, approvedToday: 0, deniedToday: 0 });
    const [sessionStatus, setSessionStatus] = useState({ active: false, expires_in: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    const fetchAll = useCallback(async () => {
        try {
            const [approvalsRes, historyRes, sessionRes] = await Promise.all([
                get("/api/approvals").catch(() => []),
                get("/api/approvals?status=resolved").catch(() => []),
                get("/api/status").catch(() => ({ biometric_session: { active: false, expires_in: 0 } }))
            ]);

            const pList = Array.isArray(approvalsRes) ? approvalsRes : [];
            const hList = Array.isArray(historyRes) ? historyRes : [];

            setPending(pList);
            setHistory(hList);

            const approvedCount = hList.filter(x => x.status === 'approved' && new Date(x.timestamp).toDateString() === new Date().toDateString()).length;
            const deniedCount = hList.filter(x => x.status === 'denied' && new Date(x.timestamp).toDateString() === new Date().toDateString()).length;

            setStats({
                pending: pList.length,
                approvedToday: approvedCount || 0, // Fallbacks
                deniedToday: deniedCount || 0
            });

            // Mock or actual session status based on backend
            setSessionStatus((sessionRes as any)?.biometric_session || { active: false, expires_in: 0 });

            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch approvals");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchAll();
        const iv = setInterval(fetchAll, 10000);
        return () => clearInterval(iv);
    }, [fetchAll]);

    const handleAction = async (id: string, action: 'approve' | 'deny', modifiedData?: any) => {
        try {
            await post(`/api/approvals/${id}/${action}`, modifiedData || {});
            // Optimistic update
            setPending(prev => prev.filter(p => p.id !== id));
            fetchAll();
        } catch (e) {
            console.error("Action failed", e);
        }
    };

    const unlockSession = async () => {
        try {
            await post("/api/nova/biometric-unlock", {});
            fetchAll();
        } catch (e) {
            console.error("Unlock failed", e);
        }
    };

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">APPROVAL PANEL</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchAll} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            <div className="grid grid-cols-4 gap-4">
                <div className="nova-card flex flex-col items-center justify-center p-4">
                    <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">PENDING</span>
                    <span className={`text-2xl ${stats.pending > 0 ? 'text-[var(--nova-red)]' : 'text-[var(--nova-green)]'}`}>{stats.pending}</span>
                </div>
                <div className="nova-card flex flex-col items-center justify-center p-4">
                    <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">APPROVED TODAY</span>
                    <span className="text-2xl text-[var(--nova-green)]">{stats.approvedToday}</span>
                </div>
                <div className="nova-card flex flex-col items-center justify-center p-4">
                    <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)]">DENIED TODAY</span>
                    <span className="text-2xl text-[var(--nova-muted)]">{stats.deniedToday}</span>
                </div>
                <div className="nova-card flex flex-col items-center justify-center p-4">
                    <span className="text-[9px] uppercase tracking-wider text-[var(--nova-muted)] mb-1">SESSION</span>
                    <span className={`text-xs ${sessionStatus.active ? 'text-[var(--nova-green)]' : 'text-[var(--nova-amber)]'}`}>
                        {sessionStatus.active ? `ACTIVE (${sessionStatus.expires_in}m)` : 'EXPIRED'}
                    </span>
                    {!sessionStatus.active && (
                        <button onClick={unlockSession} className="mt-2 text-[10px] bg-[var(--nova-accent)]/10 text-[var(--nova-accent)] px-2 py-1 rounded hover:bg-[var(--nova-accent)]/20 cursor-pointer">
                            UNLOCK SESSION
                        </button>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
                <div className="flex flex-col gap-4">
                    <h2 className="text-[10px] tracking-widest text-[var(--nova-muted)]">PENDING QUEUE</h2>
                    {pending.length === 0 ? (
                        <div className="nova-card flex items-center justify-center h-32 text-xs text-[var(--nova-muted)]">No pending approvals</div>
                    ) : (
                        pending.map(p => (
                            <ApprovalCard key={p.id} item={p} onAction={handleAction} />
                        ))
                    )}
                </div>

                <div className="flex flex-col gap-4">
                    <h2 className="text-[10px] tracking-widest text-[var(--nova-muted)]">ACTION HISTORY</h2>
                    <div className="nova-card overflow-y-auto max-h-[500px] flex flex-col bg-[var(--nova-surface)]">
                        {history.slice(0, 20).map((h, i) => (
                            <div key={i} className="flex flex-col gap-1 p-3 border-b border-[var(--nova-border)] last:border-0 hover:bg-[var(--nova-surface2)] transition-colors">
                                <div className="flex justify-between text-xs">
                                    <span className="text-[var(--nova-muted)]">{new Date(h.timestamp || Date.now()).toLocaleTimeString()}</span>
                                    <span className={h.status === 'approved' ? 'text-[var(--nova-green)]' : 'text-[var(--nova-red)]'}>
                                        {h.status?.toUpperCase()}
                                    </span>
                                </div>
                                <div className="text-[10px] text-[var(--nova-text)] truncate">{h.command || h.action || h.reason}</div>
                            </div>
                        ))}
                        {history.length === 0 && <div className="p-6 text-center text-xs text-[var(--nova-muted)]">No history found</div>}
                    </div>
                </div>
            </div>
        </div>
    );
}

function ApprovalCard({ item, onAction }: { item: any, onAction: (id: string, a: 'approve' | 'deny', mod?: any) => void }) {
    const isHigh = item.risk === 'HIGH';
    const border = isHigh ? 'border-[var(--nova-red)]' : 'border-[var(--nova-amber)]';
    const bg = isHigh ? 'bg-[var(--nova-red)]' : 'bg-[var(--nova-amber)]';
    const textColor = isHigh ? 'text-[var(--nova-red)]' : 'text-[var(--nova-amber)]';

    const [isModifying, setIsModifying] = useState(false);
    const [modText, setModText] = useState(item.command || item.action || '');

    return (
        <div className={`nova-card !p-4 border ${border} flex flex-col gap-3 relative overflow-hidden transition-all duration-300`}>
            <div className={`absolute left-0 top-0 bottom-0 w-1 ${bg}`} />

            <div className={`text-xs ${textColor} border-b ${border}/30 pb-2`}>
                ┌─ APPROVAL REQUIRED
            </div>

            <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${bg} text-black`}>[{item.risk || 'MEDIUM'}]</span>
                <span className="text-xs text-[var(--nova-text)] truncate font-bold">{item.command || item.action || 'Unknown Action'}</span>
            </div>

            <div className="text-[10px] text-[var(--nova-muted)] grid grid-cols-[60px_1fr] gap-1">
                <span>Source:</span><span className="text-[var(--nova-text)]">{item.source || 'controller'}</span>
                <span>Time:</span><span className="text-[var(--nova-text)]">{new Date(item.timestamp || Date.now()).toLocaleTimeString()}</span>
                <span>Reason:</span><span className="text-[var(--nova-text)]">{item.reason || 'Manual review required based on risk profile.'}</span>
            </div>

            {isModifying ? (
                <div className="flex flex-col gap-2 mt-2">
                    <input
                        value={modText}
                        onChange={e => setModText(e.target.value)}
                        className="bg-black/50 border border-[var(--nova-accent)] rounded p-1 text-xs text-[var(--nova-text)] w-full outline-none"
                    />
                    <div className="flex gap-2 justify-end">
                        <button onClick={() => setIsModifying(false)} className="text-[10px] text-[var(--nova-muted)] hover:text-white cursor-pointer px-2">CANCEL</button>
                        <button onClick={() => onAction(item.id, 'approve', { command: modText })} className="text-[10px] text-[var(--nova-accent)] hover:text-white cursor-pointer border border-[var(--nova-accent)] px-2 py-1 rounded">SUBMIT MODIFIED</button>
                    </div>
                </div>
            ) : (
                <div className="flex gap-3 mt-2">
                    <button onClick={() => onAction(item.id, 'approve')} className="flex-1 border-b border-[var(--nova-green)] text-[var(--nova-green)] hover:bg-[var(--nova-green)]/10 text-xs py-1 cursor-pointer transition-colors text-center">[APPROVE ✓]</button>
                    <button onClick={() => onAction(item.id, 'deny')} className="flex-1 border-b border-[var(--nova-red)] text-[var(--nova-red)] hover:bg-[var(--nova-red)]/10 text-xs py-1 cursor-pointer transition-colors text-center">[DENY ✗]</button>
                    <button onClick={() => setIsModifying(true)} className="flex-1 border-b border-[var(--nova-accent)] text-[var(--nova-accent)] hover:bg-[var(--nova-accent)]/10 text-xs py-1 cursor-pointer transition-colors text-center">[MODIFY ✎]</button>
                </div>
            )}
        </div>
    );
}
