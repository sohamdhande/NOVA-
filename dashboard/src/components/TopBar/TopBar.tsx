import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useNovaStore } from "../../store/novaStore";
import { API_BASE } from "../../api";

export function TopBar() {
    const { token, timeRemaining } = useAuth();
    const { metrics, setMetrics, systemStatus, setSystemStatus, setAutonomy } = useNovaStore();
    const [sessionSec, setSessionSec] = useState(timeRemaining());

    // Refresh session timer every second
    useEffect(() => {
        const iv = setInterval(() => setSessionSec(timeRemaining()), 1000);
        return () => clearInterval(iv);
    }, [timeRemaining]);

    // Poll metrics every 5s
    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/metrics`, {
                    headers: token ? { "Authorization": `Bearer ${token}` } : {},
                });
                if (res.ok) {
                    const d = await res.json();
                    setMetrics({
                        cpu: d.cpu,
                        ram: d.ram,
                        disk: d.disk,
                        battery: d.battery,
                        batteryCharging: d.battery_charging,
                    });
                }
            } catch { /* ignore */ }
        };
        fetchMetrics();
        const iv = setInterval(fetchMetrics, 5000);
        return () => clearInterval(iv);
    }, [setMetrics, token]);

    const sessionMin = Math.floor(sessionSec / 60);
    const sessionColor = sessionSec < 300 ? "text-[var(--nova-amber)]" : "text-[var(--nova-muted)]";

    const statusDot =
        systemStatus === "online"
            ? "bg-[var(--nova-green)] animate-pulse"
            : systemStatus === "paused"
                ? "bg-[var(--nova-amber)]"
                : "bg-[var(--nova-red)]";

    const handleToggle = async () => {
        const endpoint = systemStatus === "paused" ? "/api/nova/resume" : "/api/nova/pause";
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST" });
            if (res.ok) {
                const d = await res.json();
                setSystemStatus(d.autonomy ? "online" : "paused");
                setAutonomy(d.autonomy);
            }
        } catch { /* ignore */ }
    };

    function MiniBar({ label, value }: { label: string; value: number }) {
        const barColor = value > 85 ? "bg-[var(--nova-red)]" : value > 60 ? "bg-[var(--nova-amber)]" : "bg-[var(--nova-green)]";
        return (
            <div className="flex items-center gap-1.5">
                <span className="text-[9px] text-[var(--nova-muted)] uppercase">{label}</span>
                <div className="w-14 h-1.5 bg-[var(--nova-surface2)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${Math.min(value, 100)}%` }} />
                </div>
                <span className="text-[9px] text-[var(--nova-muted)] w-7 text-right">{value}%</span>
            </div>
        );
    }

    return (
        <div className="h-[52px] flex items-center justify-between px-4 bg-[var(--nova-bg)] border-b border-[var(--nova-border)] select-none shrink-0">
            {/* Left */}
            <div className="flex items-center gap-3">
                <span className="text-[var(--nova-accent)] font-mono font-bold tracking-[0.35em] text-sm">N · O · V · A</span>
                <span className="text-[9px] text-[var(--nova-muted)] tracking-wider">v4.0</span>
            </div>

            {/* Center */}
            <div className="flex items-center gap-3 text-[10px] font-mono tracking-wider uppercase">
                <div className={`w-2 h-2 rounded-full ${statusDot}`} />
                <span className="text-[var(--nova-text)]">SYSTEM {systemStatus.toUpperCase()}</span>
                <span className="text-[var(--nova-border)]">│</span>
                <span className="text-[var(--nova-muted)]">MODE API_SERVER</span>
                <span className="text-[var(--nova-border)]">│</span>
                <span className="text-[var(--nova-muted)]">MODEL mistral:7b</span>
            </div>

            {/* Right */}
            <div className="flex items-center gap-4">
                <MiniBar label="CPU" value={metrics.cpu} />
                <MiniBar label="RAM" value={metrics.ram} />

                {/* Battery */}
                <div className="flex items-center gap-1">
                    <span className="text-[9px] text-[var(--nova-muted)] uppercase">BAT</span>
                    <span className={`text-[9px] ${metrics.battery < 30 ? "text-[var(--nova-amber)]" : metrics.batteryCharging ? "text-[var(--nova-green)]" : "text-[var(--nova-muted)]"}`}>
                        {metrics.battery}%{metrics.batteryCharging ? " ⚡" : ""}
                    </span>
                </div>

                <span className="text-[var(--nova-border)]">│</span>

                {/* Session timer */}
                <span className={`text-[10px] font-mono tracking-wider ${sessionColor}`}>
                    SESSION {sessionMin}m
                </span>

                <span className="text-[var(--nova-border)]">│</span>

                {/* Pause / Resume */}
                <button
                    onClick={handleToggle}
                    className={`text-[10px] font-mono tracking-wider px-2 py-1 rounded border transition-colors ${systemStatus === "paused"
                        ? "text-[var(--nova-amber)] border-[var(--nova-amber)]/30 hover:bg-[var(--nova-amber)]/10"
                        : "text-[var(--nova-accent)] border-[var(--nova-accent)]/30 hover:bg-[var(--nova-accent)]/10"
                        }`}
                >
                    {systemStatus === "paused" ? "▶ RESUME" : "⏸ PAUSE"}
                </button>
            </div>
        </div>
    );
}
