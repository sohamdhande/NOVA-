import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";

type LockState = "idle" | "verifying" | "denied" | "granted";

// Particle component for the floating background dots
function Particles() {
    const particles = Array.from({ length: 60 }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 2 + 1,
        duration: Math.random() * 20 + 15,
        delay: Math.random() * -20,
        opacity: Math.random() * 0.4 + 0.1,
    }));

    return (
        <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
            {particles.map((p) => (
                <div
                    key={p.id}
                    className="absolute rounded-full"
                    style={{
                        left: `${p.x}%`,
                        top: `${p.y}%`,
                        width: `${p.size}px`,
                        height: `${p.size}px`,
                        background: `rgba(0, 255, 204, ${p.opacity})`,
                        animation: `lock-float ${p.duration}s ease-in-out ${p.delay}s infinite`,
                    }}
                />
            ))}
        </div>
    );
}

export function LockScreen() {
    const { login } = useAuth();
    const [status, setStatus] = useState<LockState>("idle");
    const [time, setTime] = useState(new Date());
    const [showContent, setShowContent] = useState(false);

    // Clock
    useEffect(() => {
        const interval = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(interval);
    }, []);

    // Entry animation
    useEffect(() => {
        const t = setTimeout(() => setShowContent(true), 300);
        return () => clearTimeout(t);
    }, []);

    const handleAuthenticate = useCallback(async () => {
        console.log("[NOVA AUTH] Fingerprint clicked");
        if (status === "verifying") return;
        setStatus("verifying");

        try {
            const response = await fetch("http://localhost:8000/api/auth/biometric", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            console.log("[NOVA AUTH] Response status:", response.status);

            if (response.ok) {
                const data = await response.json();
                setStatus("granted");
                setTimeout(() => login(data.token, data.expires_in), 800);
            } else {
                setStatus("denied");
                setTimeout(() => setStatus("idle"), 2500);
            }
        } catch (err) {
            console.error("[NOVA AUTH] Biometric call failed:", err);
            setStatus("denied");
            setTimeout(() => setStatus("idle"), 2500);
        }
    }, [status, login]);

    const accentColor =
        status === "denied"
            ? "rgba(255, 70, 70, 1)"
            : status === "granted"
                ? "rgba(52, 211, 153, 1)"
                : "rgba(0, 255, 204, 1)";

    const accentColorDim =
        status === "denied"
            ? "rgba(255, 70, 70, 0.15)"
            : status === "granted"
                ? "rgba(52, 211, 153, 0.15)"
                : "rgba(0, 255, 204, 0.08)";

    const statusText =
        status === "verifying"
            ? "VERIFYING BIOMETRICS..."
            : status === "denied"
                ? "ACCESS DENIED"
                : status === "granted"
                    ? "ACCESS GRANTED"
                    : "BIOMETRIC AUTHENTICATION REQUIRED";

    const subText =
        status === "idle"
            ? "Touch the sensor to unlock"
            : status === "verifying"
                ? "Scanning biometric signature..."
                : status === "denied"
                    ? "Authentication failed — try again"
                    : "Welcome back, Operator";

    const formatTime = (d: Date) =>
        d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });

    const formatDate = (d: Date) =>
        d.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });

    return (
        <div
            className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center transition-all duration-1000 ${status === "granted" ? "opacity-0 scale-105 pointer-events-none" : "opacity-100 scale-100"
                }`}
            style={{
                background: `radial-gradient(ellipse at 50% 40%, #041e1e 0%, #020d0d 50%, #000505 100%)`,
            }}
        >
            {/* Particles */}
            <Particles />

            {/* Hex grid overlay */}
            <div
                className="fixed inset-0 pointer-events-none opacity-[0.03]"
                aria-hidden="true"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='49' viewBox='0 0 28 49'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%2300ffcc' fill-opacity='1'%3E%3Cpath d='M13.99 9.25l13 7.5v15l-13 7.5L1 31.75v-15l12.99-7.5zM3 17.9v12.7l10.99 6.34 11-6.35V17.9l-11-6.34L3 17.9zM0 15l12.98-7.5V0h-2v6.35L0 12.69v2.3zm0 18.5L12.98 41v8h-2v-6.85L0 35.81v-2.3zM15 0v7.5L27.99 15H28v-2.31h-.01L17 6.35V0h-2zm0 49v-8l12.99-7.5H28v2.31h-.01L17 42.15V49h-2z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
                }}
            />

            {/* Scan line */}
            <div className="lock-scanline" />

            {/* Corner brackets */}
            <div className="fixed top-6 left-6 w-12 h-12 border-l-2 border-t-2 pointer-events-none" style={{ borderColor: accentColor, opacity: 0.3 }} />
            <div className="fixed top-6 right-6 w-12 h-12 border-r-2 border-t-2 pointer-events-none" style={{ borderColor: accentColor, opacity: 0.3 }} />
            <div className="fixed bottom-6 left-6 w-12 h-12 border-l-2 border-b-2 pointer-events-none" style={{ borderColor: accentColor, opacity: 0.3 }} />
            <div className="fixed bottom-6 right-6 w-12 h-12 border-r-2 border-b-2 pointer-events-none" style={{ borderColor: accentColor, opacity: 0.3 }} />

            {/* Top status bar */}
            <div
                className={`fixed top-0 left-0 right-0 flex items-center justify-between px-8 py-4 font-mono text-[10px] tracking-[0.25em] uppercase transition-all duration-700 ${showContent ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"
                    }`}
                style={{ color: `${accentColor}` }}
            >
                <span style={{ opacity: 0.5 }}>SYSTEM: N.O.V.A — NEURAL OPERATIVE VIRTUAL ASSISTANT</span>
                <span style={{ opacity: 0.5 }}>{formatTime(time)}</span>
            </div>

            {/* Date display */}
            <div
                className={`font-mono text-[11px] tracking-[0.3em] uppercase mb-8 transition-all duration-700 delay-100 ${showContent ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                    }`}
                style={{ color: "rgba(255,255,255,0.2)" }}
            >
                {formatDate(time)}
            </div>

            {/* Logo */}
            <div
                className={`relative mb-14 transition-all duration-700 delay-200 ${showContent ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                    }`}
            >
                <div
                    className="font-mono text-5xl font-light tracking-[0.6em] select-none"
                    style={{
                        color: accentColor,
                        textShadow: `0 0 40px ${accentColorDim}, 0 0 80px ${accentColorDim}`,
                    }}
                >
                    N.O.V.A
                </div>
                {/* Underline decoration */}
                <div className="flex items-center gap-2 mt-4">
                    <div className="flex-1 h-px" style={{ background: `linear-gradient(90deg, transparent, ${accentColor})`, opacity: 0.3 }} />
                    <div className="w-1.5 h-1.5 rotate-45" style={{ background: accentColor, opacity: 0.5 }} />
                    <div className="flex-1 h-px" style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)`, opacity: 0.3 }} />
                </div>
            </div>

            {/* Fingerprint button with concentric rings */}
            <div
                className={`relative transition-all duration-700 delay-300 ${showContent ? "opacity-100 scale-100" : "opacity-0 scale-50"
                    }`}
            >
                {/* Outer ring 3 */}
                <div
                    className="absolute inset-0 rounded-full lock-ring-3"
                    style={{
                        width: "180px",
                        height: "180px",
                        top: "50%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                        border: `1px solid ${accentColor}`,
                        opacity: status === "verifying" ? 0.4 : 0.1,
                    }}
                />
                {/* Outer ring 2 */}
                <div
                    className="absolute inset-0 rounded-full lock-ring-2"
                    style={{
                        width: "150px",
                        height: "150px",
                        top: "50%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                        border: `1px solid ${accentColor}`,
                        opacity: status === "verifying" ? 0.5 : 0.15,
                    }}
                />
                {/* Outer ring 1 */}
                <div
                    className="absolute inset-0 rounded-full lock-ring-1"
                    style={{
                        width: "130px",
                        height: "130px",
                        top: "50%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                        border: `1px dashed ${accentColor}`,
                        opacity: status === "verifying" ? 0.6 : 0.2,
                    }}
                />

                {/* Main button */}
                <div
                    onClick={handleAuthenticate}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter") handleAuthenticate(); }}
                    className={`relative w-24 h-24 rounded-full flex items-center justify-center cursor-pointer transition-all duration-500
                        ${status === "idle" ? "lock-pulse-glow" : ""}
                        ${status === "verifying" ? "lock-spin-slow" : ""}
                        hover:scale-110 active:scale-95`}
                    style={{
                        background: `radial-gradient(circle, ${accentColorDim} 0%, transparent 70%)`,
                        border: `2px solid ${accentColor}`,
                        boxShadow: status === "granted"
                            ? `0 0 40px rgba(52, 211, 153, 0.6), 0 0 80px rgba(52, 211, 153, 0.3), inset 0 0 30px rgba(52, 211, 153, 0.1)`
                            : status === "denied"
                                ? `0 0 40px rgba(255, 70, 70, 0.6), 0 0 80px rgba(255, 70, 70, 0.3), inset 0 0 30px rgba(255, 70, 70, 0.1)`
                                : `0 0 20px rgba(0, 255, 204, 0.2), inset 0 0 20px rgba(0, 255, 204, 0.05)`,
                        pointerEvents: "all",
                    }}
                >
                    {/* Fingerprint SVG */}
                    <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="w-10 h-10 pointer-events-none transition-colors duration-300"
                        style={{ color: accentColor }}
                    >
                        <path d="M2 12C2 6.5 6.5 2 12 2a10 10 0 0 1 8 4" />
                        <path d="M5 19.5C5.5 18 6 15 6 12c0-3.5 2.5-6 6-6 3.5 0 6 2.5 6 6 0 1-.5 3-1 4.5" />
                        <path d="M8.5 16.5c-.5 1.5-.5 2-.5 3.5" />
                        <path d="M12 12c0 2.5-.5 5-1 7" />
                        <path d="M9.5 9.4c1-.4 2-.4 3 0s2 1.2 2 2.6c0 2-.5 4-1 6" />
                        <path d="M20 22c.5-2.5 1-5 1-8" />
                        <path d="M17.5 22a18.7 18.7 0 0 0 .5-4" />
                        <path d="M3 11c0-4.5 4-8 9-8s9 3.5 9 8" />
                    </svg>
                </div>
            </div>

            {/* Status text */}
            <div
                className={`mt-12 font-mono text-xs tracking-[0.35em] uppercase transition-all duration-500 delay-400 ${showContent ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                    }`}
                style={{
                    color: status === "denied"
                        ? "rgba(255, 70, 70, 0.9)"
                        : status === "granted"
                            ? "rgba(52, 211, 153, 0.9)"
                            : "rgba(255, 255, 255, 0.5)",
                    textShadow: status !== "idle" && status !== "verifying"
                        ? `0 0 20px ${accentColorDim}`
                        : "none",
                }}
            >
                {status === "verifying" && (
                    <span className="lock-text-flicker">{statusText}</span>
                )}
                {status !== "verifying" && statusText}
            </div>

            {/* Sub text */}
            <div
                className={`mt-3 font-mono text-[10px] tracking-[0.2em] transition-all duration-500 delay-500 ${showContent ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                    }`}
                style={{ color: "rgba(255, 255, 255, 0.2)" }}
            >
                {subText}
            </div>

            {/* Bottom status indicators */}
            <div
                className={`fixed bottom-8 left-0 right-0 flex justify-center gap-12 font-mono text-[9px] tracking-[0.2em] uppercase transition-all duration-700 delay-700 ${showContent ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                    }`}
                style={{ color: "rgba(255,255,255,0.15)" }}
            >
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 lock-status-blink" />
                    <span>SYSTEM ONLINE</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 lock-status-blink" style={{ animationDelay: "0.5s" }} />
                    <span>ENCRYPTED</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 lock-status-blink" style={{ animationDelay: "1s" }} />
                    <span>SECURE CHANNEL</span>
                </div>
            </div>

            {/* Animations */}
            <style>{`
                .lock-scanline {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 1px;
                    background: linear-gradient(90deg, 
                        transparent 0%, 
                        rgba(0,255,204,0.03) 15%,
                        rgba(0,255,204,0.15) 50%, 
                        rgba(0,255,204,0.03) 85%,
                        transparent 100%
                    );
                    box-shadow: 0 0 20px rgba(0,255,204,0.1), 0 0 60px rgba(0,255,204,0.05);
                    animation: lock-scan 4s linear infinite;
                    pointer-events: none;
                    z-index: 10000;
                }

                @keyframes lock-scan {
                    0%   { top: -2px; }
                    100% { top: 100vh; }
                }

                @keyframes lock-float {
                    0%, 100% {
                        transform: translateY(0px) translateX(0px);
                        opacity: 0.3;
                    }
                    25% {
                        transform: translateY(-20px) translateX(10px);
                        opacity: 0.6;
                    }
                    50% {
                        transform: translateY(-10px) translateX(-5px);
                        opacity: 0.2;
                    }
                    75% {
                        transform: translateY(-30px) translateX(8px);
                        opacity: 0.5;
                    }
                }

                .lock-pulse-glow {
                    animation: lock-glow 3s ease-in-out infinite;
                }

                @keyframes lock-glow {
                    0%, 100% {
                        box-shadow: 0 0 15px rgba(0,255,204,0.15), inset 0 0 15px rgba(0,255,204,0.03);
                    }
                    50% {
                        box-shadow: 0 0 40px rgba(0,255,204,0.35), 0 0 80px rgba(0,255,204,0.15), inset 0 0 30px rgba(0,255,204,0.08);
                    }
                }

                .lock-spin-slow {
                    animation: lock-spin 2s linear infinite;
                }

                @keyframes lock-spin {
                    0%   { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                .lock-ring-1 {
                    animation: lock-ring-pulse 3s ease-in-out infinite;
                }
                .lock-ring-2 {
                    animation: lock-ring-pulse 3s ease-in-out 0.5s infinite;
                }
                .lock-ring-3 {
                    animation: lock-ring-pulse 3s ease-in-out 1s infinite;
                }

                @keyframes lock-ring-pulse {
                    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.1; }
                    50%      { transform: translate(-50%, -50%) scale(1.08); opacity: 0.3; }
                }

                .lock-text-flicker {
                    animation: lock-flicker 0.15s ease-in-out infinite alternate;
                }

                @keyframes lock-flicker {
                    0%   { opacity: 0.7; }
                    100% { opacity: 1; }
                }

                .lock-status-blink {
                    animation: lock-blink 2s ease-in-out infinite;
                }

                @keyframes lock-blink {
                    0%, 100% { opacity: 1; }
                    50%      { opacity: 0.3; }
                }
            `}</style>
        </div>
    );
}
