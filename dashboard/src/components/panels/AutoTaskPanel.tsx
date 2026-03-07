import { useState, useEffect } from "react";
import { useApi } from "../../hooks/useApi";

const TEMPLATES = [
    "Take a screenshot of my screen",
    "Check system health and report",
    "List all files in Downloads folder",
    "Open Chrome and go to google.com",
    "Read the file ~/Desktop/notes.txt",
    "Show running processes"
];

export function AutoTaskPanel() {
    const api = useApi();
    const [instruction, setInstruction] = useState('');
    const [isPlanning, setIsPlanning] = useState(false);
    const [activeTasks, setActiveTasks] = useState<any[]>([]);
    const [history, setHistory] = useState<any[]>([]);

    const handleExecute = async () => {
        if (!instruction.trim()) return;
        setIsPlanning(true);
        try {
            await api.post('/api/nova/execute', { instruction });
            setInstruction('');
        } catch (err) {
            console.error(err);
        } finally {
            setIsPlanning(false);
        }
    };

    useEffect(() => {
        const poll = async () => {
            try {
                const res: any = await api.get('/api/nova/tasks/active');
                setActiveTasks(res.tasks || []);
            } catch { /* ignore */ }
        };
        poll();
        const iv = setInterval(poll, 2000);
        return () => clearInterval(iv);
    }, [api]);

    useEffect(() => {
        const load = async () => {
            try {
                const res: any = await api.get('/api/nova/tasks/history');
                setHistory(res.history || []);
            } catch { /* ignore */ }
        };
        load();
    }, [activeTasks, api]);

    return (
        <div className="h-full overflow-y-auto p-6 flex flex-col gap-6">
            {/* New Task Input */}
            <div className="nova-card p-4">
                <h3 className="text-[#00ffcc] font-mono text-xs mb-3 tracking-widest">
                    NEW AUTONOMOUS TASK
                </h3>
                <div className="flex flex-wrap gap-2 mb-4">
                    {TEMPLATES.map(t => (
                        <button
                            key={t}
                            onClick={() => setInstruction(t)}
                            className="px-2 py-1 rounded border border-[rgba(0,255,204,0.2)] text-[#00ffcc] font-mono text-xs hover:bg-[rgba(0,255,204,0.08)] transition-all"
                        >
                            {t}
                        </button>
                    ))}
                </div>
                <textarea
                    value={instruction}
                    onChange={e => setInstruction(e.target.value)}
                    placeholder="Describe what you want N.O.V.A to do...&#10;Example: Open Chrome, go to github.com, take a screenshot and save it to my desktop"
                    className="w-full bg-[#0a1a1a] border border-[rgba(0,255,204,0.2)] rounded p-3 text-[#e2e8f0] font-mono text-sm resize-none outline-none focus:border-cyan-400 placeholder-[#4a6a6a]"
                    rows={3}
                />
                <div className="flex gap-2 mt-3">
                    <button
                        onClick={handleExecute}
                        disabled={!instruction.trim() || isPlanning}
                        className="flex-1 py-2 rounded border border-[#00ffcc] text-[#00ffcc] font-mono text-sm hover:bg-[rgba(0,255,204,0.08)] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                    >
                        {isPlanning ? '⟳ PLANNING...' : '▶ EXECUTE TASK'}
                    </button>
                    <button
                        onClick={() => setInstruction('')}
                        className="px-4 py-2 rounded border border-[rgba(255,255,255,0.1)] text-[#4a6a6a] font-mono text-sm hover:border-red-500 hover:text-red-500 transition-all"
                    >
                        CLEAR
                    </button>
                </div>
            </div>

            {/* Active Tasks */}
            <div>
                <h3 className="text-[#00ffcc] font-mono text-xs mb-3 tracking-widest">
                    ACTIVE TASKS
                </h3>
                {activeTasks.length === 0 ? (
                    <div className="text-[#4a6a6a] font-mono text-sm text-center py-6 border border-dashed border-[rgba(255,255,255,0.1)] rounded">
                        No active tasks
                    </div>
                ) : (
                    <div className="flex flex-col gap-4">
                        {activeTasks.map(task => {
                            const pct = Math.round((task.current_step / Math.max(1, task.total_steps)) * 100);
                            return (
                                <div key={task.id} className="nova-card p-4">
                                    <div className="flex justify-between items-center mb-4">
                                        <span className="text-[#e2e8f0] font-mono text-sm uppercase">{task.title}</span>
                                        <span className="text-[#00ffcc] font-mono text-xs">{pct}%</span>
                                    </div>

                                    {/* Progress Bar */}
                                    <div className="w-full h-1.5 bg-[var(--nova-surface2)] rounded-full overflow-hidden mb-4">
                                        <div className="h-full bg-[#00ffcc] transition-all duration-500" style={{ width: `${pct}%` }} />
                                    </div>

                                    {/* Steps */}
                                    <div className="flex flex-col gap-2 mb-4">
                                        {task.steps.map((step: any, i: number) => {
                                            let icon = '○';
                                            let color = 'text-[#4a6a6a]';
                                            if (step.status === 'completed') {
                                                icon = '✓';
                                                color = 'text-[#00ffcc]';
                                            } else if (step.status === 'running') {
                                                icon = '◌';
                                                color = 'text-cyan-400 animate-spin-slow'; // ensure animate-spin-slow exists or fallback to animate-spin
                                            } else if (step.status === 'failed') {
                                                icon = '✗';
                                                color = 'text-red-500';
                                            }

                                            return (
                                                <div key={i} className="flex gap-2 items-start">
                                                    <span className={`${color} font-mono w-4 flex-shrink-0 text-center`}>{icon}</span>
                                                    <span className="text-[#e2e8f0] font-mono text-xs flex-1">{step.description}</span>
                                                    <span className="text-[#4a6a6a] font-mono text-[10px] uppercase w-20 text-right">{step.status}</span>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    <div className="flex gap-2">
                                        <button
                                            onClick={async () => {
                                                try {
                                                    await api.post(task.status === 'paused' ? `/api/nova/tasks/${task.id}/resume` : `/api/nova/tasks/${task.id}/pause`, {});
                                                } catch { /* ignore */ }
                                            }}
                                            className="px-3 py-1 rounded border border-[rgba(255,255,255,0.1)] text-[#4a6a6a] font-mono text-xs hover:border-[#00ffcc] hover:text-[#00ffcc] transition-all"
                                        >
                                            {task.status === 'paused' ? 'RESUME' : 'PAUSE'}
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* History */}
            <div>
                <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] mb-3 uppercase">
                    COMPLETED TASKS
                </h3>
                {history.length === 0 ? (
                    <div className="text-[10px] font-mono text-[var(--nova-muted)] text-center py-6">
                        NO HISTORY
                    </div>
                ) : (
                    <div className="flex flex-col gap-2">
                        {history.map(t => (
                            <div key={t.id} className="nova-card p-3 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <span className={`text-[10px] font-mono uppercase ${t.status === 'completed' ? 'text-[#00ffcc]' : 'text-red-500'}`}>
                                        {t.status}
                                    </span>
                                    <span className="text-[#e2e8f0] font-mono text-xs">{t.title}</span>
                                </div>
                                <div className="text-[#4a6a6a] font-mono text-[10px]">
                                    {t.steps_count} steps | {new Date(t.completed_at || '').toLocaleTimeString()}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
