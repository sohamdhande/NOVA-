import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";

function Skeleton() {
    return <div className="nova-card animate-pulse h-24" />;
}

export function FilesPanel() {
    const { get, post } = useApi();
    const { addToast } = useNovaStore();

    const [stats, setStats] = useState<any>({});
    const [largeFiles, setLargeFiles] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    const [currentPath, setCurrentPath] = useState("~/");
    const [filesList, setFilesList] = useState<any[]>([]);
    const [filesLoading, setFilesLoading] = useState(false);

    const [searchQuery, setSearchQuery] = useState("");

    const [previewContent, setPreviewContent] = useState<string | null>(null);

    const fetchFileStats = useCallback(async () => {
        try {
            const res = await get<any>('/api/files').catch(() => ({}));
            setStats(res);
            setLargeFiles(res.large_files || []);
            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch file stats");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchFileStats();
        const iv = setInterval(fetchFileStats, 60000);
        return () => clearInterval(iv);
    }, [fetchFileStats]);

    const loadDirectory = useCallback(async (path: string) => {
        setFilesLoading(true);
        try {
            const res = await get<any>(`/api/files/list?path=${encodeURIComponent(path)}`);
            setFilesList(res.files || []);
            setCurrentPath(path);
        } catch (e: any) {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to explore path' });
        } finally {
            setFilesLoading(false);
        }
    }, [get, addToast]);

    useEffect(() => {
        loadDirectory("~/");
    }, [loadDirectory]);

    const navigateUp = () => {
        if (currentPath === "~/" || currentPath === "/") return;
        const parts = currentPath.replace(/\/$/, "").split("/");
        parts.pop();
        const newPath = parts.join("/") || "/";
        loadDirectory(newPath);
    };

    const handleFileClick = async (file: any) => {
        if (file.is_dir) {
            loadDirectory(file.path);
        } else {
            try {
                const res = await post<any>('/api/files/read', { path: file.path });
                setPreviewContent(res.content || "Empty or binary file");
            } catch (e) {
                addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to read file' });
            }
        }
    };

    const handleDeleteHighRisk = async (path: string) => {
        if (window.confirm(`Delete ${path}? This requires an approval from HQ.`)) {
            // Trigger HQ approval via POST
            try {
                await post('/api/terminal', { command: `rm -rf "${path}"` });
                addToast({ id: crypto.randomUUID(), type: 'info', message: 'Deletion sent for approval.' });
            } catch {
                addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to trigger deletion.' });
            }
        }
    };

    const handlePerformSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!searchQuery.trim()) return;
        try {
            await post('/api/chat', { message: `search files ${searchQuery}` });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Search query dispatched to HQ' });
            setSearchQuery("");
        } catch (e) {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Search failed' });
        }
    };

    const dlSize = stats.downloads_mb || 0;
    const isDlLarge = dlSize > 1000;
    const dupCount = stats.duplicates || 0;

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6 relative">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">FILE SYSTEM</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchFileStats} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
                <div className="nova-card p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)]">DOWNLOADS</span>
                    <span className="text-xl text-[var(--nova-text)]">{stats.downloads_count || 0}</span>
                </div>
                <div className="nova-card p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)]">DOWNLOADS SIZE</span>
                    <span className={`text-xl ${isDlLarge ? 'text-[var(--nova-red)]' : 'text-[var(--nova-text)]'}`}>{dlSize.toFixed(1)} MB</span>
                </div>
                <div className="nova-card p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)]">DUPLICATES</span>
                    <span className={`text-xl ${dupCount > 0 ? 'text-[var(--nova-amber)]' : 'text-[var(--nova-text)]'}`}>{dupCount}</span>
                </div>
                <div className="nova-card p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--nova-muted)]">TRASH</span>
                    <span className="text-xl text-[var(--nova-text)]">{(stats.trash_mb || 0).toFixed(1)} MB</span>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-4">
                <button onClick={() => post('/api/nova/cleanup', {}).then(() => fetchFileStats())} className="flex-1 nova-card p-3 text-xs tracking-widest uppercase hover:bg-[var(--nova-surface2)] transition-colors cursor-pointer text-center border border-[var(--nova-border)]">CLEAN DOWNLOADS</button>
                <button onClick={() => post('/api/terminal', { command: "rm -rf ~/.Trash/*" })} className="flex-1 nova-card p-3 text-xs tracking-widest uppercase hover:text-[var(--nova-red)] hover:border-[var(--nova-red)] transition-colors cursor-pointer text-center border border-[var(--nova-border)]">EMPTY TRASH</button>
                <button onClick={() => post('/api/chat', { message: "find duplicate files" })} className="flex-1 nova-card p-3 text-xs tracking-widest uppercase hover:bg-[var(--nova-surface2)] transition-colors cursor-pointer text-center border border-[var(--nova-border)]">FIND DUPLICATES</button>
                <button onClick={() => post('/api/chat', { message: "analyze disk usage" })} className="flex-1 nova-card p-3 text-xs tracking-widest uppercase hover:bg-[var(--nova-surface2)] transition-colors cursor-pointer text-center border border-[var(--nova-border)]">ANALYZE DISK</button>
            </div>

            <div className="grid grid-cols-2 gap-6 flex-1 min-h-[400px]">
                {/* File Explorer */}
                <div className="nova-card p-4 flex flex-col gap-3">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase flex justify-between items-center">
                        <span>FILE EXPLORER</span>
                        <form onSubmit={handlePerformSearch} className="flex items-center">
                            <input
                                type="text"
                                placeholder="Search files..."
                                className="bg-transparent border-b border-[var(--nova-border)] outline-none text-[10px] text-[var(--nova-text)] px-1 py-0.5 w-32 focus:border-[var(--nova-accent)] focus:w-48 transition-all"
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                            />
                        </form>
                    </div>

                    <div className="flex items-center gap-2 bg-[var(--nova-surface2)] p-2 rounded text-[10px]">
                        <button onClick={navigateUp} className="text-[var(--nova-accent)] hover:underline cursor-pointer">↑ UP</button>
                        <span className="text-[var(--nova-muted)]">|</span>
                        <span className="truncate">{currentPath}</span>
                    </div>

                    <div className="flex-1 overflow-y-auto flex flex-col gap-1 pr-2">
                        {filesLoading ? (
                            <div className="text-xs text-[var(--nova-muted)] text-center py-4 animate-pulse">Scanning directory...</div>
                        ) : (
                            filesList.map((f, i) => (
                                <div key={i} onClick={() => handleFileClick(f)} className="flex items-center justify-between text-xs p-1.5 hover:bg-[var(--nova-surface2)] rounded cursor-pointer group">
                                    <div className="flex items-center gap-2 truncate">
                                        <span>{f.is_dir ? '📁' : '📄'}</span>
                                        <span className="truncate group-hover:text-[var(--nova-accent)] transition-colors">{f.name}</span>
                                    </div>
                                    <span className="text-[10px] text-[var(--nova-muted)] shrink-0 min-w-[50px] text-right">
                                        {f.is_dir ? '--' : `${f.size_kb} KB`}
                                    </span>
                                </div>
                            ))
                        )}
                        {!filesLoading && filesList.length === 0 && (
                            <div className="text-xs text-[var(--nova-muted)] text-center py-4">Directory empty</div>
                        )}
                    </div>
                </div>

                {/* Large Files */}
                <div className="nova-card p-4 flex flex-col gap-3">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase">LARGE FILES DETECTED</div>
                    <div className="flex-1 overflow-y-auto flex flex-col gap-1.5 pr-2">
                        {largeFiles.map((lf, i) => (
                            <div key={i} className="flex flex-col gap-1 border border-[var(--nova-surface2)] p-2 rounded text-xs bg-[var(--nova-bg)]">
                                <div className="flex justify-between items-center">
                                    <span className="font-bold truncate" title={lf.name}>📄 {lf.name}</span>
                                    <span className="text-[10px] text-[var(--nova-amber)] font-bold shrink-0">{lf.size_mb} MB</span>
                                </div>
                                <div className="text-[9px] text-[var(--nova-muted)] truncate">{lf.path}</div>
                                <div className="flex justify-end gap-3 mt-1.5 pt-1.5 border-t border-[var(--nova-surface2)] uppercase tracking-wider text-[9px]">
                                    <button onClick={() => post('/api/terminal', { command: `open -R "${lf.path}"` })} className="text-[var(--nova-text)] hover:underline cursor-pointer">OPEN</button>
                                    <button onClick={() => handleDeleteHighRisk(lf.path)} className="text-[var(--nova-red)] hover:underline cursor-pointer">DELETE</button>
                                </div>
                            </div>
                        ))}
                        {largeFiles.length === 0 && (
                            <div className="text-xs text-[var(--nova-muted)] text-center py-8">No large files taking up space</div>
                        )}
                    </div>
                </div>
            </div>

            {/* PREVIEW MODAL */}
            {previewContent !== null && (
                <div className="absolute inset-0 bg-black/80 flex flex-col p-10 z-50 backdrop-blur-sm">
                    <div className="flex justify-between items-center mb-4">
                        <span className="text-sm font-bold tracking-widest text-[var(--nova-accent)] uppercase">FILE PREVIEW</span>
                        <button onClick={() => setPreviewContent(null)} className="text-white hover:text-[var(--nova-red)] border border-white/20 hover:border-[var(--nova-red)] px-3 py-1 rounded text-xs cursor-pointer tracking-widest transition-colors">CLOSE</button>
                    </div>
                    <div className="flex-1 bg-[var(--nova-bg)] border border-[var(--nova-border)] rounded overflow-y-auto p-4 flex flex-col">
                        <pre className="text-[10px] text-[var(--nova-text)] font-mono whitespace-pre-wrap flex-1 opacity-90">
                            {previewContent}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
}
