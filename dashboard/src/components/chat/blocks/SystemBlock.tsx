export function SystemBlock({ data }: { data: any }) {
    const renderRow = (label: string, value: number, isBattery = false) => {
        const isWarning = value > 80 && !isBattery;
        const color = value < 60 ? 'text-[var(--nova-green)]' : value < 80 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-red)]';
        const filled = Math.round((value / 100) * 10);
        const bar = '█'.repeat(Math.max(0, filled)) + '░'.repeat(Math.max(0, 10 - filled));

        return (
            <div className="flex items-center text-xs">
                <span className="text-[var(--nova-muted)] w-16 uppercase">{label.substring(0, 6)}</span>
                <span className={`${color} mx-2`}>[{bar}]</span>
                <span className="w-8 text-right">{Math.round(value)}%</span>
                <span className="ml-2 w-4 text-center">
                    {isWarning && '⚠'}
                    {isBattery && '⚡'}
                </span>
            </div>
        );
    };

    return (
        <div className="bg-[#0a0a0a] border border-[var(--nova-accent)] rounded p-3 font-mono text-[var(--nova-text)] flex flex-col gap-2">
            <div className="text-[var(--nova-accent)] text-xs border-b border-[var(--nova-accent)]/30 pb-2 mb-1">
                ┌─ SYSTEM SCAN
            </div>
            {renderRow('CPU', data?.cpu ?? 0)}
            {renderRow('MEMORY', data?.memory ?? 0)}
            {renderRow('DISK', data?.disk ?? 0)}
            {renderRow('BATT', data?.battery ?? 0, true)}
        </div>
    );
}
