
// src/api.ts

export const API_BASE = "http://localhost:8000";

interface AuthResponse {
    token: string;
    expires_at: string;
}

interface StatusResponse {
    mode: string;
    auth_setup_required: boolean;
    daemon_running?: boolean;
    last_briefing_date?: string | null;
    authenticated?: boolean;
}

export interface Advisory {
    drop_amount: number;
    causes: string[];
    recommendations: string[];
}

export interface ProactivePayload {
    type: "morning" | "risk" | "discipline" | "deadline" | "idle";
    severity: "info" | "warning" | "critical";
    message: string;
    recommendations: string[];
}

export interface ProactiveData {
    triggered: boolean;
    payload: ProactivePayload | null;
}

export interface SummaryResponse {
    active_tasks_count: number;
    overdue_count: number;
    deadlines_48h_count: number;
    expenses_missing_today: boolean;
    missing_expense_days_count: number;
    daemon_running: boolean;
    daemon_last_error?: string | null;

    // Health Fields
    system_health?: number;
    health_zone?: "stable" | "controlled" | "elevated" | "critical";
    health_trigger?: boolean;
    advisory?: Advisory | null;

    // Proactive
    proactive?: ProactiveData | null;
}

export interface ChatResponse {
    status: "success" | "warning" | "blocked" | "info";
    trace: string[];
    message: string;
    structured: {
        type: string;
        [key: string]: unknown;
    } | null;
    projection: {
        current_health: number;
        projected_health: number;
    } | null;
    response_mode: "compact" | "expanded";
}

export const getToken = (): string | null => localStorage.getItem("nova_token");
const setToken = (token: string) => localStorage.setItem("nova_token", token);
export const clearToken = () => {
    localStorage.removeItem("nova_token");
    window.location.reload();
};

// Helper for authenticated requests
export async function authenticatedFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const token = getToken();
    const headers = new Headers(options.headers || {});

    if (token) {
        headers.append("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        clearToken();
        // Start cleanup or redirect flow handled by App state
        throw new Error("Unauthorized");
    }

    return response;
}

export const api = {
    getStatus: async (): Promise<StatusResponse> => {
        // Status is public but returns more info if authenticated
        try {
            const res = await authenticatedFetch("/api/status");
            return await res.json();
        } catch (e) {
            // If 401, it throws. If network error, throws.
            // For status, if 401, we might effectively be unauthenticated?
            // Actually authenticatedFetch throws on 401. 
            // User requirement: "If response is 401: Clear token, Throw auth error"
            throw e;
        }
    },

    getSummary: async (): Promise<SummaryResponse> => {
        const res = await authenticatedFetch("/api/summary");
        return await res.json();
    },

    getApprovals: async () => {
        const res = await authenticatedFetch("/api/approvals");
        return await res.json();
    },

    approveAction: async (id: number) => {
        const res = await authenticatedFetch(`/api/approvals/${id}/approve`, { method: "POST" });
        return await res.json();
    },

    denyAction: async (id: number) => {
        const res = await authenticatedFetch(`/api/approvals/${id}/deny`, { method: "POST" });
        return await res.json();
    },

    login: async (password: string): Promise<AuthResponse> => {
        const res = await fetch(`${API_BASE}/api/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password }),
        });

        if (!res.ok) {
            if (res.status === 401) throw new Error("Invalid password");
            if (res.status === 403) throw new Error("Setup required");
            throw new Error(`Login failed: ${res.statusText}`);
        }

        const data: AuthResponse = await res.json();
        setToken(data.token);
        localStorage.setItem("nova_session_expiry", data.expires_at);
        return data;
    },

    setupPassword: async (password: string): Promise<void> => {
        const res = await fetch(`${API_BASE}/api/setup-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password }),
        });

        if (!res.ok) {
            throw new Error("Setup failed");
        }
    },

    restartDaemon: async (): Promise<void> => {
        const res = await authenticatedFetch("/api/daemon/restart", {
            method: "POST",
        });

        if (!res.ok) {
            if (res.status === 400) throw new Error("Daemon already running");
            throw new Error("Restart failed");
        }
    },

    sendChat: async (message: string, sessionId?: string | null): Promise<ChatResponse> => {
        const res = await authenticatedFetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, session_id: sessionId || null }),
        });

        if (!res.ok) {
            throw new Error(`Chat request failed: ${res.statusText}`);
        }

        return await res.json();
    },
};
