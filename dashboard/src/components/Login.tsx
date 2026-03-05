
// src/components/Login.tsx
import React, { useState } from 'react';
import { api } from '../api';

interface LoginProps {
    onLoginSuccess: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            await api.login(password);
            onLoginSuccess();
        } catch (err: any) {
            setError(err.message || "Login failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-screen">
            <div className="panel" style={{ width: '300px' }}>
                <h2 style={{ textAlign: 'center', color: 'var(--accent-green)' }}>NOVA // ACCESS</h2>
                {error && <div className="error">{error}</div>}
                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <input
                            type="password"
                            placeholder="PASSWORD"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            disabled={loading}
                            autoFocus
                        />
                    </div>
                    <button type="submit" disabled={loading}>
                        {loading ? "AUTHENTICATING..." : "ENTER"}
                    </button>
                </form>
            </div>
        </div>
    );
};
