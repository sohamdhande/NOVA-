import { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi";

export function TaskProgressToast() {
    const api = useApi();
    const [activeTasks, setActiveTasks] = useState<any[]>([]);

    useEffect(() => {
        const poll = async () => {
            try {
                const res: any = await api.get('/api/nova/tasks/active');
                setActiveTasks(res.tasks || []);
            } catch { /* ignore */ }
        };
        poll();
        const iv = setInterval(poll, 3000);
        return () => clearInterval(iv);
    }, [api]);

    if (activeTasks.length === 0) return null;

    return (
        <div className="fixed bottom-6 left-6 z-50 flex flex-col gap-2 pointer-events-none">
            {activeTasks.map((task: any) => {
                const pct = Math.round((task.current_step / Math.max(1, task.total_steps)) * 100);
                const currentStepStr = task.steps.find((s: any) => s.status === 'running')?.description || 'Processing...';

                return (
                    <div key={task.id} className="bg-[#0a1a1a] border-l-2 border-l-[#00ffcc] border border-[rgba(255,255,255,0.05)] rounded p-3 w-80 shadow-lg pointer-events-auto flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                            <span className="text-[#e2e8f0] font-mono text-xs truncate uppercase font-bold pr-2">{task.title}</span>
                            <span className="text-[#00ffcc] font-mono text-[10px]">{pct}%</span>
                        </div>

                        <div className="w-full h-1 bg-[var(--nova-surface2)] rounded-full overflow-hidden">
                            <div className="h-full bg-[#00ffcc] transition-all duration-500" style={{ width: `${pct}%` }} />
                        </div>

                        <span className="text-[#4a6a6a] font-mono text-[10px] truncate">
                            {currentStepStr}
                        </span>

                        {pct === 100 && (
                            <button className="text-[9px] border bg-[rgba(0,255,204,0.1)] border-[rgba(0,255,204,0.3)] text-[#00ffcc] font-mono rounded px-2 py-0.5 mt-1 hover:bg-[rgba(0,255,204,0.2)]">
                                DONE
                            </button>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
