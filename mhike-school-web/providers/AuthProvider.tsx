"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

type User = {
    id: number;
    email: string;
    full_name?: string | null;
    role: string;
    school_id?: number | null;
    school_name?: string | null;
    is_active: boolean;
    created_at: string;
};

type AuthContextType = {
    token: string | null;
    user: User | null;
    loading: boolean;
    setToken: (token: string | null) => void;
    refreshUser: () => Promise<void>;
    logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "mhike_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [token, setTokenState] = useState<string | null>(null);
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    const setToken = (value: string | null) => {
        setTokenState(value);
        if (value) {
            localStorage.setItem(TOKEN_KEY, value);
        } else {
            localStorage.removeItem(TOKEN_KEY);
            setUser(null);
        }
    };

    const refreshUser = async () => {
        const activeToken = token ?? localStorage.getItem(TOKEN_KEY);
        if (!activeToken) {
            setUser(null);
            setLoading(false);
            return;
        }

        try {
            const res = await fetch("http://localhost:8000/api/v1/auth/me", {
                headers: {
                    Authorization: `Bearer ${activeToken}`,
                },
            });

            if (!res.ok) {
                throw new Error("Failed to fetch current user");
            }

            const data = await res.json();
            setUser(data);
        } catch {
            setUser(null);
            localStorage.removeItem(TOKEN_KEY);
            setTokenState(null);
        } finally {
            setLoading(false);
        }
    };

    const logout = () => {
        setToken(null);
        setUser(null);
    };

    useEffect(() => {
        const stored = localStorage.getItem(TOKEN_KEY);
        if (stored) {
            setTokenState(stored);
        } else {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (token) {
            refreshUser();
        }
    }, [token]);

    const value = useMemo(
        () => ({
            token,
            user,
            loading,
            setToken,
            refreshUser,
            logout,
        }),
        [token, user, loading]
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return ctx;
}