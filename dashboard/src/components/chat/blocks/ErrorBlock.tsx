export function ErrorBlock({ data, message }: { data: any, message: string }) {
    return (
        <div className="bg-[#0a0a0a] border border-[var(--nova-red)] rounded p-3 font-mono flex flex-col gap-2">
            <div className="text-[var(--nova-red)] text-xs border-b border-[var(--nova-red)]/30 pb-2 mb-1">
                ┌─ MISSION FAILED
            </div>
            <div className="text-[var(--nova-red)] text-xs">
                ✗ {data?.error || message}
            </div>
            {data?.recommendation && (
                <div className="text-[var(--nova-muted)] text-[10px] mt-1">
                    Recommend: {data?.recommendation}
                </div>
            )}
        </div>
    );
}
