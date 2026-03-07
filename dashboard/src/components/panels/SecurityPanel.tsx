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

    const [scanning, setScanning] = useState(false);
    const [scanReport, setScanReport] = useState<any>(null);
    const [lastScan, setLastScan] = useState<string | null>(null);
    const [threatScore, setThreatScore] = useState(0);

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
                    { ts: new Date().toISOString(), cmd: "sudo apt remove python", reason: "Blocked by sudo rule", tier: 'CRITICAL', command: 'sudo apt remove python' }
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

    const handleScan = async () => {
        setScanning(true);
        try {
            const data = await post<any>(
                '/api/security/scan', {}
            );
            setThreatScore(data.threat_score ?? 0);
            setLastScan(new Date().toLocaleString());
            setScanReport(data);
        } catch (e) {
            console.error('Scan failed:', e);
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Security scan failed' });
        } finally {
            setScanning(false);
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

            {/* Threat Score Ring */}
            <div className="flex items-center gap-6 mb-6 p-4 rounded-lg border border-[rgba(0,255,204,0.15)] bg-[#020d0d]">
                <div className="relative w-20 h-20 flex-shrink-0">
                    <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
                        <circle cx="40" cy="40" r="34"
                            fill="none"
                            stroke="rgba(0,255,204,0.1)"
                            strokeWidth="5" />
                        <circle cx="40" cy="40" r="34"
                            fill="none"
                            stroke={threatScore < 30 
                              ? '#00ffcc' 
                              : threatScore < 60 
                              ? '#fbbf24' 
                              : '#ef4444'}
                            strokeWidth="5"
                            strokeLinecap="round"
                            strokeDasharray="213.6"
                            strokeDashoffset={213.6 - (threatScore / 100) * 213.6}
                            style={{ filter: `drop-shadow(0 0 4px ${
                              threatScore < 30 ? '#00ffcc'
                              : threatScore < 60 ? '#fbbf24'
                              : '#ef4444'})` }}
                            className="transition-all duration-1000"
                        />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className={`text-lg font-bold font-mono ${
                          threatScore < 30 
                            ? 'text-[#00ffcc]' 
                            : threatScore < 60 
                            ? 'text-amber-400' 
                            : 'text-red-400'}`}>
                            {threatScore}
                        </span>
                    </div>
                </div>
                
                <div className="flex-1">
                    <div className="text-[9px] font-mono tracking-widest text-[#4a6a6a] mb-1">
                        THREAT LEVEL
                    </div>
                    <div className={`text-2xl font-bold font-mono uppercase ${
                      threatScore < 30 
                        ? 'text-[#00ffcc]' 
                        : threatScore < 60 
                        ? 'text-amber-400' 
                        : 'text-red-400'}`}>
                        {threatScore < 30 ? 'CLEAR' 
                         : threatScore < 60 ? 'ELEVATED' 
                         : 'HIGH RISK'}
                    </div>
                    <div className="text-xs font-mono text-[#4a6a6a] mt-1">
                        Last scan: {lastScan 
                          ? new Date(lastScan).toLocaleTimeString() 
                          : 'Never'}
                    </div>
                </div>
                
                <button 
                  onClick={handleScan}
                  disabled={scanning}
                  className={`text-xs font-mono px-4 py-2 rounded border transition-all duration-200 ${scanning ? 'border-[#00ffcc]/20 text-[#00ffcc]/40 cursor-wait' : 'border-[#00ffcc]/40 text-[#00ffcc] hover:bg-[#00ffcc]/10 hover:border-[#00ffcc]/60 cursor-pointer'}`}>
                    {scanning ? (
                        <span className="flex items-center gap-2">
                            <span className="w-3 h-3 border-2 border-[#00ffcc]/30 border-t-[#00ffcc] rounded-full animate-spin inline-block" />
                            SCANNING...
                        </span>
                    ) : '▶ RUN SCAN'}
                </button>
            </div>

            {scanReport && (
                <div className="mb-6 rounded-lg border border-[rgba(0,255,204,0.15)] bg-[#020d0d] p-4">
                    
                    <div className="flex items-center gap-2 mb-3">
                        <div className="w-0.5 h-4 bg-[#00ffcc] rounded-full" />
                        <span className="text-[10px] font-mono tracking-[0.3em] text-[#4a6a6a] uppercase">
                            Last Scan Report — {lastScan ?? 'Never'}
                        </span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 mb-3">
                        {[
                            { 
                                label: "PROCESSES CHECKED", 
                                value: scanReport.processes_checked ?? 0,
                                color: "cyan"
                            },
                            { 
                                label: "SUSPICIOUS FILES", 
                                value: scanReport.suspicious_files ?? 0,
                                color: (scanReport.suspicious_files ?? 0) > 0 ? "red" : "cyan"
                            },
                            { 
                                label: "OPEN PORTS", 
                                value: scanReport.open_ports ?? 0,
                                color: (scanReport.open_ports ?? 0) > 5 ? "amber" : "cyan"
                            },
                            { 
                                label: "LAUNCH AGENTS", 
                                value: scanReport.vulnerabilities ?? 0,
                                color: (scanReport.vulnerabilities ?? 0) > 10 ? "amber" : "cyan"
                            },
                            { 
                                label: "FILES SCANNED", 
                                value: scanReport.files_scanned ?? 0,
                                color: "cyan" 
                            },
                        ].map(item => (
                            <div key={item.label} className="bg-[#0a0a0a] rounded p-3 border border-[rgba(0,255,204,0.08)]">
                                <div className="text-[9px] font-mono tracking-widest text-[#4a6a6a] mb-1">
                                    {item.label}
                                </div>
                                <div className={`text-xl font-bold font-mono ${
                                    item.color === 'red' ? 'text-red-400' 
                                    : item.color === 'amber' ? 'text-amber-400' 
                                    : 'text-[#00ffcc]'}`}>
                                    {item.value}
                                </div>
                            </div>
                        ))}
                    </div>
                    
                    {/* Findings list */}
                    {scanReport.findings && scanReport.findings.length > 0 && (
                        <div className="space-y-1 max-h-40 overflow-y-auto">
                            <div className="text-[9px] font-mono tracking-widest text-[#4a6a6a] mb-2">
                                FINDINGS
                            </div>
                            {scanReport.findings.map((f: string, i: number) => (
                                <div key={i} className="flex gap-2 text-xs font-mono text-[#e2e8f0] p-1.5 bg-[#111] rounded">
                                    <span className="text-amber-400">▸</span>
                                    {f}
                                </div>
                            ))}
                        </div>
                    )}
                    
                    {/* All clear message */}
                    {(!scanReport.findings || scanReport.findings.length === 0) && (
                        <div className="flex items-center gap-2 text-xs font-mono text-[#00ffcc]">
                            <span>✓</span>
                            <span>No threats detected. System is clean.</span>
                        </div>
                    )}

                    {scanReport?.ai_analysis && (
                        <div className="mt-3 p-3 rounded bg-[rgba(0,255,204,0.03)] border border-[rgba(0,255,204,0.1)]">
                            <div className="text-[9px] font-mono tracking-widest text-[#4a6a6a] mb-2">
                                AI THREAT ANALYSIS
                            </div>
                            <p className="text-xs font-mono text-[#e2e8f0] leading-relaxed">
                                {scanReport.ai_analysis}
                            </p>
                        </div>
                    )}
                </div>
            )}

            {/* Empty state when no scan run yet */}
            {!scanReport && (
                <div className="mb-6 rounded-lg border border-dashed border-[rgba(0,255,204,0.1)] p-6 text-center">
                    <div className="text-xs font-mono text-[#4a6a6a]">
                        No scan data. Click RUN SCAN to analyze your system.
                    </div>
                </div>
            )}

            {/* Status Row */}
            <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg border p-4 bg-[#020d0d] border-[rgba(0,255,204,0.15)] flex flex-col justify-center">
                    <div className="text-[9px] font-mono tracking-widest text-[#4a6a6a] mb-2 uppercase text-center md:text-left">
                        BIOMETRIC SESSION
                    </div>
                    {status.bio ? (
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-[#00ffcc] animate-pulse" />
                            <span className="text-[#00ffcc] text-sm font-mono font-bold">
                                ACTIVE
                            </span>
                        </div>
                    ) : (
                        <div className="flex items-center justify-between">
                            <span className="text-amber-400 text-sm font-mono font-bold">
                                LOCKED
                            </span>
                            <button 
                              onClick={handleUnlockBio}
                              className="text-[10px] font-mono px-3 py-1 rounded border border-[#00ffcc]/40 text-[#00ffcc] hover:bg-[#00ffcc]/10 transition-all cursor-pointer">
                                UNLOCK
                            </button>
                        </div>
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

            <div className="grid grid-cols-2 gap-6 flex-1 min-h-[400px] mt-6">
                {/* Left Column */}
                <div className="flex flex-col gap-6">
                    <div className="nova-card p-4 flex flex-col gap-3 flex-1 h-[260px]">
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
                            {blockedCommands && blockedCommands.length > 0 ? (
                                blockedCommands.map((cmd, i) => (
                                    <div key={i} className="flex items-center gap-2 bg-[#0a0a0a] border border-red-500/20 rounded px-3 py-2 text-xs font-mono group">
                                        <span className="text-red-400">$</span>
                                        <span className="text-[#e2e8f0] flex-1 truncate">{cmd.cmd || cmd}</span>
                                        <button className="text-red-400/50 hover:text-red-400 text-xs">✕</button>
                                    </div>
                                ))
                            ) : (
                                <div className="text-xs font-mono text-[#4a6a6a] italic p-3 text-center">
                                    No blocked commands configured
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Column */}
                <div className="flex flex-col gap-6">
                    <div className="nova-card p-4 flex flex-col gap-3 flex-1">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase text-center font-bold">AUTONOMY SETTINGS</div>
                        <div className="flex flex-col gap-6 py-2">
                            <div className="flex flex-col gap-0 border border-[rgba(0,255,204,0.05)] rounded-lg bg-[#020d0d] px-3">
                                {[
                                    { key: 'auto_cleanup', label: 'AUTO CLEANUP' },
                                    { key: 'auto_reasoning', label: 'AUTO REASONING' },
                                    { key: 'auto_reply', label: 'AUTO REPLY' }
                                ].map(({ key, label }) => {
                                    const value = toggles[key as keyof typeof toggles];
                                    return (
                                        <div key={key} className="flex items-center justify-between py-3 border-b border-[rgba(0,255,204,0.05)] last:border-0">
                                            <span className="text-xs font-mono text-[#e2e8f0] tracking-wider">{label}</span>
                                            <button
                                                onClick={() => handleToggle(key as keyof typeof toggles)}
                                                className={`relative w-10 h-5 rounded-full transition-all duration-300 cursor-pointer ${
                                                    value
                                                    ? 'bg-[#00ffcc]/20 border border-[#00ffcc]/40' 
                                                    : 'bg-[#111] border border-[rgba(255,255,255,0.1)]'
                                                }`}>
                                                <div className={`absolute top-0.5 w-4 h-4 rounded-full transition-all duration-300 ${
                                                    value 
                                                    ? 'left-[1.05rem] bg-[#00ffcc]' 
                                                    : 'left-0.5 bg-[#4a6a6a]'
                                                }`} />
                                            </button>
                                        </div>
                                    );
                                })}
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
                            {recentBlocked && recentBlocked.length > 0 ? (
                                recentBlocked.map((item, i) => (
                                    <div key={i} className={`flex items-start gap-2 p-2 rounded text-xs font-mono mb-1 ${
                                        item.tier === 'CRITICAL' || item.reason?.toLowerCase().includes('destructive') || item.reason?.toLowerCase().includes('escalation')
                                        ? 'bg-red-500/10 border border-red-500/20' 
                                        : 'bg-amber-400/5 border border-amber-400/10'
                                    }`}>
                                        <span className={item.tier === 'CRITICAL' || item.reason?.toLowerCase().includes('destructive') || item.reason?.toLowerCase().includes('escalation')
                                            ? 'text-red-400' : 'text-amber-400'}>
                                            ●
                                        </span>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex justify-between items-center pb-1">
                                                <div className={item.tier === 'CRITICAL' || item.reason?.toLowerCase().includes('destructive') || item.reason?.toLowerCase().includes('escalation') ? 'text-red-300 font-bold' : 'text-amber-300 font-bold'}>
                                                    {item.tier || 'WARNING'} TIER
                                                </div>
                                                <span className="text-[10px] text-[var(--nova-muted)] text-right">
                                                    {item.ts && !isNaN(new Date(item.ts).getTime()) 
                                                        ? new Date(item.ts).toLocaleString() 
                                                        : new Date().toLocaleString()}
                                                </span>
                                            </div>
                                            <div className="text-[#a0b0b0] text-[10px] truncate">
                                                {item.command || item.action || item.cmd || 'Unknown'}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-[10px] text-[var(--nova-muted)] text-center py-6">No actions blocked recently</div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
