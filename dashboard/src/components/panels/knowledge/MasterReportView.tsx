import React, { useState, useEffect } from "react";
import { useApi } from "../../../hooks/useApi";

interface MasterReportStatus {
    report_hash: string;
    generated_at: string;
    sections_rerendered: string[];
    sections_from_cache: string[];
}

export function MasterReportView() {
    const { get, apiFetch } = useApi();
    const [status, setStatus] = useState<MasterReportStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);
    const [pdfLoading, setPdfLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchStatus = async () => {
        try {
            setLoading(true);
            const data = await get<MasterReportStatus>("/api/knowledge/master-report/status");
            setStatus(data);
            setError(null);
        } catch (err: any) {
            setError(err.message || "Failed to fetch master report status");
        } finally {
            setLoading(false);
        }
    };

    const fetchPdf = async () => {
        try {
            setPdfLoading(true);
            const response = await apiFetch("/api/knowledge/master-report");
            if (!response.ok) throw new Error("Failed to generate PDF");
            
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            setPdfUrl(url);
            setError(null);
            
            // Refresh status after PDF generation in case new sections were cached
            fetchStatus();
        } catch (err: any) {
            setError(err.message || "Failed to fetch master report PDF");
        } finally {
            setPdfLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        fetchPdf();
        
        return () => {
            if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleRegenerate = () => {
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(null);
        fetchPdf();
    };

    if (loading && !status && !pdfUrl) {
        return (
            <div className="h-full flex items-center justify-center text-[var(--nova-muted)] font-mono text-sm">
                Generating Master Report...
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col gap-4">
            <div className="flex items-center justify-between shrink-0">
                <div>
                    <h2 className="text-lg font-mono text-[var(--nova-text)] tracking-wider">MASTER REPORT</h2>
                    {status && (
                        <p className="text-xs text-[var(--nova-muted)] font-mono mt-1">
                            Last generated: {new Date(status.generated_at).toLocaleString()}
                        </p>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleRegenerate}
                        disabled={pdfLoading}
                        className="px-3 py-1.5 bg-[var(--nova-surface2)] hover:bg-[var(--nova-surface3)] text-[var(--nova-text)] border border-[var(--nova-border)] rounded text-xs font-mono disabled:opacity-50 transition-colors"
                    >
                        {pdfLoading ? "Generating..." : "Regenerate"}
                    </button>
                    {pdfUrl && (
                        <a
                            href={pdfUrl}
                            download={`master-report-${new Date().toISOString().split("T")[0]}.pdf`}
                            className="px-3 py-1.5 bg-[rgba(0,255,204,0.1)] hover:bg-[rgba(0,255,204,0.2)] text-[var(--nova-accent)] border border-[var(--nova-accent)]/30 rounded text-xs font-mono transition-colors"
                        >
                            Download PDF
                        </a>
                    )}
                </div>
            </div>

            {error && (
                <div className="p-3 bg-red-900/20 border border-red-500/30 rounded text-red-400 text-sm font-mono shrink-0">
                    {error}
                </div>
            )}

            {status && (
                <div className="flex gap-4 shrink-0 text-xs font-mono">
                    <div className="px-3 py-2 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded flex-1">
                        <span className="text-[var(--nova-muted)] block mb-1">Freshly Rendered Sections</span>
                        <span className="text-[var(--nova-text)]">{status.sections_rerendered.length || "None (Fully Cached)"}</span>
                    </div>
                    <div className="px-3 py-2 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded flex-1">
                        <span className="text-[var(--nova-muted)] block mb-1">Sections from Cache</span>
                        <span className="text-[var(--nova-text)]">{status.sections_from_cache.length}</span>
                    </div>
                    <div className="px-3 py-2 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded flex-1">
                        <span className="text-[var(--nova-muted)] block mb-1">Hash</span>
                        <span className="text-[var(--nova-text)] truncate block" title={status.report_hash}>
                            {status.report_hash.substring(0, 12)}...
                        </span>
                    </div>
                </div>
            )}

            <div className="flex-1 bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded overflow-hidden relative">
                {pdfLoading ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-[var(--nova-surface)]/50 backdrop-blur-sm z-10">
                        <span className="text-[var(--nova-accent)] font-mono text-sm animate-pulse">
                            Assembling PDF Document...
                        </span>
                    </div>
                ) : null}
                
                {pdfUrl ? (
                    <iframe
                        src={pdfUrl}
                        className="w-full h-full border-0"
                        title="Master Report PDF"
                    />
                ) : !pdfLoading && !error ? (
                    <div className="h-full flex items-center justify-center text-[var(--nova-muted)] font-mono text-sm">
                        PDF not available
                    </div>
                ) : null}
            </div>
        </div>
    );
}
