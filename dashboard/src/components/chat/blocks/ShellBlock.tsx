export function ShellBlock({ data }: { data: any }) {
    const isSuccess = data?.exit_code === 0;
    return (
        <div className="bg-[#0a0a0a] border border-[var(--nova-border)] rounded p-3 font-mono flex flex-col gap-2">
            <div className="text-[var(--nova-muted)] text-xs border-b border-[var(--nova-border)] pb-2 mb-1">
                ┌─ TERMINAL OUTPUT
            </div>
            <div className="text-[var(--nova-accent)] text-xs">$ {data?.command}</div>
            <div className="text-[var(--nova-green)] text-xs whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                {data?.output}
            </div>
            <div className={`text-xs text-right mt-2 ${isSuccess ? 'text-[var(--nova-green)]' : 'text-[var(--nova-red)]'}`}>
                exit: {data?.exit_code ?? 'None'} {isSuccess ? '✓' : '✗'}
            </div>
        </div>
    );
}
