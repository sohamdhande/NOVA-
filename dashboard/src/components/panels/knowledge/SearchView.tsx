import { useState, useCallback } from "react";
import { useApi } from "../../../hooks/useApi";

interface SearchResult {
    type: string;
    id: string;
    full_id?: string;
    text: string;
}

interface Props {
    onInspect: (id: string) => void;
}

export function SearchView({ onInspect }: Props) {
    const { get } = useApi();
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [searched, setSearched] = useState(false);
    const [loading, setLoading] = useState(false);

    const search = useCallback(async () => {
        if (!query.trim()) return;
        setLoading(true);
        try {
            const data = await get<SearchResult[]>(`/api/knowledge/search?q=${encodeURIComponent(query)}`);
            setResults(data);
            setSearched(true);
        } catch {
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, [get, query]);

    const grouped = {
        commit: results.filter(r => r.type === "commit"),
        observation: results.filter(r => r.type === "observation"),
        entity: results.filter(r => r.type === "entity"),
        artifact: results.filter(r => r.type === "artifact"),
    };

    return (
        <div className="flex flex-col h-full">
            <h2 className="text-xs font-mono tracking-widest text-[var(--nova-accent)] uppercase mb-3">Knowledge Search</h2>

            {/* Search bar */}
            <div className="flex gap-2 mb-4">
                <input
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && search()}
                    placeholder="Search entities, artifacts, commits, observations..."
                    className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded px-3 py-2 text-sm font-mono text-[var(--nova-text)] focus:outline-none focus:border-[var(--nova-accent)] placeholder:text-[var(--nova-muted)]"
                />
                <button
                    onClick={search}
                    disabled={!query.trim() || loading}
                    className="bg-[var(--nova-accent)] text-black font-bold px-4 py-2 rounded text-xs font-mono uppercase tracking-wider hover:brightness-110 disabled:opacity-40 transition-all"
                >
                    {loading ? "..." : "Search"}
                </button>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto space-y-4">
                {!searched && (
                    <div className="text-xs font-mono text-[var(--nova-muted)] text-center mt-12">
                        Enter a query to search the knowledge graph.
                    </div>
                )}
                {searched && results.length === 0 && (
                    <div className="text-xs font-mono text-[var(--nova-muted)] text-center mt-12">
                        No results for "{query}".
                    </div>
                )}

                {Object.entries(grouped).map(([type, items]) => {
                    if (items.length === 0) return null;
                    const colors: Record<string, string> = {
                        commit: "text-[var(--nova-accent)]",
                        observation: "text-[#60a5fa]",
                        entity: "text-[#a78bfa]",
                        artifact: "text-[var(--nova-amber)]",
                    };
                    return (
                        <div key={type}>
                            <h3 className={`text-[10px] font-mono tracking-widest uppercase mb-2 ${colors[type] || "text-[var(--nova-muted)]"}`}>
                                {type}s ({items.length})
                            </h3>
                            <div className="space-y-1">
                                {items.map((item, i) => (
                                    <button
                                        key={i}
                                        onClick={() => onInspect(item.full_id || item.id)}
                                        className="w-full text-left p-2.5 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded hover:border-[var(--nova-accent)]/30 hover:bg-[var(--nova-accent)]/5 transition-colors"
                                    >
                                        <div className="text-xs font-mono text-[var(--nova-text)] truncate">{item.id}</div>
                                        <div className="text-[10px] font-mono text-[var(--nova-muted)] truncate mt-0.5">{item.text}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
