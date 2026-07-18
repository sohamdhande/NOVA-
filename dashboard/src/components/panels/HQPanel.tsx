import { useState, useEffect, useRef, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";
import { useEventBus } from "../../hooks/useEventBus";
import { ChatMessage, type NovaMessage } from "../chat/ChatMessage";
import { FileAutocomplete } from '../chat/FileAutocomplete';
import { CommandSuggestions } from '../chat/CommandSuggestions';
import { AdvisoryBanner } from '../chat/AdvisoryBanner';

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
    const [inputValue, setInputValue] = useState("");
    const [messages, setMessages] = useState<NovaMessage[]>([]);
    const [isThinking, setIsThinking] = useState(false);
    const [showAutocomplete, setShowAutocomplete] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [lastVoiceCommand, setLastVoiceCommand] = useState("");
    const { lastEvent } = useEventBus();
    const [resourceStats, setResourceStats] = useState<any>(null);
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

    useEffect(() => {
        if (lastEvent?.type === "resource_stats") {
            setResourceStats(lastEvent.payload);
        }
    }, [lastEvent]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setInputValue(val);
        setShowAutocomplete(val.includes('~/') || val.startsWith('/'));
    };

    const handlePathSelect = (path: string) => {
        const parts = inputValue.split(' ');
        parts[parts.length - 1] = path;
        setInputValue(parts.join(' '));
        setShowAutocomplete(false);
    };

    const sendMessageText = async (text: string) => {
        if (!text.trim() || isThinking) return;

        setIsThinking(true);
        setTimeout(() => chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight), 50);

        try {
            const data = await post<any>("/api/chat", { message: text });

            const novaMsg: NovaMessage = {
                id: (Date.now() + 1).toString(),
                role: 'nova',
                content: data.message,
                block_type: data.block_type,
                data: data.data,
                requires_approval: data.requires_approval,
                risk: data.risk,
                success: data.success,
                timestamp: new Date()
            };

            setMessages(prev => [...prev, novaMsg]);

            if (data.block_type === 'navigation' && data.data?.navigate_to) {
                setActivePanel(data.data.navigate_to);
            }
        } catch {
            const errorMsg: NovaMessage = {
                id: (Date.now() + 1).toString(),
                role: 'nova',
                content: "Error: failed to reach N.O.V.A",
                block_type: "error",
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsThinking(false);
            setTimeout(() => chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight), 50);
        }
    };

    const handleSend = async () => {
        if (!inputValue.trim() || isThinking) return;

        const text = inputValue;
        const userMsg: NovaMessage = {
            id: Date.now().toString(),
            role: "user",
            content: text,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMsg]);
        setInputValue("");

        await sendMessageText(text);
    };

    useEffect(() => {
        const checkVoice = async () => {
            try {
                const res: any = await get('/api/voice/status');
                const cmds = res.recent_commands || [];

                const latest = cmds[cmds.length - 1];
                if (latest && latest.type === 'command' &&
                    latest.text !== lastVoiceCommand) {
                    setLastVoiceCommand(latest.text);

                    const voiceMsg: NovaMessage = {
                        id: Date.now().toString(),
                        role: 'user',
                        content: `🎤 ${latest.text}`,
                        timestamp: new Date()
                    };
                    setMessages(prev => [...prev, voiceMsg]);

                    await sendMessageText(latest.text);
                }
            } catch { /* ignore */ }
        };
        const iv = setInterval(checkVoice, 3000);
        return () => clearInterval(iv);
    }, [lastVoiceCommand, get, isThinking]);

    const handleApprove = (id: string) => {
        setMessages(prev => prev.map(m =>
            m.id === id
                ? { ...m, block_type: 'mission', content: 'Action approved. Executing...' }
                : m
        ));
    };

    const handleDeny = (id: string) => {
        setMessages(prev => prev.map(m =>
            m.id === id
                ? { ...m, block_type: 'error', content: 'Action denied by user.' }
                : m
        ));
    };

    const handleCleanupApprove = async (
        messageId: string, 
        action: string
    ) => {
        if (action === 'ai_cleanup_execute') {
            // Update message to show executing
            setMessages(prev => prev.map(m => 
                m.id === messageId 
                    ? {...m, data: {
                        ...m.data, 
                        executed: true
                      }} 
                    : m
            ));
            // Send execute command
            try {
                const data = await post<any>(
                    '/api/chat', 
                    { message: 'yes execute cleanup' }
                );
                // Add result message
                const resultMsg: NovaMessage = {
                    id: (Date.now()+1).toString(),
                    role: 'nova' as const,
                    content: data.message,
                    block_type: 'text',
                    data: {},
                    requires_approval: false,
                    success: true,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, resultMsg]);
            } catch (err: any) {
                const errorMsg: NovaMessage = {
                    id: (Date.now()+1).toString(),
                    role: 'nova' as const,
                    content: "Error: " + (err.message || "Failed to execute cleanup."),
                    block_type: 'error',
                    data: {},
                    requires_approval: false,
                    success: false,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, errorMsg]);
            }
        }
    };

    const handleCleanupDeny = (messageId: string) => {
        setMessages(prev => prev.map(m =>
            m.id === messageId
                ? {...m, data: {
                    ...m.data,
                    executed: true
                  }}
                : m
        ));
        const cancelMsg: NovaMessage = {
            id: (Date.now()+1).toString(),
            role: 'nova' as const,
            content: 'Cleanup cancelled.',
            block_type: 'text',
            data: {},
            requires_approval: false,
            success: true,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, cancelMsg]);
    };

    /* ─── Health ring ─── */
    const healthScore = health?.score ?? 0;
    const healthZone = (health?.zone ?? "CONTROLLED").toUpperCase();

    const stats = {
      activeTasks: (status as any)?.active_tasks ?? 3,
      overdue: (status as any)?.overdue ?? 0,
      upcoming: (status as any)?.deadlines ?? 1,
      spend: (status as any)?.today_spend ?? 0
    };

    const SectionCard = ({ title, children, accent = false }: any) => (
      <div className={`group relative overflow-hidden rounded-xl border p-5
        bg-black/40 backdrop-blur-md mb-4
        transition-all duration-500 hover:shadow-[0_8px_30px_rgba(0,255,204,0.08)]
        ${accent 
          ? 'border-[rgba(0,255,204,0.4)] shadow-[0_0_15px_rgba(0,255,204,0.1)]' 
          : 'border-[rgba(0,255,204,0.15)] hover:border-[rgba(0,255,204,0.3)]'
        }`}>
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[rgba(0,255,204,0.3)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="absolute -inset-1 bg-gradient-to-br from-[#00ffcc]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        <div className="flex items-center gap-3 mb-5 relative z-10">
          <div className="w-1 h-5 bg-gradient-to-b from-[#00ffcc] to-[#0088aa] rounded-full shadow-[0_0_10px_rgba(0,255,204,0.5)]" />
          <span className="text-[11px] font-mono tracking-[0.4em] text-transparent bg-clip-text bg-gradient-to-r from-[#e2e8f0] to-[#4a6a6a] font-bold uppercase">
            {title}
          </span>
        </div>
        <div className="relative z-10">
          {children}
        </div>
      </div>
    );

    const advisories = (health?.advisories as string[]) || [];
    const briefingItems = briefing?.briefing || [];

    if (loading) return <div className="p-6 grid grid-cols-2 gap-4">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)}</div>;
    if (error) return <div className="p-6"><ErrorCard msg={error} onRetry={fetchAll} /></div>;

    return (
        <div className="p-8 h-full overflow-y-auto relative bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[rgba(0,255,204,0.03)] via-transparent to-transparent">
            {/* Header */}
            <div className="flex items-center justify-between mb-8 pb-4 border-b border-[rgba(0,255,204,0.1)] relative">
                <div className="absolute bottom-0 left-0 w-1/3 h-[1px] bg-gradient-to-r from-[#00ffcc]/50 to-transparent" />
                <h1 className="text-base font-bold font-mono tracking-[0.4em] uppercase text-transparent bg-clip-text bg-gradient-to-r from-[#00ffcc] to-teal-200 drop-shadow-[0_0_8px_rgba(0,255,204,0.5)]">COMMAND CENTER</h1>
                <div className="flex items-center gap-4 bg-black/30 px-4 py-2 rounded-full border border-[rgba(0,255,204,0.15)] shadow-[inset_0_0_15px_rgba(0,0,0,0.5)]">
                    <span className="w-2 h-2 rounded-full bg-[#00ffcc] animate-pulse shadow-[0_0_8px_#00ffcc]"></span>
                    <span className="text-[10px] font-mono text-[#8a9a9a] uppercase tracking-widest">SYS.UPDATED: <span className="text-[#e2e8f0] font-bold">{lastUpdated.toLocaleTimeString()}</span></span>
                    <button onClick={fetchAll} className="text-[#00ffcc] hover:text-white transition-colors text-sm cursor-pointer ml-2 hover:rotate-180 duration-500 ease-in-out">⟳</button>
                </div>
            </div>

            {resourceStats && (
                <div className="flex justify-between items-center bg-[#010a0a]/80 backdrop-blur-md border border-[rgba(0,255,204,0.15)] rounded-lg px-4 py-2 mb-6 shadow-[0_4px_15px_rgba(0,0,0,0.4)]">
                    <div className="flex gap-6">
                        <div className="flex flex-col">
                            <span className="text-[9px] font-mono tracking-widest text-[#8a9a9a]">NOVA CPU</span>
                            <span className={`text-xs font-mono font-bold ${resourceStats.cpu_percent > 40 ? 'text-red-400' : 'text-[#00ffcc]'}`}>{resourceStats.cpu_percent}%</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[9px] font-mono tracking-widest text-[#8a9a9a]">NOVA RAM</span>
                            <span className={`text-xs font-mono font-bold ${resourceStats.memory_mb > 500 ? 'text-amber-400' : 'text-[#e2e8f0]'}`}>{resourceStats.memory_mb} MB</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[9px] font-mono tracking-widest text-[#8a9a9a]">SYS FREE</span>
                            <span className={`text-xs font-mono font-bold ${resourceStats.system_memory_free_gb < 1 ? 'text-red-400' : 'text-[#e2e8f0]'}`}>{resourceStats.system_memory_free_gb} GB</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc] animate-pulse"></span>
                        <span className="text-[9px] font-mono tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-[#00ffcc] to-teal-200">MONITOR ACTIVE</span>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-5 gap-8 h-full">
                {/* LEFT COLUMN */}
                <div className="col-span-3 flex flex-col gap-2">
                    {/* Premium Health Ring */}
                    <div className="relative flex items-center justify-center w-64 h-64 mx-auto mt-4 group">
                      {/* Outer intense glow that pulses */}
                      <div className={`absolute inset-0 rounded-full blur-[40px] opacity-20 group-hover:opacity-40 transition-all duration-1000 animate-pulse
                        ${healthScore >= 80 
                          ? 'bg-[#00ffcc]' 
                          : healthScore >= 60
                          ? 'bg-amber-400'
                          : 'bg-red-500'
                        }`} />
                      
                      {/* Outer dashed rotating ring - highly detailed */}
                      <svg className="absolute w-[115%] h-[115%] animate-[spin_60s_linear_infinite] opacity-60 group-hover:opacity-100 transition-opacity duration-1000" viewBox="0 0 140 140">
                         <circle cx="70" cy="70" r="68" fill="none" stroke="url(#ringGrad1)" strokeWidth="0.5" strokeDasharray="2 6" />
                      </svg>

                      {/* Inner counter-rotating ring */}
                      <svg className="absolute w-[105%] h-[105%] animate-[spin_30s_linear_infinite_reverse] opacity-40 group-hover:opacity-80 transition-opacity duration-1000" viewBox="0 0 140 140">
                         <circle cx="70" cy="70" r="64" fill="none" stroke="url(#ringGrad2)" strokeWidth="1.5" strokeDasharray="15 30" strokeLinecap="round" />
                      </svg>

                      {/* Main SVG Ring with rich gradients */}
                      <svg className="absolute w-full h-full -rotate-90 drop-shadow-[0_0_15px_rgba(0,255,204,0.3)] transition-all duration-1000" viewBox="0 0 120 120">
                        <defs>
                          <linearGradient id="ringGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor={healthScore >= 80 ? '#00ffcc' : healthScore >= 60 ? '#fbbf24' : '#ef4444'} stopOpacity="0.8" />
                            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                          </linearGradient>
                          <linearGradient id="ringGrad2" x1="100%" y1="100%" x2="0%" y2="0%">
                            <stop offset="0%" stopColor={healthScore >= 80 ? '#0088aa' : healthScore >= 60 ? '#b45309' : '#991b1b'} stopOpacity="0.8" />
                            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                          </linearGradient>
                          <linearGradient id="mainArc" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor={healthScore >= 80 ? '#00ffcc' : healthScore >= 60 ? '#fbbf24' : '#ef4444'} />
                            <stop offset="100%" stopColor={healthScore >= 80 ? '#0088aa' : healthScore >= 60 ? '#b45309' : '#7f1d1d'} />
                          </linearGradient>
                        </defs>
                        {/* Background track with glass effect */}
                        <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="8" />
                        <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(0,0,0,0.5)" strokeWidth="8" strokeDasharray="4 8" />
                        
                        {/* Progress arc */}
                        <circle cx="60" cy="60" r="52" fill="none"
                          stroke="url(#mainArc)"
                          strokeWidth="8" strokeLinecap="round" strokeDasharray={`${2 * Math.PI * 52}`}
                          strokeDashoffset={`${(2 * Math.PI * 52) - (healthScore / 100) * (2 * Math.PI * 52)}`}
                          className="transition-all duration-1000 ease-out"
                        />
                      </svg>
                      
                      {/* Premium Center Orb */}
                      <div className={`relative flex flex-col items-center justify-center w-44 h-44 rounded-full backdrop-blur-2xl z-10 transition-all duration-1000
                        bg-gradient-to-br from-black/80 to-[#010a0a]/60 border border-white/5 shadow-[inset_0_0_40px_rgba(0,0,0,0.9)]
                        group-hover:shadow-[inset_0_0_50px_${healthScore >= 80 ? 'rgba(0,255,204,0.15)' : healthScore >= 60 ? 'rgba(251,191,36,0.15)' : 'rgba(239,68,68,0.15)'}]`}>
                        <div className="absolute inset-0 rounded-full bg-gradient-to-t from-transparent to-white/5 pointer-events-none" />
                        <div className={`absolute -inset-2 rounded-full opacity-0 group-hover:opacity-10 transition-opacity duration-1000 bg-gradient-to-b 
                          ${healthScore >= 80 ? 'from-[#00ffcc]' : healthScore >= 60 ? 'from-amber-400' : 'from-red-500'} to-transparent blur-md pointer-events-none`} />
                        
                        <span className={`relative z-10 text-7xl font-black font-mono tracking-tighter drop-shadow-2xl transition-all duration-1000
                          ${healthScore >= 80 ? 'text-transparent bg-clip-text bg-gradient-to-b from-white via-[#e2e8f0] to-[#00ffcc]' : healthScore >= 60 ? 'text-transparent bg-clip-text bg-gradient-to-b from-white via-[#e2e8f0] to-amber-400' : 'text-transparent bg-clip-text bg-gradient-to-b from-white via-[#e2e8f0] to-red-500'}`}>
                          {healthScore}
                        </span>
                        <span className={`relative z-10 text-[10px] font-mono tracking-[0.5em] mt-3 font-bold uppercase transition-all duration-1000
                          ${healthScore >= 80 ? 'text-[#00ffcc]/80 drop-shadow-[0_0_5px_rgba(0,255,204,0.5)]' : healthScore >= 60 ? 'text-amber-400/80 drop-shadow-[0_0_5px_rgba(251,191,36,0.5)]' : 'text-red-500/80 drop-shadow-[0_0_5px_rgba(239,68,68,0.5)]'}`}>
                          {healthZone}
                        </span>
                      </div>
                    </div>

                    {/* Quick Stats Row */}
                    <div className="grid grid-cols-2 gap-4 mt-6">
                      {[
                        { label: "ACTIVE TASKS", value: stats.activeTasks, icon: "⚡", color: "cyan" },
                        { label: "OVERDUE ISSUES", value: stats.overdue, icon: "⚠", color: stats.overdue > 0 ? "red" : "cyan" },
                        { label: "48H DEADLINES", value: stats.upcoming, icon: "⏱", color: stats.upcoming > 0 ? "amber" : "cyan" },
                        { label: "TODAY'S SPEND", value: `${stats.spend}`, icon: "💰", color: "cyan" }
                      ].map(card => (
                        <div key={card.label}
                          className={`relative overflow-hidden rounded-xl border p-5 bg-black/40 backdrop-blur-xl
                            ${card.color === 'red' ? 'border-red-500/40 shadow-[0_4px_20px_rgba(239,68,68,0.1)]' : card.color === 'amber' ? 'border-amber-400/40 shadow-[0_4px_20px_rgba(251,191,36,0.1)]' : 'border-[rgba(0,255,204,0.15)] shadow-[0_4px_20px_rgba(0,0,0,0.3)]'}
                            hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(0,255,204,0.15)] transition-all duration-300 group cursor-default`}
                        >
                          {/* Background radial glow */}
                          <div className={`absolute -inset-1 opacity-0 blur-2xl group-hover:opacity-20 transition-opacity duration-500
                            ${card.color === 'red' ? 'bg-red-500' : card.color === 'amber' ? 'bg-amber-400' : 'bg-[#00ffcc]'}`} />
                          
                          <div className="relative z-10 flex flex-col h-full justify-between">
                            <div className="flex items-center justify-between mb-4">
                              <span className="text-[10px] font-mono tracking-[0.2em] font-semibold text-[#8a9a9a] group-hover:text-white transition-colors duration-300">
                                {card.label}
                              </span>
                              <span className={`text-sm opacity-90 bg-black/50 p-2 rounded-lg border border-white/5 shadow-inner
                                ${card.color === 'red' ? 'text-red-400 border-red-500/20' : card.color === 'amber' ? 'text-amber-400 border-amber-400/20' : 'text-[#00ffcc] border-[#00ffcc]/20'}`}>
                                {card.icon}
                              </span>
                            </div>
                            <div className={`text-3xl font-black font-mono tracking-tight drop-shadow-lg
                              ${card.color === 'red' ? 'text-red-400' : card.color === 'amber' ? 'text-amber-400' : 'text-white group-hover:text-[#00ffcc] transition-colors duration-300'}`}>
                              {card.value}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Quick Command Bar & Chat */}
                    <div className="mt-4">
                        <AdvisoryBanner onActionClick={(cmd) => { setInputValue(cmd); setTimeout(handleSend, 50); }} />
                    </div>
                    
                    <div className="flex flex-col relative overflow-hidden rounded-xl border border-[rgba(0,255,204,0.15)] bg-black/30 backdrop-blur-2xl shadow-[0_15px_40px_rgba(0,0,0,0.6)] mt-2" style={{ height: '380px' }}>
                        {/* subtle animated top border */}
                        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#00ffcc]/60 to-transparent opacity-50" />
                        
                        {/* Scrollable message area */}
                        <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ minHeight: 0 }} ref={chatBoxRef}>
                            <CommandSuggestions
                                visible={messages.length === 0 && !isThinking && inputValue === ''}
                                onSelect={(cmd) => { setInputValue(cmd); setTimeout(handleSend, 50); }}
                            />
                            {messages.map(msg => (
                                <ChatMessage
                                    key={msg.id}
                                    message={msg}
                                    onApprove={(id, action) => {
                                        if (action === 'ai_cleanup_execute' && id) {
                                            handleCleanupApprove(id, action);
                                        } else {
                                            handleApprove(msg.id);
                                        }
                                    }}
                                    onDeny={(id) => {
                                        if (msg.block_type === 'cleanup_approval' && id) {
                                            handleCleanupDeny(id);
                                        } else {
                                            handleDeny(msg.id);
                                        }
                                    }}
                                />
                            ))}
                            {isThinking && (
                                <div className="flex justify-start">
                                    <div className="px-4 py-3 rounded-lg border border-[rgba(0,255,204,0.2)] bg-[#020a0a] shadow-lg flex items-center gap-3">
                                        <div className="w-1.5 h-1.5 bg-[#00ffcc] rounded-full animate-ping" />
                                        <span className="text-[#00ffcc] text-xs font-mono font-bold uppercase tracking-widest">N.O.V.A processing</span>
                                        <span className="flex gap-0.5 ml-1">
                                            <span className="w-1 h-1 bg-[#00ffcc] rounded-full animate-bounce" style={{animationDelay: "0ms"}}/>
                                            <span className="w-1 h-1 bg-[#00ffcc] rounded-full animate-bounce" style={{animationDelay: "150ms"}}/>
                                            <span className="w-1 h-1 bg-[#00ffcc] rounded-full animate-bounce" style={{animationDelay: "300ms"}}/>
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Fixed input bar at bottom */}
                        <div className="relative mt-auto bg-[#010808]/80 backdrop-blur-xl border-t border-[rgba(0,255,204,0.1)] p-4 shadow-[0_-10px_30px_rgba(0,0,0,0.3)]">
                          <FileAutocomplete
                              query={inputValue}
                              onSelect={handlePathSelect}
                              visible={showAutocomplete}
                          />
                          <div className="flex items-center gap-3 
                            bg-black/60 border border-[rgba(0,255,204,0.15)]
                            rounded-xl px-4 py-3
                            focus-within:border-[rgba(0,255,204,0.6)]
                            focus-within:shadow-[0_0_20px_rgba(0,255,204,0.15)]
                            focus-within:bg-[#020d0d]
                            transition-all duration-300 group">
                            <span className="text-[#00ffcc] text-xs font-mono opacity-50 group-focus-within:animate-pulse group-focus-within:opacity-100">▶</span>
                            <input
                              value={inputValue}
                              onChange={handleInputChange}
                              onKeyDown={e => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                  e.preventDefault();
                                  handleSend();
                                }
                              }}
                              placeholder="Issue directive to N.O.V.A..."
                              disabled={isThinking}
                              className="flex-1 bg-transparent text-sm font-mono text-[#e2e8f0] outline-none placeholder-[#4a6a6a] disabled:opacity-50"
                            />
                            {isThinking ? (
                              <div className="w-5 h-5 border-2 border-[rgba(0,255,204,0.2)] border-t-[#00ffcc] rounded-full animate-spin flex-shrink-0" />
                            ) : (
                              <button onClick={handleSend} disabled={!inputValue.trim()}
                                className="text-black bg-[#00ffcc] opacity-70 hover:opacity-100 transition-all font-bold text-sm px-3 py-1 rounded shadow-[0_0_10px_rgba(0,255,204,0.3)] hover:shadow-[0_0_15px_rgba(0,255,204,0.6)] disabled:opacity-20 disabled:shadow-none font-mono tracking-widest">
                                EXECUTE
                              </button>
                            )}
                          </div>
                          
                          {/* Slash command hint */}
                          <div className="flex gap-2 mt-3 flex-wrap">
                            {['/briefing', '/focus', '/clean', '/analyze', '/sec'].map(cmd => (
                              <button key={cmd}
                                onClick={() => { setInputValue(cmd); setTimeout(handleSend, 50); }}
                                className="text-[10px] font-mono px-3 py-1 rounded-md border border-[rgba(0,255,204,0.1)] bg-white/5 text-[#8a9a9a] hover:text-[#00ffcc] hover:bg-[#00ffcc]/10 hover:border-[#00ffcc]/40 hover:shadow-[0_0_10px_rgba(0,255,204,0.15)] transition-all duration-300">
                                {cmd}
                              </button>
                            ))}
                          </div>
                        </div>
                    </div>
                </div>

                {/* RIGHT COLUMN */}
                <div className="col-span-2 flex flex-col gap-5 overflow-y-auto w-full pt-1">
                    {/* Morning Briefing */}
                    <SectionCard title="Morning Briefing">
                      {briefingItems.length > 0 ? (
                        <div className="space-y-3">
                          {briefingItems.map((item: any, i: number) => (
                            <div key={i} className={`group/item flex gap-3 text-sm flex-col p-4 rounded-lg bg-black/40 border
                              transition-all duration-300 hover:shadow-lg
                              ${item.severity === 'high' || item.severity === 'critical'
                                ? 'border-red-500/20 hover:border-red-500/40 hover:bg-red-500/5'
                                : item.severity === 'medium' || item.severity === 'warning'
                                ? 'border-amber-400/20 hover:border-amber-400/40 hover:bg-amber-400/5'
                                : 'border-[#00ffcc]/15 hover:border-[#00ffcc]/30 hover:bg-[#00ffcc]/5'
                              }`}>
                              <span className={`text-[10px] font-mono tracking-widest font-bold uppercase
                                ${item.severity === 'high' || item.severity === 'critical' ? 'text-red-400' 
                                : item.severity === 'medium' || item.severity === 'warning' ? 'text-amber-400' : 'text-[#00ffcc]'}`
                              }>
                                {(item.severity || 'INFO')}
                              </span>
                              <span className="text-[#e2e8f0] font-mono leading-relaxed opacity-90 group-hover/item:opacity-100 transition-opacity">
                                {item.message}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center p-6 bg-black/20 rounded-lg border border-dashed border-white/10">
                          <span className="text-[#4a6a6a] font-mono text-xs italic tracking-widest mt-2">NO BRIEFING LOADED</span>
                        </div>
                      )}
                    </SectionCard>

                    {/* Pending Approvals */}
                    <SectionCard title="Pending Approvals">
                      {approvals.length === 0 ? (
                        <div className="flex items-center gap-3 text-xs font-mono text-[#00ffcc] bg-[#00ffcc]/5 border border-[#00ffcc]/20 p-4 rounded-lg shadow-[inset_0_0_15px_rgba(0,255,204,0.05)]">
                          <div className="w-6 h-6 rounded-full bg-[#00ffcc]/20 flex items-center justify-center border border-[#00ffcc]/50">
                            <span className="text-lg leading-none -mt-[2px]">✓</span>
                          </div>
                          <span className="font-bold tracking-wider">ALL SYSTEMS CLEAR</span>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {approvals.map((a: any) => (
                            <div key={a.id} className="border border-amber-400/30 rounded-lg p-3 bg-gradient-to-r from-amber-400/10 to-transparent shadow-[0_4px_15px_rgba(251,191,36,0.05)] group/app hover:border-amber-400/50 transition-colors">
                              <div className="text-xs font-mono text-amber-300 mb-3 font-semibold tracking-wide flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                                {a.command || a.action}
                              </div>
                              <div className="flex gap-3">
                                <button onClick={() => { handleApprove(a.id); setActivePanel('approvals'); }} className="flex-1 text-[11px] font-mono font-bold tracking-widest px-3 py-2 rounded border border-[#00ffcc]/40 text-[#00ffcc] bg-black/50 hover:bg-[#00ffcc]/20 hover:text-white hover:shadow-[0_0_15px_rgba(0,255,204,0.3)] transition-all duration-300">
                                  AUTHORIZE
                                </button>
                                <button onClick={() => { handleDeny(a.id); setActivePanel('approvals'); }} className="flex-1 text-[11px] font-mono font-bold tracking-widest px-3 py-2 rounded border border-red-500/40 text-red-500 bg-black/50 hover:bg-red-500/20 hover:text-white hover:shadow-[0_0_15px_rgba(239,68,68,0.3)] transition-all duration-300">
                                  DENY
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </SectionCard>

                    {/* Intelligence Brief */}
                    <SectionCard title="Active Protocol Advisories">
                      {advisories.length === 0 ? (
                        <div className="flex items-center gap-3 text-xs font-mono text-[#00ffcc] opacity-70 p-2">
                          <span className="w-2 h-2 rounded-full bg-[#00ffcc] animate-ping" />
                          <span className="tracking-widest">NOMINAL</span>
                        </div>
                      ) : (
                        <div className="flex flex-col gap-1">
                          {advisories.map((adv: string, i: number) => (
                            <div key={i} className="flex gap-3 text-xs font-mono p-3 hover:bg-white/5 rounded-lg transition-colors items-start">
                              <div className="mt-[2px] w-4 h-4 rounded border border-amber-400/50 flex items-center justify-center flex-shrink-0 bg-amber-400/10 shadow-[0_0_10px_rgba(251,191,36,0.2)]">
                                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                              </div>
                              <span className="text-[#e2e8f0] leading-relaxed">
                                {adv}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </SectionCard>
                </div>
            </div>
        </div>
    );
}
