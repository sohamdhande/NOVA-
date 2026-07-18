import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../../hooks/useApi";
import { ChronicleOverview } from "./ChronicleOverview";
import { DailyChronicleReport, type ReportData } from "./DailyChronicleReport";
import { KnowledgeHealthSection, type HealthData } from "./KnowledgeHealthSection";
import { EvolutionSection } from "./EvolutionSection";

interface HomeStatsData {
    stats: { commits: number; artifacts: number; entities: number; observations: number; compiler_status: string };
    recent_commits: { hash: string; short_hash: string; timestamp: string; summary: string }[];
    recent_entities: { id: string; name: string }[];
}

interface Props {
    onInspect: (id: string) => void;
    onNavigate: (view: string) => void;
}

export function HomeView({ onInspect, onNavigate }: Props) {
    const { get } = useApi();
    const [stats, setStats] = useState<HomeStatsData | null>(null);
    const [report, setReport] = useState<ReportData | null>(null);
    const [health, setHealth] = useState<HealthData | null>(null);
    const [window, setWindow] = useState("today");
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [stRes, hlthRes, repRes] = await Promise.all([
                get<HomeStatsData>("/api/knowledge/stats"),
                get<HealthData>("/api/knowledge/health"),
                get<ReportData>(`/api/knowledge/report?window=${window}`)
            ]);
            setStats(stRes);
            setHealth(hlthRes);
            setReport(repRes);
        } catch { /* ignore */ }
        finally { setLoading(false); }
    }, [get, window]);

    useEffect(() => { load(); }, [load]);

    if (loading && !stats) return <div className="p-4 text-xs font-mono text-[var(--nova-muted)] animate-pulse">Loading Chronicle Home...</div>;
    if (!stats || !stats.stats) return (
        <div className="p-4 text-xs font-mono text-[var(--nova-red)]">
            Failed to connect to Chronicle Runtime (Server responded 404 or 500). Please restart backend server.
        </div>
    );

    return (
        <div className="flex flex-col h-full space-y-4 overflow-y-auto pr-1 font-mono">
            <ChronicleOverview stats={stats.stats} snapshot={(report as any)?.snapshot} onNavigate={onNavigate} />
            <DailyChronicleReport report={report} window={window} onWindowChange={(w) => setWindow(w)} onInspect={onInspect} />
            <KnowledgeHealthSection health={health} onInspect={onInspect} />
            <EvolutionSection evolution={(report as any)?.memory_evolution} recent_commits={stats.recent_commits} recent_entities={stats.recent_entities} onInspect={onInspect} onNavigate={onNavigate} />
        </div>
    );
}
