import {
    useState,
    useEffect,
    useRef,
    useCallback,
    type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, type ChatResponse } from "../../api";

// ------------------------------------------------------------------ //
//  Types                                                               //
// ------------------------------------------------------------------ //

type ArcMode = "CLOSED" | "OPEN_COMPACT" | "OPEN_EXPANDED";

interface ArcMessage {
    id: string;
    role: "user" | "nova";
    message: string;
    trace?: string[];
    structured?: { type: string;[key: string]: unknown } | null;
    projection?: { current_health: number; projected_health: number } | null;
    status?: string;
}

// ------------------------------------------------------------------ //
//  Structured Block Renderers                                          //
// ------------------------------------------------------------------ //

function TaskListBlock({ items }: { items: string[] }) {
    return (
        <div className="mt-3 bg-white/[0.03] border border-white/[0.06] p-3">
            <div className="text-[9px] uppercase tracking-[0.2em] text-white/30 mb-2 font-mono">
                Task List
            </div>
            {items.map((item, i) => (
                <div
                    key={i}
                    className="flex items-start gap-2 text-xs text-white/70 font-mono py-1 border-b border-white/[0.04] last:border-0"
                >
                    <span className="text-accent/60 mt-px">▸</span>
                    {item}
                </div>
            ))}
        </div>
    );
}

function AdvisoryBlock({ recommendations }: { recommendations: string[] }) {
    return (
        <div className="mt-3 bg-critical/[0.05] border border-critical/[0.15] p-3">
            <div className="text-[9px] uppercase tracking-[0.2em] text-critical/60 mb-2 font-mono">
                Advisory
            </div>
            {recommendations.map((r, i) => (
                <div
                    key={i}
                    className="text-xs text-white/60 font-mono py-1 pl-3 border-l border-critical/30"
                >
                    {r}
                </div>
            ))}
        </div>
    );
}

function FinanceSummaryBlock({
    today,
    month,
}: {
    today: number;
    month: number;
}) {
    return (
        <div className="mt-3 bg-white/[0.03] border border-white/[0.06] p-3 font-mono">
            <div className="text-[9px] uppercase tracking-[0.2em] text-white/30 mb-2">
                Finance Summary
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
                <span className="text-white/40">Today</span>
                <span className="text-white/80">₹{today.toFixed(2)}</span>
                <span className="text-white/40">Month</span>
                <span className="text-white/80">₹{month.toFixed(2)}</span>
            </div>
        </div>
    );
}

function ConfirmationBlock({
    domain,
    action,
}: {
    domain: string;
    action: string;
}) {
    return (
        <div className="mt-3 bg-warning/[0.05] border border-warning/[0.2] p-3 font-mono">
            <div className="text-[9px] uppercase tracking-[0.2em] text-warning/60 mb-2">
                Confirmation Required
            </div>
            <div className="text-xs text-white/60">
                <span className="text-warning/80">{domain}/{action}</span> — awaiting approval
            </div>
        </div>
    );
}

function ProjectionBar({
    current,
    projected,
}: {
    current: number;
    projected: number;
}) {
    const delta = projected - current;
    const color =
        delta >= 0 ? "text-success" : delta > -5 ? "text-warning" : "text-critical";

    return (
        <div className="mt-3 bg-white/[0.03] border border-white/[0.06] p-3 font-mono">
            <div className="text-[9px] uppercase tracking-[0.2em] text-white/30 mb-2">
                Health Projection
            </div>
            <div className="flex items-center gap-3 text-xs">
                <span className="text-white/50">{current}</span>
                <span className="text-white/20">→</span>
                <span className={color}>{projected}</span>
                <span className={`text-[10px] ${color}`}>
                    ({delta >= 0 ? "+" : ""}{delta})
                </span>
            </div>
        </div>
    );
}

function StructuredRenderer({
    structured,
}: {
    structured: { type: string;[key: string]: unknown };
}) {
    switch (structured.type) {
        case "task_list":
            return <TaskListBlock items={(structured.items as string[]) || []} />;
        case "advisory":
            return (
                <AdvisoryBlock
                    recommendations={(structured.recommendations as string[]) || []}
                />
            );
        case "finance_summary":
            return (
                <FinanceSummaryBlock
                    today={(structured.today as number) || 0}
                    month={(structured.month as number) || 0}
                />
            );
        case "confirmation_required":
            return (
                <ConfirmationBlock
                    domain={(structured.domain as string) || ""}
                    action={(structured.action as string) || ""}
                />
            );
        case "client_command":
            return (
                <div className="mt-2 text-[10px] text-white/30 font-mono uppercase">
                    ▸ Client action: {(structured.target as string) || (structured.action as string)}
                </div>
            );
        default:
            return null;
    }
}

// ------------------------------------------------------------------ //
//  Waveform Animation                                                  //
// ------------------------------------------------------------------ //

function Waveform({ active }: { active: boolean }) {
    return (
        <div className="flex items-end gap-px h-3 mt-1 opacity-40">
            {Array.from({ length: 24 }).map((_, i) => (
                <motion.div
                    key={i}
                    className="w-px bg-accent/60"
                    animate={{
                        height: active ? [2, 8, 4, 10, 3, 6][i % 6] : 1,
                    }}
                    transition={{
                        duration: 0.4,
                        repeat: active ? Infinity : 0,
                        repeatType: "reverse",
                        delay: i * 0.05,
                    }}
                />
            ))}
        </div>
    );
}

// ------------------------------------------------------------------ //
//  Main Component                                                      //
// ------------------------------------------------------------------ //

interface InvocationArcProps {
    healthTrigger?: boolean;
    healthZone?: string;
    proactivePayload?: {
        type: string;
        severity: string;
        message: string;
        recommendations: string[];
    } | null;
    onArcOpen?: () => void;
    onArcClose?: () => void;
}

export function InvocationArc({
    healthTrigger = false,
    healthZone = "stable",
    proactivePayload = null,
    onArcOpen,
    onArcClose,
}: InvocationArcProps) {
    // `mode` = logical state: what the arc SHOULD be.
    // `shouldRender` = keeps DOM alive during exit animation.
    const [mode, setMode] = useState<ArcMode>("CLOSED");
    const [shouldRender, setShouldRender] = useState(false);

    const [messages, setMessages] = useState<ArcMessage[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [isStreaming, setIsStreaming] = useState(false);

    const inputRef = useRef<HTMLInputElement>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const msgIdCounter = useRef(0);
    const lastToggleRef = useRef(0);

    const isOpen = mode !== "CLOSED";
    const width = mode === "OPEN_EXPANDED" ? 540 : 420;

    // ---- Open / Close helpers ---- //
    const openArc = useCallback(
        (expanded = false) => {
            const now = Date.now();
            if (now - lastToggleRef.current < 300) return;
            lastToggleRef.current = now;

            setShouldRender(true);
            setMode(expanded ? "OPEN_EXPANDED" : "OPEN_COMPACT");
            onArcOpen?.();
        },
        [onArcOpen]
    );

    const closeArc = useCallback(() => {
        const now = Date.now();
        if (now - lastToggleRef.current < 300) return;
        lastToggleRef.current = now;

        // Setting mode to CLOSED triggers AnimatePresence exit.
        // shouldRender stays true until onExitComplete fires.
        setMode("CLOSED");
        onArcClose?.();

        // Blur input so global key handler works immediately after
        if (inputRef.current) inputRef.current.blur();
    }, [onArcClose]);

    // Called when Framer Motion finishes the exit animation
    const handleExitComplete = useCallback(() => {
        setShouldRender(false);
    }, []);

    // ---- Auto-scroll ---- //
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: "smooth",
            });
        }
    }, [messages]);

    // ---- Auto-focus input when open ---- //
    useEffect(() => {
        if (isOpen && inputRef.current) {
            setTimeout(() => inputRef.current?.focus(), 350);
        }
    }, [isOpen]);

    // ---- Health-trigger auto-open ---- //
    useEffect(() => {
        if (healthTrigger && mode === "CLOSED") {
            setShouldRender(true);
            setMode("OPEN_EXPANDED");
            onArcOpen?.();

            if (proactivePayload) {
                const id = `nova-${++msgIdCounter.current}`;
                setMessages((prev) => [
                    ...prev,
                    {
                        id,
                        role: "nova",
                        message: proactivePayload.message,
                        structured: {
                            type: "advisory",
                            recommendations: proactivePayload.recommendations,
                        },
                        status: "info",
                    },
                ]);
            }
        }
    }, [healthTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

    // ---- Global Keyboard (capture phase) ---- //
    // Using capture phase (3rd arg = true) ensures this handler
    // fires BEFORE React's synthetic event system, so ESC always
    // reaches us even when an <input> inside the arc has focus.
    useEffect(() => {
        const handler = (e: globalThis.KeyboardEvent) => {
            const target = e.target as HTMLElement;
            const isTyping =
                target.tagName === "INPUT" ||
                target.tagName === "TEXTAREA" ||
                target.isContentEditable;

            // "/" toggles — only when not typing in other inputs
            if (e.key === "/" && !isTyping) {
                e.preventDefault();
                if (mode === "CLOSED") {
                    openArc(false);
                } else {
                    closeArc();
                }
                return;
            }

            // ESC always closes — even from inside the arc's own input
            if (e.key === "Escape" && mode !== "CLOSED") {
                e.preventDefault();
                e.stopPropagation();
                closeArc();
            }
        };

        window.addEventListener("keydown", handler, true);
        return () => window.removeEventListener("keydown", handler, true);
    }, [mode, openArc, closeArc]);

    // ---- Streaming Simulation ---- //
    const streamMessage = useCallback(
        (
            fullText: string,
            extra: Partial<ArcMessage>,
            onComplete?: () => void
        ) => {
            setIsStreaming(true);
            const sentences = fullText.match(/[^.!?]+[.!?]?\s*/g) || [fullText];
            const id = `nova-${++msgIdCounter.current}`;

            setMessages((prev) => [
                ...prev,
                { id, role: "nova", message: "", ...extra },
            ]);

            let idx = 0;
            const interval = setInterval(() => {
                if (idx < sentences.length) {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === id
                                ? { ...m, message: m.message + sentences[idx] }
                                : m
                        )
                    );
                    idx++;
                } else {
                    clearInterval(interval);
                    setIsStreaming(false);
                    onComplete?.();
                }
            }, 90);
        },
        []
    );

    // ---- Send Message ---- //
    const handleSend = useCallback(async () => {
        const msg = inputValue.trim();
        if (!msg || isStreaming) return;

        setInputValue("");
        const userId = `user-${++msgIdCounter.current}`;
        setMessages((prev) => [...prev, { id: userId, role: "user", message: msg }]);

        try {
            const response: ChatResponse = await api.sendChat(msg);

            if (response.response_mode === "expanded" && mode === "OPEN_COMPACT") {
                setMode("OPEN_EXPANDED");
            }

            streamMessage(
                response.message,
                {
                    trace: response.trace,
                    structured: response.structured,
                    projection: response.projection,
                    status: response.status,
                },
                () => {
                    if (response.response_mode === "compact" && mode === "OPEN_EXPANDED") {
                        setTimeout(() => setMode("OPEN_COMPACT"), 1000);
                    }
                }
            );
        } catch {
            const errId = `nova-${++msgIdCounter.current}`;
            setMessages((prev) => [
                ...prev,
                {
                    id: errId,
                    role: "nova",
                    message: "Connection failed. Check backend status.",
                    status: "warning",
                },
            ]);
        }
    }, [inputValue, isStreaming, mode, streamMessage]);

    // ---- Input Keydown ---- //
    const handleInputKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
            e.preventDefault();
            handleSend();
        }
        // Block "/" from being typed into input
        if (e.key === "/") {
            e.stopPropagation();
        }
        // ESC is handled by the global capture-phase listener.
        // Do NOT stopPropagation for Escape here.
    };

    // ---- Status color ---- //
    const zoneColor =
        healthZone === "critical"
            ? "text-critical"
            : healthZone === "elevated"
                ? "text-warning"
                : "text-accent";

    // ---- Render ---- //
    if (!shouldRender && !isOpen) return null;

    return (
        <>
            {/* Ambient dimming overlay */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="fixed inset-0 bg-black/5 z-40 pointer-events-none"
                    />
                )}
            </AnimatePresence>

            {/* The Arc */}
            <AnimatePresence onExitComplete={handleExitComplete}>
                {isOpen && (
                    <>
                        {/* Cyan edge trace */}
                        <motion.div
                            key="arc-edge"
                            initial={{ scaleY: 0 }}
                            animate={{ scaleY: 1 }}
                            exit={{ scaleY: 0 }}
                            transition={{ duration: 0.2, ease: "easeOut" }}
                            style={{ transformOrigin: "top" }}
                            className="fixed right-0 top-0 bottom-0 w-px bg-accent/40 z-[51]"
                        />

                        {/* Main container */}
                        <motion.div
                            key="arc-main"
                            initial={{ scaleX: 0, rotate: -3, opacity: 0 }}
                            animate={{ scaleX: 1, rotate: 0, opacity: 1 }}
                            exit={{ scaleX: 0, rotate: -3, opacity: 0 }}
                            transition={{
                                duration: 0.4,
                                ease: [0.22, 1, 0.36, 1],
                            }}
                            style={{
                                width,
                                transformOrigin: "right center",
                            }}
                            className="fixed right-0 top-0 bottom-0 z-50 flex flex-col
                bg-[#0E1319]/95 backdrop-blur-lg
                border-l border-white/[0.06]
                rounded-tl-2xl rounded-bl-2xl
                shadow-[inset_2px_0_20px_rgba(0,240,255,0.03)]
                transition-[width] duration-300 ease-out"
                        >
                            {/* ---- Header Strip ---- */}
                            <div className="px-5 pt-5 pb-3 border-b border-white/[0.06]">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-accent/80">
                                            NOVA AI CORE
                                        </div>
                                        <div className="text-[9px] font-mono uppercase tracking-[0.15em] text-white/30 mt-0.5">
                                            Status: <span className={zoneColor}>OPERATIONAL</span>
                                        </div>
                                    </div>
                                    <button
                                        onClick={closeArc}
                                        className="text-white/20 hover:text-white/50 transition-colors text-xs font-mono"
                                    >
                                        ESC
                                    </button>
                                </div>
                                <div className="text-[8px] font-mono uppercase tracking-[0.15em] text-white/20 mt-1">
                                    Context:{" "}
                                    <span className="text-white/40">
                                        {healthZone?.toUpperCase() || "STABLE"}
                                    </span>
                                </div>
                            </div>

                            {/* ---- Intelligence Stream ---- */}
                            <div
                                ref={scrollRef}
                                className="flex-1 overflow-y-auto px-5 py-4 space-y-4
                  scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
                            >
                                {messages.length === 0 && (
                                    <div className="text-center py-16">
                                        <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-white/15">
                                            Intelligence Stream Active
                                        </div>
                                        <div className="text-[9px] font-mono text-white/10 mt-2">
                                            Press / to toggle &middot; Type to engage
                                        </div>
                                    </div>
                                )}

                                {messages.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={msg.role === "user" ? "ml-8" : "mr-4"}
                                    >
                                        {/* Role tag */}
                                        <div
                                            className={`text-[8px] font-mono uppercase tracking-[0.2em] mb-1 ${msg.role === "user"
                                                ? "text-white/25 text-right"
                                                : msg.status === "warning"
                                                    ? "text-warning/50"
                                                    : msg.status === "blocked"
                                                        ? "text-critical/50"
                                                        : "text-accent/40"
                                                }`}
                                        >
                                            {msg.role === "user" ? "OPERATOR" : "NOVA"}
                                        </div>

                                        {/* Message */}
                                        <div
                                            className={`text-[13px] font-mono leading-relaxed ${msg.role === "user"
                                                ? "text-white/70 text-right"
                                                : msg.status === "warning"
                                                    ? "text-warning/80"
                                                    : msg.status === "blocked"
                                                        ? "text-critical/70"
                                                        : "text-white/60"
                                                }`}
                                        >
                                            {msg.message}
                                            {isStreaming &&
                                                msg === messages[messages.length - 1] &&
                                                msg.role === "nova" && (
                                                    <span className="inline-block w-1.5 h-3.5 bg-accent/60 ml-0.5 animate-pulse" />
                                                )}
                                        </div>

                                        {/* Trace (collapsed) */}
                                        {msg.trace && msg.trace.length > 0 && (
                                            <div className="mt-1.5 text-[9px] font-mono text-white/15 leading-tight">
                                                {msg.trace.slice(0, 3).map((t, i) => (
                                                    <div key={i}>· {t}</div>
                                                ))}
                                                {msg.trace.length > 3 && (
                                                    <div>· +{msg.trace.length - 3} more</div>
                                                )}
                                            </div>
                                        )}

                                        {/* Structured blocks */}
                                        {msg.structured && (
                                            <StructuredRenderer structured={msg.structured} />
                                        )}

                                        {/* Projection */}
                                        {msg.projection && (
                                            <ProjectionBar
                                                current={msg.projection.current_health}
                                                projected={msg.projection.projected_health}
                                            />
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* ---- Command Input ---- */}
                            <div className="px-5 pb-5 pt-2 border-t border-white/[0.06]">
                                <div className="flex items-center gap-2">
                                    <span className="text-accent/50 font-mono text-sm">{">"}</span>
                                    <input
                                        ref={inputRef}
                                        type="text"
                                        value={inputValue}
                                        onChange={(e) => setInputValue(e.target.value)}
                                        onKeyDown={handleInputKeyDown}
                                        placeholder="_"
                                        disabled={isStreaming}
                                        className="flex-1 bg-transparent border-none outline-none
                      text-sm font-mono text-white/80
                      placeholder:text-accent/20
                      caret-accent"
                                        autoComplete="off"
                                        spellCheck={false}
                                    />
                                </div>
                                <Waveform active={isStreaming} />
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </>
    );
}
