import { useCallback } from "react";
import { useAuth } from "../context/AuthContext";

const BASE_URL = "http://localhost:8000";

export function useApi() {
    const { token, logout } = useAuth();

    const apiFetch = useCallback(
        async (endpoint: string, options: RequestInit = {}): Promise<Response> => {
            const headers = new Headers(options.headers || {});

            if (token) {
                headers.set("Authorization", `Bearer ${token}`);
            }

            const res = await fetch(`${BASE_URL}${endpoint}`, {
                ...options,
                headers,
            });

            if (res.status === 401) {
                logout();
                throw new Error("Session expired");
            }

            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                const errMsg = errData?.detail || errData?.message || res.statusText || "API Error";
                throw new Error(errMsg);
            }

            return res;
        },
        [token, logout]
    );

    const get = useCallback(
        async <T = unknown>(endpoint: string): Promise<T> => {
            const res = await apiFetch(endpoint);
            return res.json();
        },
        [apiFetch]
    );

    const post = useCallback(
        async <T = unknown>(endpoint: string, body?: unknown): Promise<T> => {
            const res = await apiFetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: body ? JSON.stringify(body) : undefined,
            });
            return res.json();
        },
        [apiFetch]
    );

    const patch = useCallback(
        async <T = unknown>(endpoint: string, body?: unknown): Promise<T> => {
            const res = await apiFetch(endpoint, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: body ? JSON.stringify(body) : undefined,
            });
            return res.json();
        },
        [apiFetch]
    );

    return { apiFetch, get, post, patch };
}
