import { useState } from "react";
import { useApi } from "../../../hooks/useApi";

export function SettingsView() {
    const { get, post } = useApi();
    const [loading, setLoading] = useState(false);
    const [notice, setNotice] = useState("");

    const handleExport = async () => {
        setLoading(true);
        try {
            const data = await get<unknown[]>("/api/knowledge/export");
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `nova_knowledge_export_${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
            setNotice("Chronicle export downloaded successfully.");
        } catch {
            setNotice("Export failed.");
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        if (!confirm("Are you sure you want to reset local knowledge? This drops all compiled commits.")) return;
        setLoading(true);
        try {
            const res = await post<{ message: string }>("/api/knowledge/reset", {});
            setNotice(res.message);
        } catch {
            setNotice("Reset failed.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full space-y-6 overflow-y-auto pr-1 font-mono">
            <div>
                <h2 className="text-xs tracking-widest text-[var(--nova-accent)] uppercase">Chronicle User Settings</h2>
                <p className="text-[10px] text-[var(--nova-muted)] mt-0.5">Personal knowledge workspace preferences. Compiler internals (NAS-001..011) remain permanently locked.</p>
            </div>

            {notice && <div className="p-3 bg-[var(--nova-accent)]/10 border border-[var(--nova-accent)]/30 rounded text-xs text-[var(--nova-accent)]">{notice}</div>}



            {/* Data Management */}
            <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-4 space-y-4 max-w-xl">
                <h3 className="text-[10px] tracking-wider text-[var(--nova-muted)] uppercase">Data Governance & Portability</h3>

                <div className="flex items-center justify-between">
                    <div>
                        <span className="text-xs text-[var(--nova-text)] block">Export Compiled Knowledge</span>
                        <span className="text-[9px] text-[var(--nova-muted)]">Download complete commit ledger and KIR nodes as JSON.</span>
                    </div>
                    <button onClick={handleExport} disabled={loading} className="px-4 py-1.5 bg-[var(--nova-surface2)] border border-[var(--nova-border)] text-xs text-[var(--nova-text)] rounded hover:border-[var(--nova-accent)] transition-all">
                        ⬇ Export JSON
                    </button>
                </div>

                <hr className="border-[var(--nova-border)]/50" />

                <div className="flex items-center justify-between">
                    <div>
                        <span className="text-xs text-[var(--nova-red)] block">Reset Local Knowledge</span>
                        <span className="text-[9px] text-[var(--nova-muted)]">Purge local SQLite commit database. Cannot be undone.</span>
                    </div>
                    <button onClick={handleReset} disabled={loading} className="px-4 py-1.5 bg-[var(--nova-red)]/10 border border-[var(--nova-red)]/40 text-xs text-[var(--nova-red)] rounded hover:bg-[var(--nova-red)] hover:text-black font-bold transition-all">
                        ⚠ Reset Local Knowledge
                    </button>
                </div>
            </div>
        </div>
    );
}
