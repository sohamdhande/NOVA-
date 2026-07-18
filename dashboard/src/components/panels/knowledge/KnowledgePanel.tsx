import { useState, useCallback } from "react";
import { useApi } from "../../../hooks/useApi";
import { InspectorCard } from "./InspectorCard";
import { HomeView } from "./HomeView";
import { NewArtifactView } from "./NewArtifactView";
import { SettingsView } from "./SettingsView";
import { ExplorerView } from "./ExplorerView";
import { SearchView } from "./SearchView";
import { TimelineView } from "./TimelineView";
import { ListView } from "./ListView";
import { ReasoningView } from "./ReasoningView";
import { ExplainView } from "./ExplainView";
import { IntegrityView } from "./IntegrityView";
import { MasterReportView } from "./MasterReportView";

type SubView =
    | "home" | "integrity" | "new_artifact" | "explorer" | "timeline" | "search"
    | "commits" | "reasoning" | "explain" | "settings" | "master_report"
    | "artifacts" | "observations" | "entities" | "relationships";

const NAV_ITEMS: { key: SubView; label: string; icon: string }[] = [
    { key: "home", label: "Home", icon: "⌂" },
    { key: "integrity", label: "Integrity", icon: "⎈" },
    { key: "master_report", label: "Master Report", icon: "📄" },
    { key: "new_artifact", label: "New Artifact", icon: "📥" },
    { key: "explorer", label: "Explorer", icon: "◈" },
    { key: "timeline", label: "Timeline", icon: "◷" },
    { key: "search", label: "Search", icon: "⌕" },
    { key: "commits", label: "Commits", icon: "⊞" },
    { key: "reasoning", label: "Reasoning", icon: "⚙" },
    { key: "explain", label: "Provenance", icon: "⥮" },
    { key: "settings", label: "Settings", icon: "❖" },
];

interface InspectData {
    object_type: string;
    id: string;
    summary: string;
    metadata: Record<string, unknown>;
    relationships: { target: string; relation: string }[];
    timeline: { timestamp: string; event: string }[];
    provenance: string[];
    supporting_evidence: string[];
    related_commits: string[];
}

export function KnowledgePanel() {
    const { get } = useApi();
    const [activeView, setActiveView] = useState<SubView>("home");
    const [inspecting, setInspecting] = useState<InspectData | null>(null);
    const [inspectLoading, setInspectLoading] = useState(false);

    const handleInspect = useCallback(async (id: string) => {
        if (!id) return;
        setInspectLoading(true);
        try {
            const data = await get<InspectData>(`/api/knowledge/inspect/${encodeURIComponent(id)}`);
            setInspecting(data);
        } catch {
            setInspecting(null);
        } finally {
            setInspectLoading(false);
        }
    }, [get]);

    const handleNavigate = (view: string) => {
        setActiveView(view as SubView);
        setInspecting(null);
    };

    const clearInspect = () => setInspecting(null);

    return (
        <div className="h-full flex flex-col p-4 overflow-hidden select-none">
            {/* Panel header */}
            <div className="flex items-center justify-between mb-4 shrink-0">
                <div className="flex items-center gap-3">
                    <h1 className="text-lg font-mono tracking-[0.3em] text-[var(--nova-accent)] drop-shadow-[0_0_8px_rgba(0,255,204,0.4)]">CHRONICLE</h1>
                    <span className="text-[9px] font-mono text-[var(--nova-muted)] tracking-wider bg-[var(--nova-surface2)] px-2 py-0.5 rounded border border-[var(--nova-border)]">IMMUTABLE</span>
                </div>
                {inspecting && (
                    <button
                        onClick={clearInspect}
                        className="text-[9px] font-mono text-[var(--nova-muted)] hover:text-[var(--nova-accent)] transition-colors px-2 py-1 border border-[var(--nova-border)] rounded"
                    >
                        ✕ Close Inspector
                    </button>
                )}
            </div>

            {/* Two-column workspace */}
            <div className="flex flex-1 gap-3 min-h-0 overflow-hidden">
                {/* Left sub-nav */}
                <div className="w-[160px] shrink-0 flex flex-col gap-0.5 overflow-y-auto">
                    {NAV_ITEMS.map(item => {
                        const active = activeView === item.key;
                        return (
                            <button
                                key={item.key}
                                onClick={() => handleNavigate(item.key)}
                                className={`flex items-center gap-2 px-3 py-2 rounded text-left transition-colors relative ${
                                    active
                                        ? "text-[var(--nova-accent)] bg-[rgba(0,255,204,0.05)] border border-[var(--nova-accent)]/20 font-bold"
                                        : "text-[var(--nova-muted)] hover:text-[var(--nova-text)] hover:bg-white/[0.02] border border-transparent"
                                }`}
                            >
                                <span className="text-xs w-4 text-center font-mono">{item.icon}</span>
                                <span className="text-[10px] font-mono tracking-[0.1em] uppercase">{item.label}</span>
                            </button>
                        );
                    })}
                </div>

                {/* Right content */}
                <div className="flex-1 flex gap-3 min-h-0 overflow-hidden">
                    {/* Main sub-view */}
                    <div className={`${inspecting ? "flex-1" : "w-full"} overflow-y-auto transition-all`}>
                        {activeView === "home" && <HomeView onInspect={handleInspect} onNavigate={handleNavigate} />}
                        {activeView === "integrity" && <IntegrityView onInspect={handleInspect} />}
                        {activeView === "master_report" && <MasterReportView />}
                        {activeView === "new_artifact" && <NewArtifactView onInspect={handleInspect} onNavigate={handleNavigate} />}
                        {activeView === "settings" && <SettingsView />}
                        {activeView === "explorer" && <ExplorerView onInspect={handleInspect} />}
                        {activeView === "search" && <SearchView onInspect={handleInspect} />}
                        {activeView === "timeline" && <TimelineView onInspect={handleInspect} />}
                        {activeView === "reasoning" && <ReasoningView />}
                        {activeView === "explain" && <ExplainView onInspect={handleInspect} />}
                        {activeView === "artifacts" && (
                            <ListView title="Artifacts" endpoint="/api/knowledge/artifacts" columns={[{ key: "id", label: "Path", truncate: true }, { key: "type", label: "Type" }, { key: "content", label: "Content", truncate: true }]} idKey="id" onInspect={handleInspect} />
                        )}
                        {activeView === "observations" && (
                            <ListView title="Observations" endpoint="/api/knowledge/observations" columns={[{ key: "id", label: "ID", truncate: true }, { key: "dialect", label: "Dialect" }, { key: "op", label: "Op" }, { key: "content", label: "Content", truncate: true }]} idKey="id" onInspect={handleInspect} />
                        )}
                        {activeView === "entities" && (
                            <ListView title="Entities" endpoint="/api/knowledge/entities" columns={[{ key: "id", label: "Entity ID" }, { key: "name", label: "Name" }]} idKey="id" onInspect={handleInspect} />
                        )}
                        {activeView === "relationships" && (
                            <ListView title="Relationships" endpoint="/api/knowledge/relationships" columns={[{ key: "source", label: "Source", truncate: true }, { key: "relation", label: "Relation" }, { key: "target", label: "Target", truncate: true }]} idKey="source" onInspect={handleInspect} />
                        )}
                        {activeView === "commits" && (
                            <ListView title="Knowledge Commits" endpoint="/api/knowledge/commits" columns={[{ key: "short_hash", label: "Hash" }, { key: "timestamp", label: "Timestamp" }, { key: "dialect", label: "Dialect" }, { key: "op", label: "Op" }, { key: "summary", label: "Summary", truncate: true }]} idKey="hash" onInspect={handleInspect} />
                        )}
                    </div>

                    {/* Inspector side panel */}
                    {(inspecting || inspectLoading) && (
                        <div className="w-[400px] shrink-0 overflow-y-auto">
                            {inspectLoading ? (
                                <div className="bg-[var(--nova-surface)] border border-[var(--nova-border)] rounded-lg p-4 animate-pulse">
                                    <div className="h-4 bg-[var(--nova-surface2)] rounded w-1/3 mb-3" />
                                    <div className="h-3 bg-[var(--nova-surface2)] rounded w-2/3 mb-2" />
                                    <div className="h-3 bg-[var(--nova-surface2)] rounded w-1/2" />
                                </div>
                            ) : inspecting ? (
                                <InspectorCard data={inspecting} onNavigate={handleInspect} />
                            ) : null}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
