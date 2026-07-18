import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../../hooks/useApi";

interface ColumnDef {
    key: string;
    label: string;
    truncate?: boolean;
}

interface Props {
    title: string;
    endpoint: string;
    columns: ColumnDef[];
    idKey: string;
    onInspect: (id: string) => void;
}

export function ListView({ title, endpoint, columns, idKey, onInspect }: Props) {
    const { get } = useApi();
    const [items, setItems] = useState<Record<string, unknown>[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await get<Record<string, unknown>[]>(endpoint);
            setItems(data);
            setError("");
        } catch (e: any) {
            setError(e.message ?? "Failed to load");
        } finally {
            setLoading(false);
        }
    }, [get, endpoint]);

    useEffect(() => { load(); }, [load]);

    if (loading) return <div className="p-4 text-xs font-mono text-[var(--nova-muted)] animate-pulse">Loading {title.toLowerCase()}...</div>;
    if (error) return <div className="p-4 text-xs font-mono text-[var(--nova-red)]">{error} <button onClick={load} className="ml-2 text-[var(--nova-accent)] hover:underline">Retry</button></div>;

    return (
        <div className="flex flex-col h-full">
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase">{title}</h2>
                <div className="flex items-center gap-3">
                    <span className="text-[9px] font-mono text-[var(--nova-muted)]">{items.length} total</span>
                    <button onClick={load} className="text-[9px] font-mono text-[var(--nova-muted)] hover:text-[var(--nova-accent)] transition-colors px-2 py-1 border border-[var(--nova-border)] rounded">⟳</button>
                </div>
            </div>

            <div className="flex-1 overflow-auto bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg">
                <table className="w-full text-xs font-mono">
                    <thead className="sticky top-0 bg-[var(--nova-surface2)]/95 backdrop-blur z-10">
                        <tr>
                            {columns.map(col => (
                                <th key={col.key} className="text-left text-[9px] tracking-wider text-[var(--nova-muted)] uppercase font-normal py-2.5 px-3 border-b border-[var(--nova-border)]/50">
                                    {col.label}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {items.length === 0 && (
                            <tr><td colSpan={columns.length} className="text-center py-8 text-[var(--nova-muted)]">No data.</td></tr>
                        )}
                        {items.map((item, i) => (
                            <tr
                                key={i}
                                onClick={() => onInspect(String(item[idKey] ?? ""))}
                                className="border-b border-[var(--nova-border)]/20 hover:bg-[var(--nova-accent)]/5 transition-colors cursor-pointer"
                            >
                                {columns.map(col => (
                                    <td key={col.key} className={`py-2 px-3 text-[var(--nova-text)] ${col.truncate ? "truncate max-w-[200px]" : ""}`}>
                                        {String(item[col.key] ?? "—")}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
