import { useNovaStore } from "../../store/novaStore";

const NAV_ITEMS = [
    { icon: "⌂", label: "HQ", key: "hq" },
    { icon: "⬛", label: "TERMINAL", key: "terminal" },
    { icon: "✓", label: "TASKS", key: "tasks" },
    { icon: "⚡", label: "AUTOMATIONS", key: "automations" },
    { icon: "📊", label: "MONITOR", key: "monitor" },
    { icon: "🔐", label: "APPROVALS", key: "approvals" },
    { icon: "💬", label: "COMMS", key: "comms" },
    { icon: "🧠", label: "MEMORY", key: "memory" },
    { icon: "🔧", label: "SKILLS", key: "skills" },
    { icon: "👁", label: "REASONING", key: "reasoning" },
    { icon: "📈", label: "PRODUCTIVITY", key: "productivity" },
    { icon: "📁", label: "FILES", key: "files" },
    { icon: "🌐", label: "BROWSER", key: "browser" },
    { icon: "🛡", label: "SECURITY", key: "security" },
    { icon: "⚙️", label: "SETTINGS", key: "settings" },
];

export function Sidebar() {
    const { activePanel, setActivePanel, pendingApprovals } = useNovaStore();

    return (
        <div className="w-[200px] shrink-0 h-full bg-[var(--nova-bg)] border-r border-[var(--nova-border)] flex flex-col select-none">
            {/* Logo */}
            <div className="h-12 flex items-center justify-center">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-[var(--nova-accent)]">
                    <path d="M10 0L20 10L10 20L0 10Z" fill="currentColor" opacity="0.8" />
                    <path d="M10 4L16 10L10 16L4 10Z" fill="var(--nova-bg)" />
                    <path d="M10 6L14 10L10 14L6 10Z" fill="currentColor" opacity="0.4" />
                </svg>
            </div>

            {/* Nav items */}
            <nav className="flex-1 overflow-y-auto py-1">
                {NAV_ITEMS.map((item) => {
                    const active = activePanel === item.key;
                    return (
                        <button
                            key={item.key}
                            onClick={() => setActivePanel(item.key)}
                            className={`w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors relative ${active
                                    ? "text-[var(--nova-accent)] bg-[rgba(0,255,204,0.05)]"
                                    : "text-[var(--nova-muted)] hover:text-[var(--nova-text)] hover:bg-white/[0.02]"
                                }`}
                        >
                            {/* Active indicator */}
                            {active && (
                                <div className="absolute left-0 top-1 bottom-1 w-0.5 bg-[var(--nova-accent)] rounded-r" />
                            )}

                            <span className="text-sm w-5 text-center">{item.icon}</span>
                            <span className="text-[10px] font-mono tracking-[0.15em] uppercase">{item.label}</span>

                            {/* Approval badge */}
                            {item.key === "approvals" && pendingApprovals > 0 && (
                                <span className="ml-auto text-[8px] bg-[var(--nova-red)] text-white rounded-full w-4 h-4 flex items-center justify-center font-bold">
                                    {pendingApprovals}
                                </span>
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="px-3 py-3 border-t border-[var(--nova-border)]">
                <div className="text-[8px] font-mono text-[var(--nova-muted)] tracking-wider uppercase">NOVA v4.0</div>
            </div>
        </div>
    );
}
