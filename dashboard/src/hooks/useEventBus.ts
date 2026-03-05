import { useEffect, useRef, useState } from "react";
import { useNovaStore } from "../store/novaStore";

interface NovaEvent {
    type: string;
    source: string;
    payload: Record<string, unknown>;
    priority: number;
}

export function useEventBus() {
    const wsRef = useRef<WebSocket | null>(null);
    const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
    const [connected, setConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<NovaEvent | null>(null);

    useEffect(() => {
        let alive = true;

        function connect() {
            if (!alive) return;

            const ws = new WebSocket("ws://localhost:8000/api/ws/events");
            wsRef.current = ws;

            ws.onopen = () => {
                if (alive) setConnected(true);
            };

            ws.onmessage = (msg) => {
                if (!alive) return;
                try {
                    const event: NovaEvent = JSON.parse(msg.data);
                    setLastEvent(event);

                    const id = crypto.randomUUID();
                    const store = useNovaStore.getState();

                    switch (event.type) {
                        case "battery_low":
                            store.addToast({ id, message: `Battery low: ${event.payload.battery}%`, type: "warning" });
                            break;
                        case "cpu_spike":
                            store.addToast({ id, message: `CPU spike: ${event.payload.cpu}%`, type: "warning" });
                            break;
                        case "approval_required":
                            store.setPendingApprovals(store.pendingApprovals + 1);
                            store.addToast({ id, message: `Approval needed: ${event.payload.command ?? "action"}`, type: "info" });
                            break;
                        case "action_executed":
                            store.addToast({ id, message: `Action executed: ${event.payload.action ?? "ok"}`, type: "success" });
                            break;
                        case "daemon_started":
                            store.addToast({ id, message: "Daemon started", type: "info" });
                            break;
                    }
                } catch {
                    // ignore bad messages
                }
            };

            ws.onclose = () => {
                if (!alive) return;
                setConnected(false);
                const t = setTimeout(connect, 5000);
                timersRef.current.push(t);
            };

            ws.onerror = () => {
                // Silently close — onclose will handle reconnect
            };
        }

        // Delay connection by 100ms to survive React StrictMode's
        // immediate mount → unmount → remount cycle
        const startTimer = setTimeout(connect, 100);
        timersRef.current.push(startTimer);

        return () => {
            alive = false;
            timersRef.current.forEach(clearTimeout);
            timersRef.current = [];
            if (wsRef.current) {
                wsRef.current.onclose = null;
                wsRef.current.onerror = null;
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, []);

    return { connected, lastEvent };
}
