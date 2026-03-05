
// src/components/Setup.tsx
import React, { useState } from 'react';
import { api } from '../api';

interface SetupProps {
    onSetupSuccess: () => void;
}

export const Setup: React.FC<SetupProps> = ({ onSetupSuccess }) => {
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (password !== confirm) {
            setError("Passwords do not match");
            return;
        }
        if (password.length < 8) {
            setError("Password must be at least 8 chars"); // Basic check
            return;
        }

        setLoading(true);

        try {
            await api.setupPassword(password);
            // Auto login after setup? Or just redirect to login?
            // User flow said: "If auth_setup_required -> render Setup screen... Else render Login".
            // After setup, auth_setup_required becomes false. So App will switch to Login automatically upon re-fetching status.
            onSetupSuccess();
        } catch (err: any) {
            setError(err.message || "Setup failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-screen">
            <div className="panel" style={{ width: '350px' }}>
                <h2 style={{ textAlign: 'center', color: 'var(--accent-red)' }}>NOVA // SYSTEM INIT</h2>
                <div style={{ textAlign: 'center', color: 'var(--text-dim)', marginBottom: '20px' }}>
                    Restricted Environment. Set Admin Password.
                </div>

                {error && <div className="error">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <input
                            type="password"
                            placeholder="NEW PASSWORD"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            disabled={loading}
                            autoFocus
                        />
                    </div>
                    <div className="input-group">
                        <input
                            type="password"
                            placeholder="CONFIRM PASSWORD"
                            value={confirm}
                            onChange={(e) => setConfirm(e.target.value)}
                            disabled={loading}
                        />
                    </div>
                    <button type="submit" disabled={loading}>
                        {loading ? "INITIALIZING..." : "SET ACCESS CODE"}
                    </button>
                </form>
            </div>
        </div>
    );
};
