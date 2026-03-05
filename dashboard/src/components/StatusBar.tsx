
// src/components/StatusBar.tsx
import React, { useState, useEffect } from 'react';

interface StatusBarProps {
    mode: string;
    daemonRunning: boolean;
    expiresAt: string | null;
}

export const StatusBar: React.FC<StatusBarProps> = ({ mode, daemonRunning, expiresAt }) => {
    const [timeLeft, setTimeLeft] = useState("");

    useEffect(() => {
        if (!expiresAt) {
            setTimeLeft("");
            return;
        }

        const interval = setInterval(() => {
            const now = new Date().getTime();
            const expiry = new Date(expiresAt).getTime();
            const diff = expiry - now;

            if (diff <= 0) {
                setTimeLeft("EXPIRED");
                // App might handle logout via polling status (401), but visual indicator helps
            } else {
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((diff % (1000 * 60)) / 1000);
                setTimeLeft(`${minutes}m ${seconds}s`);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [expiresAt]);

    const getSessionColor = () => {
        if (timeLeft === "EXPIRED") return "red";
        if (!timeLeft) return "neutral";

        // Check if < 5m
        // We need the raw diff here? Or parse the string? 
        // Parsing "Xm Ys" is annoying. Let's calculate state in the effect or just standard check.
        // Actually, let's keep it simple. If text starts with "0m", "1m", "2m", "3m", "4m" -> amber.
        if (timeLeft.match(/^[0-4]m/)) return "amber";
        return "neutral"; // Default for session is not specified as green, usually info is neutral. 
        // Logic says "SESSION < 5m -> amber". > 5m ???
        // Let's make >5m green for "good" or neutral. User said "Mode -> neutral". 
        // Let's stick to neutral for >5m to keep it clean, unless "good" session needs green. 
        // But "DAEMON ACTIVE -> green". 
        // I'll use neutral for >5m.
    };

    return (
        <div className="status-bar">
            <div>
                [ MODE: <span className="indicator neutral">{mode.toUpperCase()}</span> ]
            </div>
            <div>
                [ DAEMON: <span className={`indicator ${daemonRunning ? 'green' : 'red'}`}>
                    {daemonRunning ? "ACTIVE" : "DOWN"}
                </span> ]
            </div>
            <div>
                [ SESSION: <span className={`indicator ${getSessionColor()}`}>{timeLeft || "--"}</span> ]
            </div>
        </div>
    );
};
