export function MissionBlock({ data }: { data: any }) {
    return (
        <div className="bg-[#0a0a0a] border-l-2 border-l-[var(--nova-green)] border border-[var(--nova-border)] rounded p-3 font-mono flex flex-col gap-2">
            <div className="text-[var(--nova-green)] text-xs border-b border-[var(--nova-border)] pb-2 mb-1">
                ┌─ MISSION COMPLETE
            </div>
            <div className="flex flex-col gap-1 text-xs text-[var(--nova-text)]">
                {data?.actions?.map((act: string, i: number) => (
                    <div key={i}>✓ {act}</div>
                ))}
                {data?.action && <div>✓ {data.action}</div>}
                {(!data?.actions || data?.actions.length === 0) && !data?.action && <div>✓ Task complete</div>}
            </div>
            {data?.project && (
                <div className="mt-2 text-xs text-[var(--nova-accent)]">
                    Workspace: {data.project} — ACTIVE
                </div>
            )}
        </div>
    );
}
