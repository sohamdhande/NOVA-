import { useNovaStore } from "../store/novaStore";
import { TopBar } from "../components/TopBar/TopBar";
import { Sidebar } from "../components/Sidebar/Sidebar";
import { PlaceholderPanel } from "../components/panels/PlaceholderPanel";
import { HQPanel } from "../components/panels/HQPanel";
import { MonitorPanel } from "../components/panels/MonitorPanel";
import { TasksPanel } from "../components/panels/TasksPanel";
import { AutomationsPanel } from "../components/panels/AutomationsPanel";

const PANELS: Record<string, { title: string; description: string; icon: string }> = {
    hq: { title: "COMMAND CENTER", description: "Central HQ overview with live system feed", icon: "⌂" },
    terminal: { title: "TERMINAL BRIDGE", description: "Execute and monitor terminal commands", icon: "⬛" },
    tasks: { title: "TASKS & GOALS", description: "Track objectives and daily progress", icon: "✓" },
    automations: { title: "AUTOMATION LIBRARY", description: "Manage system and productivity automations", icon: "⚡" },
    monitor: { title: "SYSTEM MONITOR", description: "Real-time hardware and process metrics", icon: "📊" },
    approvals: { title: "APPROVAL PANEL", description: "Review and approve high-risk actions", icon: "🔐" },
    comms: { title: "COMMS HUB", description: "Email, Slack, and WhatsApp integration", icon: "💬" },
    memory: { title: "MEMORY VIEWER", description: "Events, decisions, and reflections log", icon: "🧠" },
    skills: { title: "SKILLS MODULE", description: "Install and manage N.O.V.A skill plugins", icon: "🔧" },
    reasoning: { title: "AI REASONING", description: "Inspect the inference pipeline and plans", icon: "👁" },
    productivity: { title: "PRODUCTIVITY", description: "Coding hours, focus sessions, and scores", icon: "📈" },
    files: { title: "FILE SYSTEM", description: "Downloads, duplicates, and cleanup tools", icon: "📁" },
    browser: { title: "BROWSER PANEL", description: "Headless browser automation control", icon: "🌐" },
    security: { title: "SECURITY", description: "Command whitelist, blocked actions, audit", icon: "🛡" },
    settings: { title: "SETTINGS", description: "Configure intervals, thresholds, and model", icon: "⚙️" },
};

function ActivePanel({ panelKey }: { panelKey: string }) {
    switch (panelKey) {
        case "hq": return <HQPanel />;
        case "monitor": return <MonitorPanel />;
        case "tasks": return <TasksPanel />;
        case "automations": return <AutomationsPanel />;
        default: {
            const panel = PANELS[panelKey] ?? PANELS.hq;
            return <PlaceholderPanel title={panel.title} description={panel.description} icon={panel.icon} />;
        }
    }
}

export function DashboardLayout() {
    const { activePanel } = useNovaStore();

    return (
        <div className="flex flex-col h-screen w-screen overflow-hidden bg-[var(--nova-bg)]">
            <TopBar />
            <div className="flex flex-1 overflow-hidden">
                <Sidebar />
                <main className="flex-1 overflow-y-auto">
                    <ActivePanel panelKey={activePanel} />
                </main>
            </div>
        </div>
    );
}
