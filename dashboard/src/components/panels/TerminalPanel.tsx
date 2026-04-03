import { useState, useEffect, useRef } from "react";
import { useApi } from "../../hooks/useApi";

interface TerminalLine {
    id: string;
    type: 'command' | 'output' | 'error' | 'system';
    content: string;
    timestamp: Date;
    exitCode?: number;
}

export function TerminalPanel() {
    const { get, post } = useApi();

    // Terminal State
    const [lines, setLines] = useState<TerminalLine[]>([
        {
            id: '1',
            type: 'system',
            content: 'N.O.V.A Terminal Bridge v4.0 — Connected',
            timestamp: new Date()
        },
        {
            id: '2',
            type: 'system',
            content: 'Type commands below. All execution governed by risk engine.',
            timestamp: new Date()
        }
    ]);
    const [input, setInput] = useState('');
    const [history, setHistory] = useState<string[]>([]);
    const [historyIndex, setHistoryIndex] = useState(-1);
    const [isExecuting, setIsExecuting] = useState(false);
    const [pendingRisk, setPendingRisk] = useState<{ command: string, risk: string } | null>(null);
    const outputRef = useRef<HTMLDivElement>(null);

    // Right Column State
    const [pendingApprovals, setPendingApprovals] = useState<any[]>([]);
    const [recentExecutions, setRecentExecutions] = useState<any[]>([]);

    useEffect(() => {
        outputRef.current?.scrollTo({
            top: outputRef.current.scrollHeight,
            behavior: 'smooth'
        });
    }, [lines]);

    // Poll Approvals
    useEffect(() => {
        const fetchApprovals = async () => {
            try {
                const res = await get<any>('/api/approvals').catch(() => []);
                const filtered = (res || []).filter((a: any) => a.source === 'terminal' && a.status === 'pending');
                setPendingApprovals(filtered);
            } catch { /* ignore */ }
        };
        fetchApprovals();
        const iv = setInterval(fetchApprovals, 5000);
        return () => clearInterval(iv);
    }, [get]);

    const executeCommand = async (command: string) => {
        if (!command.trim() || isExecuting) return;

        // Add to history
        setHistory(prev => [command, ...prev.slice(0, 49)]);
        setHistoryIndex(-1);

        // Show command in terminal
        setLines(prev => [...prev, {
            id: Date.now().toString(),
            type: 'command',
            content: command,
            timestamp: new Date()
        }]);

        setInput('');
        setIsExecuting(true);
        setPendingRisk(null);

        try {
            const res = await post<any>('/api/terminal', { command });

            // Handle risk-based response
            if (res.requires_approval || res.risk === 'MEDIUM' || res.risk === 'CRITICAL') {
                setPendingRisk({ command, risk: res.risk });
                setLines(prev => [...prev, {
                    id: (Date.now() + 1).toString(),
                    type: 'system',
                    content: `⚠ ${res.risk} RISK — ${res.message}`,
                    timestamp: new Date()
                }]);
            } else if (res.status === 'executed' || res.status === 'error' || res.status === 'timeout') {
                // Show output
                setLines(prev => [...prev, {
                    id: (Date.now() + 1).toString(),
                    type: res.exit_code === 0 ? 'output' : 'error',
                    content: res.output || (res.status === 'executed' ? '(no output)' : res.message),
                    timestamp: new Date(),
                    exitCode: res.exit_code
                }]);

                setRecentExecutions(prev => [{
                    id: Date.now().toString(),
                    time: new Date(),
                    command,
                    exit_code: res.exit_code
                }, ...prev].slice(0, 10));
            }
        } catch (err: any) {
            setLines(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                type: 'error',
                content: `Connection error: ${err.message || err}`,
                timestamp: new Date()
            }]);
        } finally {
            setIsExecuting(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (pendingRisk) return;
            executeCommand(input);
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            const newIndex = Math.min(historyIndex + 1, history.length - 1);
            if (newIndex >= 0 && newIndex < history.length) {
                setHistoryIndex(newIndex);
                setInput(history[newIndex] || '');
            }
        }
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            const newIndex = Math.max(historyIndex - 1, -1);
            setHistoryIndex(newIndex);
            setInput(newIndex === -1 ? '' : history[newIndex]);
        }
        if (e.key === 'Tab') {
            e.preventDefault();
            // Optional: Simple structural autocomplete logic here
        }
    };

    const handleApprovalAction = async (id: string, action: 'approve' | 'deny') => {
        try {
            await post(`/api/approvals/${id}/${action}`, {});
            setPendingApprovals(prev => prev.filter(a => a.id !== id));
            // Let the user know to re-run
            setLines(prev => [...prev, {
                id: Date.now().toString(),
                type: 'system',
                content: `Approval ${action}d for ticket ${id}. You may re-run the command if approved.`,
                timestamp: new Date()
            }]);
            // Clear pending risk if it matches
            setPendingRisk(null);
        } catch { /* ignore */ }
    };

    const QuickCommandPill = ({ cmd }: { cmd: string }) => (
        <button
            onClick={() => {
                const cmdMap: Record<string, string> = {
                    'check processes': 'ps aux | head -20',
                    'nova status': 'ps aux | grep nova',
                    'system scan': 'df -h && uptime',
                };
                executeCommand(cmdMap[cmd] ?? cmd);
            }}
            className="text-[9px] bg-[var(--nova-surface2)] text-[var(--nova-text)] px-2 py-1 rounded font-mono hover:bg-[var(--nova-accent)] hover:text-black transition-colors cursor-pointer mr-2 mb-2"
        >
            {cmd}
        </button>
    );

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex gap-6">

            {/* LEFT COLUMN — Terminal Interface */}
            <div className="flex flex-col flex-[6] bg-[#050505] border border-[var(--nova-border)] rounded overflow-hidden">
                {/* 1. TERMINAL HEADER */}
                <div className="h-10 bg-[#111111] border-b border-[var(--nova-border)] flex items-center justify-between px-4 text-xs font-mono tracking-widest uppercase">
                    <span className="text-[var(--nova-accent)]">TERMINAL BRIDGE</span>
                    <span className={`text-[10px] ${pendingRisk?.risk === 'CRITICAL' ? 'text-[var(--nova-red)]' :
                            pendingRisk?.risk === 'MEDIUM' ? 'text-[var(--nova-amber)]' :
                                'text-[var(--nova-green)]'
                        }`}>
                        RISK: {pendingRisk?.risk || 'LOW'}
                    </span>
                </div>

                {/* 2. OUTPUT AREA */}
                <div ref={outputRef} className="flex-1 overflow-y-auto p-4 flex flex-col gap-2">
                    {lines.map(line => (
                        <div key={line.id} className="w-full">
                            {line.type === 'command' && (
                                <div className="text-cyan-400 font-mono text-sm leading-relaxed">
                                    $ {line.content}
                                </div>
                            )}
                            {line.type === 'output' && (
                                <div className="text-green-400 font-mono text-sm whitespace-pre-wrap leading-relaxed opacity-90 break-all">
                                    {line.content}
                                </div>
                            )}
                            {line.type === 'error' && (
                                <div className="text-red-400 font-mono text-sm whitespace-pre-wrap leading-relaxed">
                                    {line.content}
                                </div>
                            )}
                            {line.type === 'system' && (
                                <div className="text-[#4a6a6a] font-mono text-xs italic mt-1 mb-2">
                                    {line.content}
                                </div>
                            )}
                        </div>
                    ))}
                    {isExecuting && (
                        <div className="text-cyan-400 font-mono text-sm animate-pulse mt-1">Executing...</div>
                    )}
                </div>

                <div className="flex flex-col">
                    {/* 4. RISK INDICATOR */}
                    {pendingRisk && (
                        <div className={`p-3 text-xs flex justify-between items-center ${pendingRisk.risk === 'CRITICAL' ? 'bg-[var(--nova-red)]/20 border-t border-[var(--nova-red)]/50' :
                                'bg-[var(--nova-amber)]/20 border-t border-[var(--nova-amber)]/50'
                            }`}>
                            <span className={`font-bold uppercase tracking-widest ${pendingRisk.risk === 'CRITICAL' ? 'text-[var(--nova-red)]' : 'text-[var(--nova-amber)]'
                                }`}>
                                {pendingRisk.risk === 'CRITICAL' ? '🔴 HIGH RISK — blocked' : '⚠ MEDIUM RISK — requires approval'}
                            </span>
                            <div className="flex gap-4 uppercase font-bold text-[10px] tracking-widest">
                                {pendingRisk.risk === 'MEDIUM' && (
                                    <button
                                        onClick={() => {
                                            // Simulated bypass or send to approval
                                            setPendingRisk(null);
                                            executeCommand(pendingRisk.command); // Might just trigger approval loop again depending on backend mock
                                        }}
                                        className="text-[var(--nova-amber)] hover:underline cursor-pointer"
                                    >
                                        [EXECUTE ANYWAY]
                                    </button>
                                )}
                                {pendingRisk.risk === 'CRITICAL' && (
                                    <button
                                        className="text-[var(--nova-red)] hover:underline cursor-pointer"
                                    >
                                        [REQUEST APPROVAL]
                                    </button>
                                )}
                                <button onClick={() => setPendingRisk(null)} className="text-[var(--nova-text)] hover:underline cursor-pointer">
                                    [CANCEL]
                                </button>
                            </div>
                        </div>
                    )}

                    {/* 3. INPUT BAR */}
                    <div className="flex items-center px-4 py-3 bg-[#0a0a0a] border-t border-[var(--nova-border)]">
                        <span className="text-cyan-400 mr-2 font-bold select-none text-sm">$</span>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={isExecuting || pendingRisk !== null}
                            className="bg-transparent text-green-400 font-mono text-sm flex-1 outline-none disabled:opacity-50"
                            autoFocus
                            placeholder={pendingRisk ? "awaiting resolution..." : "enter command..."}
                            autoComplete="off"
                            spellCheck="false"
                        />
                    </div>
                </div>
            </div>

            {/* RIGHT COLUMN — Command Queue & Controls */}
            <div className="flex flex-col flex-[4] gap-6">

                {/* 5. QUICK COMMANDS */}
                <div className="nova-card p-4 flex flex-col gap-3">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase font-bold">QUICK COMMANDS</div>
                    <div className="flex flex-col gap-3 mt-1">
                        <div>
                            <span className="text-[9px] text-[var(--nova-muted)] uppercase tracking-widest block mb-2">SYSTEM:</span>
                            <div className="flex flex-wrap">
                                <QuickCommandPill cmd="ps aux" />
                                <QuickCommandPill cmd="df -h" />
                                <QuickCommandPill cmd="du -sh ~" />
                                <QuickCommandPill cmd="uname -a" />
                            </div>
                        </div>
                        <div>
                            <span className="text-[9px] text-[var(--nova-muted)] uppercase tracking-widest block mb-2">GIT:</span>
                            <div className="flex flex-wrap">
                                <QuickCommandPill cmd="git status" />
                                <QuickCommandPill cmd="git log --oneline -5" />
                                <QuickCommandPill cmd="git branch" />
                            </div>
                        </div>
                        <div>
                            <span className="text-[9px] text-[var(--nova-muted)] uppercase tracking-widest block mb-2">PYTHON:</span>
                            <div className="flex flex-wrap">
                                <QuickCommandPill cmd="pip list" />
                                <QuickCommandPill cmd="python --version" />
                            </div>
                        </div>
                        <div>
                            <span className="text-[9px] text-[var(--nova-muted)] uppercase tracking-widest block mb-2">NOVA:</span>
                            <div className="flex flex-wrap">
                                <QuickCommandPill cmd="nova status" />
                                <QuickCommandPill cmd="check processes" />
                                <QuickCommandPill cmd="system scan" />
                            </div>
                        </div>
                    </div>
                </div>

                {/* 6. COMMAND QUEUE */}
                <div className="nova-card p-4 flex flex-col gap-3 flex-1 min-h-[200px]">
                    <div className="text-[10px] text-[var(--nova-amber)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase font-bold">PENDING APPROVAL</div>
                    <div className="flex-1 overflow-y-auto flex flex-col gap-3">
                        {pendingApprovals.map(a => (
                            <div key={a.id} className="border border-[var(--nova-amber)]/20 bg-[var(--nova-amber)]/5 p-3 rounded flex flex-col gap-2">
                                <div className="flex justify-between items-start font-mono text-xs">
                                    <span className="text-[var(--nova-text)] truncate pr-4">{a.payload?.command || "Unknown command"}</span>
                                    <span className="text-[9px] text-[var(--nova-amber)] tracking-widest font-bold shrink-0">[{a.payload?.risk || 'MEDIUM'}]</span>
                                </div>
                                <span className="text-[9px] text-[var(--nova-muted)]">Requested: {new Date(a.timestamp).toLocaleTimeString()}</span>
                                <div className="flex gap-4 mt-1 font-bold tracking-widest uppercase text-[10px]">
                                    <button onClick={() => handleApprovalAction(a.id, 'approve')} className="text-[var(--nova-green)] hover:underline cursor-pointer">[APPROVE]</button>
                                    <button onClick={() => handleApprovalAction(a.id, 'deny')} className="text-[var(--nova-red)] hover:underline cursor-pointer">[DENY]</button>
                                </div>
                            </div>
                        ))}
                        {pendingApprovals.length === 0 && (
                            <div className="text-[10px] text-[var(--nova-muted)] text-center py-8">No pending terminal approvals</div>
                        )}
                    </div>
                </div>

                {/* 7. EXECUTION HISTORY */}
                <div className="nova-card p-4 flex flex-col gap-3 flex-1 min-h-[200px]">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase font-bold">RECENT EXECUTIONS</div>
                    <div className="flex-1 overflow-y-auto flex flex-col gap-1 pr-2">
                        {recentExecutions.map(e => (
                            <div
                                key={e.id}
                                onClick={() => setInput(e.command)}
                                className="flex justify-between items-center text-[10px] font-mono p-1.5 hover:bg-[var(--nova-surface2)] rounded cursor-pointer group"
                            >
                                <div className="flex items-center gap-3 truncate">
                                    <span className="text-[var(--nova-muted)] shrink-0">{e.time.toLocaleTimeString()}</span>
                                    <span className="text-cyan-400 shrink-0">$</span>
                                    <span className="text-[var(--nova-text)] truncate group-hover:text-white transition-colors">{e.command}</span>
                                </div>
                                <span className={`shrink-0 flex items-center justify-center w-4 h-4 rounded-full font-bold pt-0.5 ml-2 ${e.exit_code === 0 ? 'bg-[var(--nova-green)]/20 text-[var(--nova-green)]' : 'bg-[var(--nova-red)]/20 text-[var(--nova-red)]'
                                    }`}>
                                    {e.exit_code === 0 ? '✓' : '✗'}
                                </span>
                            </div>
                        ))}
                        {recentExecutions.length === 0 && (
                            <div className="text-[10px] text-[var(--nova-muted)] text-center py-8">No recent executions</div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
}
