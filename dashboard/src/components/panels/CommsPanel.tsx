import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function CommsPanel() {
    const { get, post } = useApi();
    const [activeTab, setActiveTab] = useState<'EMAILS' | 'SLACK' | 'WHATSAPP'>('EMAILS');
    const [data, setData] = useState<any>({ emails: [], slack: [], whatsapp: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    // Compose state
    const [composeTo, setComposeTo] = useState("");
    const [composeMsg, setComposeMsg] = useState("");
    const [composePlatform, setComposePlatform] = useState<'EMAIL' | 'SLACK'>('EMAIL');

    const fetchComms = useCallback(async () => {
        try {
            const res = await get<any>("/api/comms").catch(() => ({ emails: [], slack: [], whatsapp: [] }));
            setData(res);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch comms");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchComms();
        const iv = setInterval(fetchComms, 30000);
        return () => clearInterval(iv);
    }, [fetchComms]);

    const handleSendDraft = async (id: string, platform: string, text: string) => {
        try {
            // Note: Actual route might differ based on backend implementation
            await post(`/api/comms/${id}/approve`, { draft: text, platform });
            fetchComms();
        } catch (e) {
            console.error("Failed to send draft", e);
        }
    };

    const handleCompose = async () => {
        if (!composeTo.trim() || !composeMsg.trim()) return;
        try {
            await post('/api/comms/send', { to: composeTo, message: composeMsg, platform: composePlatform });
            setComposeTo("");
            setComposeMsg("");
        } catch (e) {
            console.error("Compose failed", e);
        }
    };

    const dismissMessage = (id: string, platform: 'emails' | 'slack' | 'whatsapp') => {
        setData((prev: any) => ({
            ...prev,
            [platform]: (prev[platform] || []).filter((x: any) => x.id !== id)
        }));
    };

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    const listToRender = activeTab === 'EMAILS' ? data.emails : activeTab === 'SLACK' ? data.slack : data.whatsapp;

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">COMMUNICATIONS HUB</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchComms} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            {/* TAB BAR */}
            <div className="flex gap-6 border-b border-[var(--nova-border)] text-xs font-bold tracking-widest">
                {['EMAILS', 'SLACK', 'WHATSAPP'].map(t => (
                    <button
                        key={t}
                        onClick={() => setActiveTab(t as any)}
                        className={`pb-2 transition-colors cursor-pointer ${activeTab === t ? 'text-[var(--nova-accent)] border-b-2 border-[var(--nova-accent)]' : 'text-[var(--nova-muted)] hover:text-[#fff]'}`}
                    >
                        {t}
                    </button>
                ))}
            </div>

            <div className="flex-1 flex flex-col gap-4 overflow-y-auto">
                {(!listToRender || listToRender.length === 0) ? (
                    <div className="flex-1 flex items-center justify-center text-[var(--nova-muted)] text-xs">
                        No {activeTab} messages detected
                    </div>
                ) : (
                    listToRender.map((item: any, i: number) => (
                        <CommCard
                            key={item.id || i}
                            item={item}
                            platform={activeTab.toLowerCase() as any}
                            onSend={handleSendDraft}
                            onDismiss={dismissMessage}
                        />
                    ))
                )}
            </div>

            {/* COMPOSE SECTION */}
            <div className="nova-card p-4 flex flex-col gap-3 mt-4 shrink-0">
                <div className="text-[10px] tracking-widest text-[var(--nova-muted)] uppercase">QUICK COMPOSE</div>
                <div className="flex gap-2">
                    <select
                        value={composePlatform}
                        onChange={e => setComposePlatform(e.target.value as any)}
                        className="bg-black/50 border border-[var(--nova-border)] rounded px-2 py-1 text-xs text-[var(--nova-accent)] outline-none"
                    >
                        <option value="EMAIL">EMAIL</option>
                        <option value="SLACK">SLACK</option>
                    </select>
                    <input
                        placeholder="To (email or @user)..."
                        value={composeTo}
                        onChange={e => setComposeTo(e.target.value)}
                        className="flex-1 bg-black/50 border border-[var(--nova-border)] rounded px-2 py-1 text-xs outline-none focus:border-[var(--nova-accent)] transition-colors"
                    />
                </div>
                <textarea
                    placeholder="Message..."
                    value={composeMsg}
                    onChange={e => setComposeMsg(e.target.value)}
                    className="bg-black/50 border border-[var(--nova-border)] rounded p-2 text-xs h-20 outline-none focus:border-[var(--nova-accent)] transition-colors font-mono resize-none"
                />
                <button
                    onClick={handleCompose}
                    disabled={!composeTo.trim() || !composeMsg.trim()}
                    className="self-end px-6 py-1 border border-[var(--nova-accent)] text-[var(--nova-accent)] hover:bg-[var(--nova-accent)]/10 transition-colors text-xs rounded disabled:opacity-50 cursor-pointer"
                >
                    SEND
                </button>
            </div>
        </div>
    );
}

function CommCard({ item, platform, onSend, onDismiss }: { item: any, platform: 'emails' | 'slack' | 'whatsapp', onSend: Function, onDismiss: Function }) {
    const prior = item.priority || 0;
    const dotColor = prior >= 7 ? 'text-[var(--nova-red)]' : prior >= 4 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-green)]';
    const titleColor = platform === 'slack' ? 'text-[var(--nova-accent)]' : 'text-[var(--nova-text)]';

    const [isEditing, setIsEditing] = useState(false);
    const [draftText, setDraftText] = useState(item.draft || '');

    return (
        <div className="nova-card border-[rgba(0,255,204,0.1)] p-4 flex flex-col gap-2 font-mono">
            <div className={`text-xs border-b border-[rgba(0,255,204,0.1)] pb-2 flex justify-between`}>
                <span className="text-[var(--nova-muted)]">┌─ {platform.toUpperCase().replace('S', '')}</span>
                <span className={`text-[10px] ${dotColor}`}>PRIORITY {prior} ●</span>
            </div>

            <div className="grid grid-cols-[60px_1fr] gap-x-2 gap-y-1 text-xs mt-2">
                <span className="text-[var(--nova-muted)]">From:</span>
                <span className={`font-bold ${titleColor}`}>{item.from || item.author}</span>

                {item.subject && (
                    <>
                        <span className="text-[var(--nova-muted)]">Subject:</span>
                        <span className="text-[var(--nova-text)] truncate">{item.subject}</span>
                    </>
                )}

                <span className="text-[var(--nova-muted)]">Time:</span>
                <span className="text-[var(--nova-text)]">{new Date(item.timestamp || Date.now()).toLocaleTimeString()}</span>

                <span className="text-[var(--nova-muted)] mt-1">Message:</span>
                <span className="text-[var(--nova-text)] mt-1 opacity-90 line-clamp-3">{item.preview || item.content}</span>
            </div>

            {item.draft && (
                <div className="mt-3 p-3 bg-black/40 border border-[var(--nova-border)] rounded relative">
                    <span className="absolute -top-2 left-2 bg-[var(--nova-bg)] px-1 text-[8px] text-[var(--nova-accent)] tracking-widest">N.O.V.A DRAFT</span>
                    {isEditing ? (
                        <textarea
                            value={draftText}
                            onChange={(e) => setDraftText(e.target.value)}
                            className="w-full bg-transparent outline-none text-xs text-[var(--nova-text)] resize-none h-16"
                        />
                    ) : (
                        <div className="text-xs text-[var(--nova-text)] opacity-90 whitespace-pre-wrap">{draftText}</div>
                    )}
                </div>
            )}

            <div className="flex gap-4 mt-2 justify-end text-[10px] font-bold tracking-wider">
                {item.draft && (
                    <>
                        <button onClick={() => isEditing ? setIsEditing(false) : setIsEditing(true)} className="text-[var(--nova-muted)] hover:text-white cursor-pointer transition-colors">
                            {isEditing ? '[CANCEL]' : '[EDIT]'}
                        </button>
                        <button
                            onClick={() => onSend(item.id, platform, draftText)}
                            className="text-[var(--nova-green)] hover:text-[var(--nova-green)] brightness-125 cursor-pointer transition-colors"
                        >
                            [SEND REPLY ✓]
                        </button>
                    </>
                )}
                <button onClick={() => onDismiss(item.id, platform)} className="text-[var(--nova-muted)] hover:text-white cursor-pointer transition-colors">
                    [DISMISS]
                </button>
            </div>
        </div>
    );
}
