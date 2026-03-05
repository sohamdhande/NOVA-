import { useState } from "react";
import { useAuth } from "../context/AuthContext";

type LockState = "idle" | "verifying" | "denied" | "granted";

export function LockScreen() {
    const { login } = useAuth();
    const [status, setStatus] = useState<LockState>("idle");

    const handleAuthenticate = async () => {
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
                login(data.token, data.expires_in);
            } else {
                setStatus("denied");
                setTimeout(() => setStatus("idle"), 2000);
            }
        } catch (err) {
            console.error("[NOVA AUTH] Biometric call failed:", err);
            setStatus("denied");
            setTimeout(() => setStatus("idle"), 2000);
        }
    };

    const iconColor =
        status === "denied"
            ? "text-red-500"
            : status === "granted"
                ? "text-emerald-400"
                : "text-cyan-400";

    const glowColor =
        status === "denied"
            ? "shadow-[0_0_20px_rgba(239,68,68,0.5)]"
            : status === "granted"
                ? "shadow-[0_0_30px_rgba(52,211,153,0.6)]"
                : "";

    const statusText =
        status === "verifying"
            ? "VERIFYING..."
            : status === "denied"
                ? "ACCESS DENIED — TRY AGAIN"
                : status === "granted"
                    ? "ACCESS GRANTED"
                    : "BIOMETRIC AUTHENTICATION REQUIRED";

    const subText =
        status === "idle"
            ? "Touch the sensor to unlock"
            : status === "verifying"
                ? "Waiting for biometric response"
                : status === "denied"
                    ? "Authentication failed"
                    : "Unlocking...";

    return (
        <div
            className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center transition-opacity duration-500 ${status === "granted" ? "opacity-0 pointer-events-none" : "opacity-100"}`}
            style={{ background: "#020d0d" }}
        >
            {/* Scan line */}
            <div className="lock-scanline" />

            {/* Logo */}
            <div className="font-mono text-4xl tracking-[0.5em] text-cyan-400 mb-16 select-none">
                N.O.V.A
            </div>

            {/* Fingerprint button */}
            <div
                onClick={handleAuthenticate}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter") handleAuthenticate(); }}
                className={`relative w-28 h-28 rounded-full border-2 border-current flex items-center justify-center transition-all duration-300 cursor-pointer
                    ${iconColor}
                    ${status === "idle" ? "lock-pulse" : ""}
                    ${status === "verifying" ? "animate-spin" : ""}
                    ${glowColor}
                    hover:scale-105 active:scale-95`}
                style={{ pointerEvents: "all" }}
            >
                <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="w-14 h-14 pointer-events-none"
                >
                    <path d="M12 10a2 2 0 0 0-2 2c0 1.02.77 2 2 2s2-.98 2-2a2 2 0 0 0-2-2z" />
                    <path d="M19.07 4.93A10 10 0 0 0 2 12c0 2.08.64 4.01 1.73 5.61" />
                    <path d="M4.93 19.07A10 10 0 0 0 22 12c0-2.08-.64-4.01-1.73-5.61" />
                    <path d="M15.54 8.46a5 5 0 0 0-7.08 0" />
                    <path d="M8.46 15.54a5 5 0 0 0 7.08 0" />
                    <path d="M12 12v.01" />
                </svg>
            </div>

            {/* Status text */}
            <div
                className={`mt-10 font-mono text-xs tracking-[0.3em] uppercase transition-colors duration-300 ${status === "denied"
                        ? "text-red-400"
                        : status === "granted"
                            ? "text-emerald-400"
                            : "text-white/60"
                    }`}
            >
                {statusText}
            </div>

            {/* Sub text */}
            <div className="mt-3 font-mono text-[10px] tracking-[0.2em] text-white/30">
                {subText}
            </div>

            {/* CSS for scan line and pulse animations */}
            <style>{`
                .lock-scanline {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(90deg, transparent, rgba(0,255,204,0.15), transparent);
                    animation: lock-scan 3s linear infinite;
                    pointer-events: none;
                    z-index: 10000;
                }
                @keyframes lock-scan {
                    0%   { top: 0; }
                    100% { top: 100vh; }
                }
                .lock-pulse {
                    animation: lock-glow 2s ease-in-out infinite;
                }
                @keyframes lock-glow {
                    0%, 100% { box-shadow: 0 0 10px rgba(0,255,204,0.3); }
                    50%      { box-shadow: 0 0 30px rgba(0,255,204,0.6); }
                }
            `}</style>
        </div>
    );
}
