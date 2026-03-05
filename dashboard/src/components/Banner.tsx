
// src/components/Banner.tsx
import React, { useState } from 'react';
import { api } from '../api';

interface BannerProps {
    daemonRunning: boolean;
    onRestart: () => void;
}

export const Banner: React.FC<BannerProps> = ({ daemonRunning, onRestart }) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    if (daemonRunning) return null;

    const handleRestart = async () => {
        setLoading(true);
        setError("");
        try {
            await api.restartDaemon();
            onRestart();
        } catch (err: any) {
            setError(err.message || "Restart failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="banner">
            <div className="banner-content">
                <span className="indicator red">⚠️ DAEMON OFFLINE</span>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {error && <span className="error" style={{ marginBottom: 0, marginRight: '10px' }}>{error}</span>}
                    <button onClick={handleRestart} disabled={loading} style={{ width: 'auto', padding: '5px 15px' }}>
                        {loading ? "INITIALIZING..." : "RESTART SYSTEM"}
                    </button>
                </div>
            </div>
        </div>
    );
};
