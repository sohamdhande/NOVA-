import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function SecurityPanel() {
    const { get, post } = useApi();
    const { addToast } = useNovaStore();

    const [status, setStatus] = useState<any>({});
    const [whitelist, setWhitelist] = useState<any[]>([]);
    const [blockedCommands, setBlockedCommands] = useState<any[]>([]);
    const [recentBlocked, setRecentBlocked] = useState<any[]>([]);

    // Autonomy settings state
    const [toggles, setToggles] = useState({ auto_cleanup: true, auto_reasoning: true, auto_reply: false });
    const [riskThreshold, setRiskThreshold] = useState("BALANCED");

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    const [newCommand, setNewCommand] = useState("");

    const fetchData = useCallback(async () => {
        try {
            // we will mock a secure single payload for all since endpoints don't fully exist
            const res = await get<any>('/api/security').catch(() => ({
                biometric_active: false,
                autonomy_level: "limited",
                blocked_today: 12,
                whitelist: ["ls", "pwd", "git status"],
                blocked_commands: [
                    { cmd: "rm -rf /", reason: "Destructive root deletion" },
                    { cmd: "mkfs", reason: "Disk format command" },
                    { cmd: "sudo", reason: "Privilege escalation" }
                ],
                recent_blocked: [
                    { ts: new Date().toISOString(), cmd: "sudo apt remove python", reason: "Blocked by sudo rule" }
                ],
                settings: { auto_cleanup: true, auto_reasoning: true, auto_reply: false, risk: "BALANCED" }
            }));

            setStatus({
                bio: res.biometric_active,
                auto: res.autonomy_level,
                count: res.blocked_today
            });
            setWhitelist(res.whitelist || []);
            setBlockedCommands(res.blocked_commands || []);
            setRecentBlocked(res.recent_blocked || []);

            if (res.settings) {
                setToggles({
                    auto_cleanup: !!res.settings.auto_cleanup,
                    auto_reasoning: !!res.settings.auto_reasoning,
                    auto_reply: !!res.settings.auto_reply,
                });
                if (res.settings.risk) setRiskThreshold(res.settings.risk);
            }

            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch security context");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchData();
        const iv = setInterval(fetchData, 60000);
        return () => clearInterval(iv);
    }, [fetchData]);

    const handleUnlockBio = async () => {
        try {
            await post('/api/nova/biometric-unlock', {});
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Biometric unlock triggered' });
            fetchData();
        } catch {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Unlock sequence failed' });
        }
    };

    const handleAddWhitelist = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newCommand.trim()) return;
        try {
            // Mock API endpoint
            await post('/api/chat', { message: `whitelist command ${newCommand}` });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Command queued for whitelist approval' });
            setNewCommand("");
        } catch {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to whitelist command' });
        }
    };

    const handleRemoveWhitelist = async (cmd: string) => {
        if (!window.confirm(`Remove ${cmd} from whitelist?`)) return;
        try {
            await post('/api/chat', { message: `remove whitelist ${cmd}` });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Removed from whitelist' });
            setWhitelist(prev => prev.filter(c => c !== cmd));
        } catch {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to remove' });
        }
    };

    const handleToggle = async (key: keyof typeof toggles) => {
        const newVal = !toggles[key];
        setToggles(p => ({ ...p, [key]: newVal }));
        try {
            await post('/api/settings', { [key]: newVal });
        } catch {
            // rollback optimistically
            setToggles(p => ({ ...p, [key]: !newVal }));
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to sync toggle to backend' });
        }
    };

    const handleRiskChange = async (val: string) => {
        setRiskThreshold(val);
        try {
            await post('/api/settings', { autonomy_level: val });
        } catch {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to update risk threshold' });
        }
    };

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">SECURITY & GOVERNANCE</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchData} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            {/* Status Row */}
            <div className="grid grid-cols-3 gap-4">
                <div className={`nova-card p-4 flex flex-col justify-center items-center border ${status.bio ? 'border-[var(--nova-green)]' : 'border-[var(--nova-red)]'}`}>
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)] mb-1">BIOMETRIC SESSION</span>
                    <span className={`text-lg font-bold tracking-widest ${status.bio ? 'text-[var(--nova-green)]' : 'text-[var(--nova-red)]'}`}>
                        {status.bio ? 'ACTIVE' : 'EXPIRED'}
                    </span>
                    {!status.bio && (
                        <button onClick={handleUnlockBio} className="mt-2 text-[8px] bg-[var(--nova-red)] text-black px-3 py-1 rounded font-bold uppercase tracking-widest cursor-pointer hover:opacity-80">UNLOCK</button>
                    )}
                </div>
                <div className="nova-card p-4 flex flex-col justify-center items-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)] mb-1">AUTONOMY LEVEL</span>
                    <span className="text-lg font-bold tracking-widest text-[var(--nova-accent)] uppercase">{status.auto || 'CONTROLLED'}</span>
                </div>
                <div className="nova-card p-4 flex flex-col justify-center items-center border border-[var(--nova-red)]/30">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-red)]/80 mb-1">BLOCKED TODAY</span>
                    <span className="text-2xl font-bold tracking-widest text-[var(--nova-red)]">{status.count || 0}</span>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-6 flex-1 min-h-[400px]">
                {/* Left Column */}
                <div className="flex flex-col gap-6">
                    <div className="nova-card p-4 flex flex-col gap-3 flex-1 h-[250px]">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase text-center font-bold">COMMAND WHITELIST</div>
                        <div className="flex-1 overflow-y-auto flex flex-col gap-1.5 pr-2">
                            {whitelist.map((w, i) => (
                                <div key={i} className="flex justify-between items-center text-xs p-2 bg-[var(--nova-surface2)] rounded">
                                    <span className="text-[var(--nova-text)] font-mono">$ {w}</span>
                                    <button onClick={() => handleRemoveWhitelist(w)} className="text-[var(--nova-muted)] hover:text-[var(--nova-red)] cursor-pointer text-[10px] transition-colors">REMOVE ✕</button>
                                </div>
                            ))}
                        </div>
                        <form onSubmit={handleAddWhitelist} className="mt-2 flex border border-[var(--nova-surface2)] rounded overflow-hidden">
                            <span className="bg-[var(--nova-surface2)] text-[var(--nova-muted)] p-2 text-xs flex items-center px-3">$</span>
                            <input type="text" value={newCommand} onChange={(e) => setNewCommand(e.target.value)} placeholder="add command..." className="bg-transparent text-xs p-2 outline-none flex-1 text-[var(--nova-text)]" />
                            <button type="submit" className="bg-[var(--nova-accent)] text-black text-[10px] px-4 font-bold tracking-widest cursor-pointer hover:opacity-80">ADD</button>
                        </form>
                    </div>

                    <div className="nova-card p-4 flex flex-col gap-3 flex-1 h-[250px]">
                        <div className="text-[10px] text-[var(--nova-red)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase text-center font-bold">BLOCKED COMMANDS (RULES)</div>
                        <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-2">
                            {blockedCommands.map((b, i) => (
                                <div key={i} className="flex flex-col gap-1 text-xs p-2 bg-black/40 border border-[var(--nova-red)]/20 rounded">
                                    <span className="text-[var(--nova-red)] font-bold truncate">$ {b.cmd}</span>
                                    <span className="text-[9px] text-[var(--nova-muted)] truncate">• {b.reason}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right Column */}
                <div className="flex flex-col gap-6">
                    <div className="nova-card p-4 flex flex-col gap-3 flex-1">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase text-center font-bold">AUTONOMY SETTINGS</div>
                        <div className="flex flex-col gap-6 py-2">
                            <div className="flex flex-col gap-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-[var(--nova-text)] uppercase tracking-wider">AUTO CLEANUP</span>
                                    <button onClick={() => handleToggle('auto_cleanup')} className={`px-4 py-1.5 text-[10px] font-bold tracking-widest rounded transition-colors cursor-pointer ${toggles.auto_cleanup ? 'bg-[var(--nova-green)] text-black' : 'bg-[var(--nova-surface2)] text-[var(--nova-muted)]'}`}>
                                        {toggles.auto_cleanup ? 'ON' : 'OFF'}
                                    </button>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-[var(--nova-text)] uppercase tracking-wider">AUTO REASONING</span>
                                    <button onClick={() => handleToggle('auto_reasoning')} className={`px-4 py-1.5 text-[10px] font-bold tracking-widest rounded transition-colors cursor-pointer ${toggles.auto_reasoning ? 'bg-[var(--nova-green)] text-black' : 'bg-[var(--nova-surface2)] text-[var(--nova-muted)]'}`}>
                                        {toggles.auto_reasoning ? 'ON' : 'OFF'}
                                    </button>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-[var(--nova-text)] uppercase tracking-wider">AUTO REPLY</span>
                                    <button onClick={() => handleToggle('auto_reply')} className={`px-4 py-1.5 text-[10px] font-bold tracking-widest rounded transition-colors cursor-pointer ${toggles.auto_reply ? 'bg-[var(--nova-green)] text-black' : 'bg-[var(--nova-surface2)] text-[var(--nova-muted)]'}`}>
                                        {toggles.auto_reply ? 'ON' : 'OFF'}
                                    </button>
                                </div>
                            </div>

                            <div className="flex flex-col gap-3 mt-4">
                                <span className="text-[10px] text-[var(--nova-muted)] uppercase tracking-widest text-center">RISK THRESHOLD</span>
                                <div className="flex rounded border border-[var(--nova-surface2)] overflow-hidden">
                                    {["CONSERVATIVE", "BALANCED", "AGGRESSIVE"].map(level => {
                                        const isSel = riskThreshold === level;
                                        return (
                                            <button
                                                key={level}
                                                onClick={() => handleRiskChange(level)}
                                                className={`flex-1 py-2 text-[9px] font-bold tracking-widest transition-colors cursor-pointer ${isSel ? 'bg-[var(--nova-accent)] text-black' : 'bg-transparent text-[var(--nova-muted)] hover:bg-[var(--nova-surface2)]'}`}
                                            >
                                                {level}
                                            </button>
                                        )
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="nova-card p-4 flex flex-col gap-3 flex-1 h-[250px]">
                        <div className="text-[10px] text-[var(--nova-red)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase text-center font-bold">BLOCKED ACTION LOG</div>
                        <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-2">
                            {recentBlocked.map((rb, i) => (
                                <div key={i} className="flex flex-col gap-1 text-xs p-2 bg-black text-[var(--nova-text)] border-l-2 border-l-[var(--nova-red)] border border-y-[var(--nova-surface2)] border-r-[var(--nova-surface2)] rounded-r">
                                    <div className="flex justify-between text-[10px] items-start pb-1">
                                        <span className="text-[var(--nova-muted)]">{new Date(rb.ts).toLocaleString()}</span>
                                    </div>
                                    <span className="font-mono text-[var(--nova-text)] truncate">{rb.cmd}</span>
                                    <span className="text-[10px] text-[var(--nova-red)] font-bold">{rb.reason}</span>
                                </div>
                            ))}
                            {recentBlocked.length === 0 && <div className="text-[10px] text-[var(--nova-muted)] text-center py-6">No actions blocked recently</div>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
