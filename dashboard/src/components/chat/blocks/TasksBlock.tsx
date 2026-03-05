export function TasksBlock({ data }: { data: any }) {
    const getDotColor = (status: string) => {
        const s = status.toLowerCase();
        if (s.includes('done') || s.includes('complete')) return 'text-[var(--nova-green)]';
        if (s.includes('prog') || s.includes('active')) return 'text-[var(--nova-amber)]';
        return 'text-[var(--nova-red)]'; // open
    };

    const getPriorityColor = (p: string) => {
        const pr = p.toLowerCase();
        if (pr.includes('high')) return 'text-[var(--nova-red)]';
        if (pr.includes('med')) return 'text-[var(--nova-amber)]';
        return 'text-[var(--nova-muted)]';
    };

    if (data?.tasks && data.tasks.length > 0) {
        return (
            <div className="bg-[#0a0a0a] border border-[var(--nova-border)] rounded p-3 font-mono flex flex-col gap-2">
                <div className="text-[var(--nova-accent)] text-xs border-b border-[var(--nova-border)] pb-2 mb-1">
                    ┌─ ACTIVE TASKS
                </div>
                <div className="flex flex-col gap-2">
                    {data.tasks.map((t: any, i: number) => (
                        <div key={i} className="flex items-center text-xs justify-between gap-3">
                            <span className={getDotColor(t.status)}>{t.status === 'completed' ? '✓' : '○'}</span>
                            <span className="text-[var(--nova-text)] flex-1 truncate">{t.title}</span>
                            <span className={getPriorityColor(t.priority || 'low')}>{t.priority?.toUpperCase() || 'LOW'}</span>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (data?.issues && data.issues.length > 0) {
        return (
            <div className="bg-[#0a0a0a] border border-[var(--nova-border)] rounded p-3 font-mono flex flex-col gap-2">
                <div className="text-[var(--nova-accent)] text-xs border-b border-[var(--nova-border)] pb-2 mb-1">
                    ┌─ JIRA ISSUES
                </div>
                <div className="flex flex-col gap-2">
                    {data.issues.map((iss: any, i: number) => (
                        <div key={i} className="flex items-center text-xs justify-between gap-3">
                            <span className="text-[var(--nova-muted)] w-14">{iss.key}</span>
                            <span className="text-[var(--nova-text)] flex-1 truncate">{iss.summary}</span>
                            <span className={getDotColor(iss.status)}>{iss.status.toUpperCase()}</span>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="bg-[#0a0a0a] border border-[var(--nova-border)] rounded p-3 font-mono text-xs text-[var(--nova-muted)]">
            No tasks found.
        </div>
    );
}
