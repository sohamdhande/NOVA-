import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../hooks/useApi";
import { useNovaStore } from "../../store/novaStore";

function Skeleton() {
    return <div className="nova-card animate-pulse h-16" />;
}

export function SettingsPanel() {
    const { get, post } = useApi();
    const { addToast } = useNovaStore();

    const [settings, setSettings] = useState<any>({});
    const [modelName, setModelName] = useState("llama3.2");

    // Notifications toggles
    const [notifs, setNotifs] = useState({
        system_alerts: true,
        email_notifications: false,
        slack_notifications: true,
        task_reminders: true
    });

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState(new Date());

    const fetchData = useCallback(async () => {
        try {
            const res = await get<any>('/api/settings').catch(() => ({
                interval_reasoning: 60,
                threshold_battery: 15,
                interval_telemetry: 300,
                retention_log: 30,
                notifs: {
                    system_alerts: true,
                    email_notifications: false,
                    slack_notifications: true,
                    task_reminders: true
                }
            }));

            setSettings({
                interval_reasoning: res.interval_reasoning || 60,
                threshold_battery: res.threshold_battery || 15,
                interval_telemetry: res.interval_telemetry || 300,
                retention_log: res.retention_log || 30,
            });

            if (res.notifs) setNotifs(res.notifs);

            setError("");
            setLastUpdated(new Date());
        } catch (e: any) {
            setError(e.message || "Failed to fetch settings");
        } finally {
            setLoading(false);
        }
    }, [get]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleSaveSetting = async (key: string, value: number) => {
        try {
            await post('/api/settings', { [key]: value });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Setting updated successfully' });
        } catch {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to update setting' });
        }
    };

    const handleUpdateModel = async () => {
        if (!modelName) return;
        try {
            await post('/api/settings/model', { model: modelName });
            addToast({ id: crypto.randomUUID(), type: 'success', message: 'Model updated in .env' });
        } catch {
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Failed to update model' });
        }
    };

    const handleNotifToggle = async (key: keyof typeof notifs) => {
        const newVal = !notifs[key];
        setNotifs(p => ({ ...p, [key]: newVal }));
        try {
            await post('/api/settings/notifications', { [key]: newVal });
        } catch {
            setNotifs(p => ({ ...p, [key]: !newVal }));
            addToast({ id: crypto.randomUUID(), type: 'error', message: 'Sync failed' });
        }
    };

    const handleDangerAction = async (action: string) => {
        let msg = "";
        if (action === "MEMORY") msg = "clear all system memory? This is irreversible.";
        if (action === "RESET") msg = "reset all parameters to defaults?";
        if (action === "SHUTDOWN") msg = "shutdown N.O.V.A engine completely?";

        if (!window.confirm(`Are you sure you want to ${msg}`)) return;

        try {
            if (action === "SHUTDOWN") {
                await post('/api/nova/shutdown', {});
                addToast({ id: crypto.randomUUID(), type: 'info', message: 'Shutdown sequence initiated...' });
            } else if (action === "MEMORY") {
                await post('/api/terminal', { command: "rm -f nova_logs.db*" });
                addToast({ id: crypto.randomUUID(), type: 'success', message: 'Memory wiped successfully' });
            } else if (action === "RESET") {
                addToast({ id: crypto.randomUUID(), type: 'success', message: 'Settings reset' });
            }
        } catch {
            addToast({ id: crypto.randomUUID(), type: 'error', message: `Action ${action} failed` });
        }
    };

    if (loading) return <div className="p-6 space-y-4"><Skeleton /><Skeleton /></div>;

    const InputRow = ({ label, objKey, suffix }: { label: string, objKey: string, suffix: string }) => {
        const [val, setVal] = useState(settings[objKey]?.toString() || "");
        return (
            <div className="flex items-center justify-between text-xs p-2 hover:bg-[var(--nova-surface2)] rounded transition-colors group">
                <span className="uppercase tracking-wider text-[var(--nova-muted)] group-hover:text-[var(--nova-text)] flex-1">{label}</span>
                <div className="flex items-center gap-3">
                    <div className="flex items-center bg-black/40 border border-[var(--nova-border)] rounded overflow-hidden">
                        <input
                            type="number"
                            className="bg-transparent text-center w-16 p-1.5 outline-none text-[var(--nova-accent)] font-bold text-xs"
                            value={val}
                            onChange={(e) => setVal(e.target.value)}
                        />
                        <span className="text-[10px] text-[var(--nova-muted)] pr-2 bg-black/40 h-full flex items-center">{suffix}</span>
                    </div>
                    <button
                        onClick={() => handleSaveSetting(objKey, parseInt(val))}
                        className="text-[10px] tracking-widest text-black bg-[var(--nova-accent)] px-3 py-1.5 rounded font-bold hover:opacity-80 transition-opacity cursor-pointer"
                    >
                        SAVE
                    </button>
                </div>
            </div>
        );
    };

    return (
        <div className="h-full overflow-y-auto p-6 bg-[var(--nova-bg)] font-mono text-[var(--nova-text)] flex flex-col gap-6">
            <div className="flex justify-between items-center text-xs">
                <h1 className="tracking-[0.3em] uppercase text-[var(--nova-accent)] font-bold">SYSTEM SETTINGS</h1>
                <div className="text-[var(--nova-muted)] flex items-center gap-3">
                    <span>UPDATED {lastUpdated.toLocaleTimeString()}</span>
                    <button onClick={fetchData} className="hover:text-[var(--nova-accent)] cursor-pointer">⟳</button>
                </div>
            </div>

            {error && <div className="text-[var(--nova-red)] text-xs border border-[var(--nova-red)] p-3 rounded">{error}</div>}

            <div className="grid grid-cols-2 gap-6">
                {/* SYSTEM CONFIG */}
                <div className="nova-card p-4 flex flex-col gap-4">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase font-bold">SYSTEM CONFIG</div>
                    <div className="flex flex-col gap-2">
                        <InputRow label="REASONING INTERVAL" objKey="interval_reasoning" suffix="minutes" />
                        <InputRow label="BATTERY THRESHOLD" objKey="threshold_battery" suffix="%" />
                        <InputRow label="TELEMETRY INTERVAL" objKey="interval_telemetry" suffix="seconds" />
                        <InputRow label="LOG RETENTION" objKey="retention_log" suffix="days" />
                    </div>
                </div>

                {/* ABOUT CARD */}
                <div className="nova-card p-4 flex flex-col gap-4 bg-black/50 overflow-hidden relative border-[var(--nova-surface2)]">
                    <div className="absolute -right-10 -top-10 text-[var(--nova-surface2)] opacity-30 select-none">
                        <span className="text-[150px] font-bold leading-none">N</span>
                    </div>
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase font-bold relative z-10">ABOUT N.O.V.A</div>
                    <div className="flex flex-col gap-3 text-xs relative z-10 h-full justify-center">
                        <div className="flex justify-between border-b border-[var(--nova-surface2)] py-1">
                            <span className="text-[var(--nova-muted)]">Version:</span><span className="text-[var(--nova-accent)] font-bold tracking-widest">v4.0</span>
                        </div>
                        <div className="flex justify-between border-b border-[var(--nova-surface2)] py-1">
                            <span className="text-[var(--nova-muted)]">Engine:</span><span className="text-white">llama3.2</span>
                        </div>
                        <div className="flex justify-between border-b border-[var(--nova-surface2)] py-1">
                            <span className="text-[var(--nova-muted)]">Uptime:</span><span className="text-white">Calculating...</span>
                        </div>
                        <div className="flex justify-between py-1">
                            <span className="text-[var(--nova-muted)]">Build Date:</span><span className="text-white">{new Date().toLocaleDateString()}</span>
                        </div>
                        <div className="mt-4 pt-4 border-t border-[var(--nova-surface2)] text-[10px] text-[var(--nova-muted)] flex flex-col gap-1 text-center">
                            <span>N.O.V.A — Neural Operational Virtual Assistant</span>
                            <span>Running on macOS</span>
                        </div>
                    </div>
                </div>

                {/* AI MODEL CONFIG */}
                <div className="nova-card p-4 flex flex-col gap-4">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase font-bold">AI MODEL</div>
                    <div className="flex flex-col gap-4 justify-center flex-1">
                        <div className="flex items-center gap-4">
                            <span className="text-xs uppercase tracking-wider text-[var(--nova-muted)] w-24">CURRENT</span>
                            <input
                                type="text"
                                value={modelName}
                                onChange={e => setModelName(e.target.value)}
                                className="flex-1 bg-[var(--nova-surface2)] border border-[var(--nova-border)] text-xs p-2 outline-none rounded text-white"
                            />
                        </div>
                        <button onClick={handleUpdateModel} className="self-end bg-transparent border border-[var(--nova-accent)] text-[var(--nova-accent)] text-[10px] px-6 py-2 rounded font-bold tracking-widest hover:bg-[var(--nova-accent)] hover:text-black transition-colors cursor-pointer">
                            UPDATE MODEL
                        </button>
                    </div>
                </div>

                {/* NOTIFICATIONS */}
                <div className="nova-card p-4 flex flex-col gap-4">
                    <div className="text-[10px] text-[var(--nova-muted)] tracking-widest border-b border-[var(--nova-border)] pb-2 uppercase font-bold">NOTIFICATIONS</div>
                    <div className="flex flex-col gap-3 py-2">
                        {(Object.keys(notifs) as Array<keyof typeof notifs>).map(key => (
                            <div key={key} className="flex justify-between items-center text-xs p-2 hover:bg-[var(--nova-surface2)] rounded transition-colors group">
                                <span className="uppercase tracking-wider text-[var(--nova-muted)] group-hover:text-[var(--nova-text)] flex-1">
                                    {key.replace('_', ' ')}
                                </span>
                                <button
                                    onClick={() => handleNotifToggle(key)}
                                    className={`px-4 py-1.5 text-[10px] font-bold tracking-widest rounded transition-colors cursor-pointer w-16 text-center ${notifs[key] ? 'bg-[var(--nova-green)] text-black' : 'bg-black/40 border border-[var(--nova-border)] text-[var(--nova-muted)]'}`}
                                >
                                    {notifs[key] ? 'ON' : 'OFF'}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* DANGER ZONE */}
                <div className="col-span-2 nova-card p-4 flex flex-col gap-4 border border-[var(--nova-red)]/40 bg-black/20">
                    <div className="text-[10px] text-[var(--nova-red)] tracking-widest border-b border-[var(--nova-red)]/30 pb-2 uppercase font-bold text-center">DANGER ZONE</div>
                    <div className="flex gap-6 pt-2">
                        <button
                            onClick={() => handleDangerAction("MEMORY")}
                            className="flex-1 border border-[var(--nova-red)]/60 text-[var(--nova-red)] hover:bg-[var(--nova-red)] hover:text-white p-3 rounded text-[10px] font-bold tracking-[0.2em] uppercase transition-colors cursor-pointer"
                        >
                            CLEAR ALL MEMORY
                        </button>
                        <button
                            onClick={() => handleDangerAction("RESET")}
                            className="flex-1 border border-[var(--nova-red)]/60 text-[var(--nova-red)] hover:bg-[var(--nova-red)] hover:text-white p-3 rounded text-[10px] font-bold tracking-[0.2em] uppercase transition-colors cursor-pointer"
                        >
                            RESET TO DEFAULTS
                        </button>
                        <button
                            onClick={() => handleDangerAction("SHUTDOWN")}
                            className="flex-1 bg-[var(--nova-red)]/80 text-white hover:bg-[var(--nova-red)] p-3 rounded text-[10px] font-bold tracking-[0.2em] uppercase transition-colors shadow-[0_0_15px_rgba(255,51,102,0.3)] cursor-pointer"
                        >
                            SHUTDOWN N.O.V.A
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
