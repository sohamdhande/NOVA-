import { useState } from 'react';

export function FilesBlock({ data }: { data: any }) {
    const [copied, setCopied] = useState<string | null>(null);

    const copyPath = (path: string) => {
        navigator.clipboard.writeText(path);
        setCopied(path);
        setTimeout(() => setCopied(null), 2000);
    };

    const truncate = (p: string) => p.length > 40 ? '...' + p.slice(-37) : p;

    if (data?.content) {
        // file_read
        return (
            <div className="bg-[#0a0a0a] border border-[var(--nova-border)] rounded p-3 font-mono flex flex-col gap-2">
                <div className="text-[var(--nova-muted)] text-xs border-b border-[var(--nova-border)] pb-2 mb-1 flex justify-between">
                    <span>┌─ FILE</span>
                    <span>({data?.lines} lines)</span>
                </div>
                <div
                    className="text-[var(--nova-accent)] text-xs cursor-pointer hover:underline relative"
                    onClick={() => copyPath(data?.path)}
                >
                    📄 {truncate(data?.path || '')}
                    {copied === data?.path && <span className="ml-2 text-[var(--nova-green)] text-[10px]">Copied!</span>}
                </div>
                <div className="text-[var(--nova-text)] text-xs whitespace-pre-wrap max-h-[200px] overflow-y-auto mt-2 p-2 bg-black/50 rounded">
                    {data?.content}
                </div>
            </div>
        );
    }

    if (data?.results) {
        // file_search
        return (
            <div className="bg-[#0a0a0a] border border-[var(--nova-border)] rounded p-3 font-mono flex flex-col gap-2">
                <div className="text-[var(--nova-muted)] text-xs border-b border-[var(--nova-border)] pb-2 mb-1">
                    ┌─ SEARCH RESULTS (Found: {data?.results?.length})
                </div>
                <div className="text-[var(--nova-text)] text-xs mb-2">Query: "{data?.query}"</div>
                <div className="max-h-[200px] overflow-y-auto flex flex-col gap-1">
                    {data?.results?.slice(0, 10).map((r: string, i: number) => (
                        <div
                            key={i}
                            className="text-[var(--nova-accent)] text-xs cursor-pointer hover:underline"
                            onClick={() => copyPath(r)}
                        >
                            📄 {truncate(r)}
                            {copied === r && <span className="ml-2 text-[var(--nova-green)] text-[10px]">Copied!</span>}
                        </div>
                    ))}
                    {data?.results?.length > 10 && (
                        <div className="text-[var(--nova-muted)] text-xs mt-1">... +{data?.results.length - 10} more</div>
                    )}
                </div>
            </div>
        );
    }

    return null;
}
