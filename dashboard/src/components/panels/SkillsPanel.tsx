import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";

function Skeleton() {
    return <div className="nova-card animate-pulse h-32" />;
}

export function SkillsPanel() {
    const { get, post } = useApi();
    const { addToast } = useNovaStore();

    const [installed, setInstalled] = useState<any[]>([]);
    const [available, setAvailable] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    const [installingId, setInstallingId] = useState<string | null>(null);

    // Custom Builder form
    const [bName, setBName] = useState("");
    const [bDesc, setBDesc] = useState("");
    const [bTrigger, setBTrigger] = useState("");
    const [bActions, setBActions] = useState("");
    const [generating, setGenerating] = useState(false);
    const [generatedCode, setGeneratedCode] = useState("");

    const fetchSkills = useCallback(async () => {
        try {
            const res = await get<any>('/api/skills').catch(() => ({ installed: [], available: [] }));
            setInstalled(res.installed || []);
            setAvailable(res.available || []);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch skills");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchSkills();
        const iv = setInterval(fetchSkills, 30000);
        return () => clearInterval(iv);
    }, [fetchSkills]);

    const handleInstall = async (skillId: string) => {
        if (installingId) return;
        setInstallingId(skillId);
        try {
            await post<{ skill_id: string }>('/api/skills/install', { skill_id: skillId });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Skill installed successfully' });
            fetchSkills();
        } catch (e: any) {
            addToast({ id: crypto.randomUUID(), type: 'error', message: e.message || 'Failed to install skill' });
        } finally {
            setInstallingId(null);
        }
    };

    const handleGenerateSkill = async () => {
        if (!bName || !bDesc || !bTrigger || !bActions) {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'All builder fields are required' });
            return;
        }
        setGenerating(true);
        setGeneratedCode("");
        try {
            const prompt = `Generate a python NOVA skill plugin:
Name: ${bName}
Desc: ${bDesc}
Trigger: ${bTrigger}
Actions: ${bActions}

Return ONLY python code, no markdown wrappers.`;
            const res = await post<any>('/api/chat', { message: prompt });
            setGeneratedCode(res.response || JSON.stringify(res));
        } catch (e: any) {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to generate skill code' });
        } finally {
            setGenerating(false);
        }
    };

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    const activeCount = installed.filter(s => s.active).length;

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">SKILLS MODULE</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchSkills} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            {/* Stats Row */}
            <div className="grid grid-cols-3 gap-4">
                <div className="nova-card p-4 flex flex-col items-center justify-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)]">INSTALLED</span>
                    <span className="text-2xl text-[var(--nova-accent)]">{installed.length}</span>
                </div>
                <div className="nova-card p-4 flex flex-col items-center justify-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)]">ACTIVE</span>
                    <span className="text-2xl text-[var(--nova-green)]">{activeCount}</span>
                </div>
                <div className="nova-card p-4 flex flex-col items-center justify-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)]">AVAILABLE</span>
                    <span className="text-2xl text-[var(--nova-muted)]">{available.length}</span>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
                {/* LEFT COL: Installed Skills */}
                <div className="flex flex-col gap-4">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">INSTALLED SKILLS</div>
                    {installed.map(s => (
                        <div key={s.id} className={`nova-card border p-4 flex flex-col gap-3 ${s.active ? 'border-[var(--nova-border)]' : 'border-[var(--nova-border)] opacity-60'}`}>
                            <div className="flex justify-between items-start">
                                <div className="flex flex-col gap-1">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[var(--nova-text)] text-sm font-bold">🔧 {s.name}</span>
                                        <span className="text-[10px] text-[var(--nova-muted)]">v{s.version || '1.0'}</span>
                                    </div>
                                    <span className="text-[10px] text-[var(--nova-muted)] max-w-xs">{s.description}</span>
                                </div>
                                <div className="flex items-center gap-2 text-[10px]">
                                    <span className={`font-bold tracking-widest ${s.active ? 'text-[var(--nova-green)]' : 'text-[var(--nova-red)]'}`}>
                                        [{s.active ? 'ACTIVE' : 'DISABLED'} ●]
                                    </span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between mt-2 pt-2 border-t border-[var(--nova-surface2)] text-[10px]">
                                <span className="text-[var(--nova-muted)]">Runs: {s.runs || 0} &nbsp;|&nbsp; Last used: {s.last_used || 'Never'}</span>
                                <div className="flex gap-4">
                                    <button className="text-[var(--nova-amber)] hover:underline cursor-pointer uppercase tracking-wider">{s.active ? 'DISABLE' : 'ENABLE'}</button>
                                    <button className="text-[var(--nova-red)] hover:underline cursor-pointer uppercase tracking-wider" onClick={() => {
                                        if (window.confirm(`Remove skill ${s.name}?`)) {
                                            // Handle remove locally or trigger api
                                            addToast({ id: crypto.randomUUID(), type: 'info', message: 'Skill removal not fully implemented yet' });
                                        }
                                    }}>REMOVE</button>
                                </div>
                            </div>
                        </div>
                    ))}
                    {installed.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-8">No skills installed</div>}
                </div>

                {/* RIGHT COL: Available Skills & Custom Builder */}
                <div className="flex flex-col gap-6">
                    <div className="flex flex-col gap-4">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">AVAILABLE SKILLS</div>
                        <div className="grid grid-cols-2 gap-4">
                            {available.map(s => (
                                <div key={s.id} className="nova-card p-4 flex flex-col justify-between gap-3">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-[var(--nova-text)] text-sm font-bold truncate">🌐 {s.name}</span>
                                        <span className="text-[10px] text-[var(--nova-muted)] line-clamp-3">{s.description}</span>
                                    </div>
                                    <div className="flex justify-end mt-2">
                                        <button
                                            onClick={() => handleInstall(s.id)}
                                            disabled={installingId === s.id}
                                            className="text-[10px] text-[var(--nova-accent)] hover:underline tracking-widest uppercase disabled:opacity-50 cursor-pointer"
                                        >
                                            {installingId === s.id ? 'INSTALLING...' : '[INSTALL ↓]'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {available.length === 0 && <div className="text-xs text-[var(--nova-muted)] text-center py-4 col-span-2">No new skills available</div>}
                        </div>
                    </div>

                    <div className="flex flex-col gap-4">
                        <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">BUILD CUSTOM SKILL</div>
                        <div className="nova-card p-4 flex flex-col gap-3 text-xs">
                            <input type="text" placeholder="Skill Name (e.g., Notion Sync)" className="bg-[var(--nova-surface2)] text-[var(--nova-text)] p-2 outline-none rounded" value={bName} onChange={e => setBName(e.target.value)} />
                            <textarea placeholder="Description" className="bg-[var(--nova-surface2)] text-[var(--nova-text)] p-2 outline-none rounded resize-none h-16" value={bDesc} onChange={e => setBDesc(e.target.value)} />
                            <input type="text" placeholder="Trigger Phrase (e.g., 'sync my notes')" className="bg-[var(--nova-surface2)] text-[var(--nova-text)] p-2 outline-none rounded" value={bTrigger} onChange={e => setBTrigger(e.target.value)} />
                            <textarea placeholder="Actions (Describe what it should do)" className="bg-[var(--nova-surface2)] text-[var(--nova-text)] p-2 outline-none rounded resize-none h-24" value={bActions} onChange={e => setBActions(e.target.value)} />

                            <button
                                onClick={handleGenerateSkill}
                                disabled={generating}
                                className="bg-[var(--nova-accent)] text-black p-2 font-bold tracking-widest rounded hover:opacity-90 transition-opacity mt-2 cursor-pointer disabled:opacity-50"
                            >
                                {generating ? 'GENERATING...' : 'GENERATE SKILL'}
                            </button>

                            {generatedCode && (
                                <div className="mt-4 flex flex-col gap-3">
                                    <div className="bg-black p-3 rounded text-[10px] text-[var(--nova-text)] overflow-x-auto whitespace-pre font-mono border border-[var(--nova-border)]">
                                        {generatedCode}
                                    </div>
                                    <button
                                        className="border border-[var(--nova-accent)] text-[var(--nova-accent)] p-2 font-bold tracking-widest rounded hover:bg-[var(--nova-accent)] hover:text-black transition-colors cursor-pointer"
                                        onClick={() => addToast({ id: crypto.randomUUID(), type: 'info', message: 'Custom installation not fully wired' })}
                                    >
                                        INSTALL GENERATED SKILL
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
