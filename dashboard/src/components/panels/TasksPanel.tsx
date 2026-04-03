import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";

function Skeleton() { return <div className="nova-card animate-pulse h-16" />; }
function ErrorCard({ msg, onRetry }: { msg: string; onRetry: () => void }) {
    return <div className="nova-card border-[var(--nova-red)] text-xs font-mono text-[var(--nova-red)]">{msg}<button onClick={onRetry} className="ml-3 underline cursor-pointer">RETRY</button></div>;
}

interface Goal { id: string; title: string; progress: number; status: string; target?: string; deadline?: string; }
interface Task { id: string; title: string; priority: string; status: string; deadline?: string; due_time?: string; }

export function TasksPanel() {
    const { get, post, patch, apiFetch } = useApi();
    const del = async (url: string) => {
        return apiFetch(url, { method: 'DELETE' });
    };
    const [goals, setGoals] = useState<Goal[]>([]);
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [showGoalForm, setShowGoalForm] = useState(false);
    const [showTaskForm, setShowTaskForm] = useState(false);
    const [goalForm, setGoalForm] = useState({ title: "", target: "", deadline: "" });
    const [taskForm, setTaskForm] = useState({ title: "", priority: "medium", deadline: "" });

    const fetchAll = useCallback(async () => {
        try {
            const [g, t] = await Promise.all([
                get<any>("/api/goals").catch(() => []),
                get<any>("/api/tasks").catch(() => []),
            ]);
            setGoals(Array.isArray(g) ? g : g?.goals ?? []);
            setTasks(Array.isArray(t) ? t : t?.tasks ?? []);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) { setError(e.message ?? "Fetch failed"); }
        finally { setLoading(false); }
    }, [get]);

    useEffect(() => { fetchAll(); const iv = setInterval(fetchAll, 30000); return () => clearInterval(iv); }, [fetchAll]);

    const addGoal = async () => {
        if (!goalForm.title) return;
        try { await post("/api/goals", goalForm); setGoalForm({ title: "", target: "", deadline: "" }); setShowGoalForm(false); fetchAll(); }
        catch { /* ignore */ }
    };

    const addTask = async () => {
        if (!taskForm.title) return;
        try { await post("/api/tasks", taskForm); setTaskForm({ title: "", priority: "medium", deadline: "" }); setShowTaskForm(false); fetchAll(); }
        catch { /* ignore */ }
    };

    // Deadline warnings
    const urgentTasks = tasks.filter((t) => {
        if (!t.deadline || t.status === "completed") return false;
        const diff = new Date(t.deadline).getTime() - Date.now();
        return diff > 0 && diff < 24 * 60 * 60 * 1000;
    });

    const priorityColor = (p: string) => p === "high" ? "bg-[var(--nova-red)]" : p === "medium" ? "bg-[var(--nova-amber)]" : "bg-[var(--nova-green)]";
    const statusColor = (s: string) => s === "completed" ? "bg-[var(--nova-green)]" : s === "active" || s === "in_progress" ? "bg-[var(--nova-accent)]" : "bg-[var(--nova-muted)]";

    if (loading) return <div className="p-6 flex flex-col gap-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />)}</div>;
    if (error) return <div className="p-6"><ErrorCard msg={error} onRetry={fetchAll} /></div>;

    return (
        <div className="p-6 h-full overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-sm font-mono tracking-[0.3em] uppercase text-[var(--nova-accent)]">TASKS & GOALS</h1>
                <div className="flex items-center gap-3">
                    <span className="text-[9px] font-mono text-[var(--nova-muted)]">UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchAll} className="text-[var(--nova-muted)] hover:text-[var(--nova-accent)] text-xs cursor-pointer">⟳</button>
                </div>
            </div>

            {/* Deadline Warnings */}
            {urgentTasks.map((t) => {
                const diff = new Date(t.deadline!).getTime() - Date.now();
                const h = Math.floor(diff / 3600000); const m = Math.floor((diff % 3600000) / 60000);
                return (
                    <div key={t.id} className="mb-3 px-4 py-2 rounded bg-[var(--nova-amber)]/10 border border-[var(--nova-amber)]/30 text-[10px] font-mono text-[var(--nova-amber)]">
                        ⚠ {t.title} due in {h}h {m}m
                    </div>
                );
            })}

            <div className="grid grid-cols-2 gap-6">
                {/* Goals */}
                <div>
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] uppercase">ACTIVE GOALS</h3>
                        <button onClick={() => setShowGoalForm(!showGoalForm)} className="text-[9px] font-mono text-[var(--nova-accent)] hover:underline cursor-pointer">
                            {showGoalForm ? "CANCEL" : "+ ADD GOAL"}
                        </button>
                    </div>

                    {showGoalForm && (
                        <div className="nova-card mb-3 flex flex-col gap-2">
                            <input value={goalForm.title} onChange={(e) => setGoalForm({ ...goalForm, title: e.target.value })} placeholder="Goal title" className="bg-[var(--nova-surface2)] border border-[var(--nova-border)] rounded px-2 py-1 text-xs font-mono text-[var(--nova-text)] outline-none" />
                            <input value={goalForm.target} onChange={(e) => setGoalForm({ ...goalForm, target: e.target.value })} placeholder="Target" className="bg-[var(--nova-surface2)] border border-[var(--nova-border)] rounded px-2 py-1 text-xs font-mono text-[var(--nova-text)] outline-none" />
                            <input type="date" value={goalForm.deadline} onChange={(e) => setGoalForm({ ...goalForm, deadline: e.target.value })} className="bg-[var(--nova-surface2)] border border-[var(--nova-border)] rounded px-2 py-1 text-xs font-mono text-[var(--nova-text)] outline-none" />
                            <button onClick={addGoal} className="text-[10px] font-mono px-3 py-1.5 rounded bg-[var(--nova-accent)]/10 border border-[var(--nova-accent)]/30 text-[var(--nova-accent)] cursor-pointer hover:bg-[var(--nova-accent)]/20">SUBMIT</button>
                        </div>
                    )}

                    {goals.length === 0 ? (
                        <div className="text-[10px] font-mono text-[var(--nova-muted)] text-center py-8">No active goals</div>
                    ) : (
                        <div className="flex flex-col gap-2">
                            {goals.map((g) => (
                                <div key={g.id} className="nova-card">
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex flex-col">
                                            <span className="text-xs font-mono text-[var(--nova-text)]">{g.title}</span>
                                            {g.deadline && <span className="text-[8px] font-mono text-[var(--nova-muted)] mt-0.5">Due: {g.deadline}</span>}
                                        </div>
                                        <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded ${g.status === "completed" ? "bg-[var(--nova-green)]/20 text-[var(--nova-green)]" : g.status === "missed" ? "bg-[var(--nova-red)]/20 text-[var(--nova-red)]" : "bg-[var(--nova-accent)]/20 text-[var(--nova-accent)]"}`}>
                                            {g.status?.toUpperCase()}
                                        </span>
                                    </div>
                                    <div className="w-full h-1.5 bg-[var(--nova-surface2)] rounded-full overflow-hidden mb-1">
                                        <div className={`h-full rounded-full transition-all duration-500 ${g.status === 'completed' ? 'bg-[#00ffcc]' : 'bg-[#00ffcc]'}`} style={{ width: `${g.status === 'completed' ? 100 : Math.min(g.progress, 100)}%` }} />
                                    </div>
                                    <span className="text-[8px] font-mono text-[var(--nova-muted)]">{g.status === 'completed' ? 100 : g.progress}% complete</span>
                                    <div className="flex gap-2 mt-2">
                                        <button
                                            onClick={async () => {
                                                await patch(
                                                    `/api/goals/${g.id}`,
                                                    { progress: 100, status: 'completed' }
                                                );
                                                fetchAll();
                                            }}
                                            className="text-[9px] font-mono text-[#00ffcc] border border-[#00ffcc]/30 px-2 py-1 rounded hover:bg-[#00ffcc]/10 transition-all cursor-pointer">
                                            ✓ COMPLETE
                                        </button>
                                        <button
                                            onClick={async () => {
                                                await del(`/api/goals/${g.id}`);
                                                fetchAll();
                                            }}
                                            className="text-[9px] font-mono text-red-400 border border-red-400/30 px-2 py-1 rounded hover:bg-red-400/10 transition-all cursor-pointer">
                                            ✕ DELETE
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Tasks */}
                <div>
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-[9px] font-mono tracking-[0.3em] text-[var(--nova-muted)] uppercase">TASK ORCHESTRATION</h3>
                        <button onClick={() => setShowTaskForm(!showTaskForm)} className="text-[9px] font-mono text-[var(--nova-accent)] hover:underline cursor-pointer">
                            {showTaskForm ? "CANCEL" : "+ ADD TASK"}
                        </button>
                    </div>

                    {showTaskForm && (
                        <div className="nova-card mb-3 flex flex-col gap-2">
                            <input value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} placeholder="Task title" className="bg-[var(--nova-surface2)] border border-[var(--nova-border)] rounded px-2 py-1 text-xs font-mono text-[var(--nova-text)] outline-none" />
                            <select value={taskForm.priority} onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })} className="bg-[var(--nova-surface2)] border border-[var(--nova-border)] rounded px-2 py-1 text-xs font-mono text-[var(--nova-text)] outline-none">
                                <option value="high">High</option>
                                <option value="medium">Medium</option>
                                <option value="low">Low</option>
                            </select>
                            <input type="date" value={taskForm.deadline} onChange={(e) => setTaskForm({ ...taskForm, deadline: e.target.value })} className="bg-[var(--nova-surface2)] border border-[var(--nova-border)] rounded px-2 py-1 text-xs font-mono text-[var(--nova-text)] outline-none" />
                            <button onClick={addTask} className="text-[10px] font-mono px-3 py-1.5 rounded bg-[var(--nova-accent)]/10 border border-[var(--nova-accent)]/30 text-[var(--nova-accent)] cursor-pointer hover:bg-[var(--nova-accent)]/20">SUBMIT</button>
                        </div>
                    )}

                    {tasks.length === 0 ? (
                        <div className="text-[10px] font-mono text-[var(--nova-muted)] text-center py-8">No tasks</div>
                    ) : (
                        <div className="flex flex-col gap-1">
                            {tasks.map((t) => {
                                const done = t.status === "completed";
                                return (
                                    <div key={t.id} className={`nova-card flex items-center gap-3 !py-2 ${done ? "opacity-50" : ""}`}>
                                        <div className={`w-1 h-8 rounded ${priorityColor(t.priority)}`} />
                                        <div className={`w-2 h-2 rounded-full ${statusColor(t.status)}`} />
                                        <span className={`text-[10px] font-mono flex-1 ${done ? "line-through text-[var(--nova-muted)]" : "text-[var(--nova-text)]"}`}>{t.title}</span>
                                        {t.due_time && <span className="text-[8px] font-mono text-[var(--nova-muted)]">{t.due_time}</span>}
                                        <button
                                            onClick={async () => {
                                                await patch(
                                                    `/api/tasks/${t.id}`,
                                                    { status: 'completed' }
                                                );
                                                fetchAll();
                                            }}
                                            className="text-[9px] font-mono text-[#00ffcc] hover:underline cursor-pointer">
                                            ✓ Complete
                                        </button>
                                        <button
                                            onClick={async () => {
                                                await del(`/api/tasks/${t.id}`);
                                                fetchAll();
                                            }}
                                            className="text-[9px] font-mono text-red-400 hover:underline cursor-pointer ml-2">
                                            ✕
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
