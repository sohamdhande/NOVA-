import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

interface AuthState {
    token: string | null;
    isAuthenticated: boolean;
    expiresAt: Date | null;
    login: (token: string, expiresIn: number) => void;
    logout: () => void;
    timeRemaining: () => number;
}

const AuthContext = createContext<AuthState>({
    token: null,
    isAuthenticated: false,
    expiresAt: null,
    login: () => { },
    logout: () => { },
    timeRemaining: () => 0,
});

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const [expiresAt, setExpiresAt] = useState<Date | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    const login = useCallback((newToken: string, expiresIn: number) => {
        setToken(newToken);
        setExpiresAt(new Date(Date.now() + expiresIn * 1000));
        setIsAuthenticated(true);
    }, []);

    const logout = useCallback(() => {
        setToken(null);
        setExpiresAt(null);
        setIsAuthenticated(false);
    }, []);

    const timeRemaining = useCallback(() => {
        if (!expiresAt) return 0;
        return Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000));
    }, [expiresAt]);

    // Auto-logout check every 30 seconds
    useEffect(() => {
        if (!isAuthenticated) return;

        const check = () => {
            if (expiresAt && Date.now() > expiresAt.getTime()) {
                logout();
            }
        };

        check();
        const interval = setInterval(check, 30_000);
        return () => clearInterval(interval);
    }, [isAuthenticated, expiresAt, logout]);

    return (
        <AuthContext.Provider value={{ token, isAuthenticated, expiresAt, login, logout, timeRemaining }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
