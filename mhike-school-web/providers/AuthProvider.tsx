"use client";

import React, {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";

export type UserRole =
    | "platform_admin"
    | "school_admin"
    | "teacher"
    | "student";

export type UserStatus =
    | "active"
    | "deactivated"
    | "pending_erasure"
    | "anonymised";

type User = {
    id: number;
    email: string;
    full_name?: string | null;
    role: UserRole;
    roles: UserRole[];
    status: UserStatus;
    school_id?: number | null;
    school_name?: string | null;
    is_active: boolean;
    created_at: string;
};

type AuthContextType = {
    token: string | null;
    user: User | null;
    loading: boolean;
    setToken: (token: string | null) => Promise<User | null>;
    refreshUser: () => Promise<User | null>;
    logout: () => void;
    hasRole: (role: UserRole) => boolean;
    isPlatformAdmin: boolean;
    isSchoolAdmin: boolean;
    isTeacher: boolean;
    isStudent: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "mhike_token";
const ME_URL = "http://localhost:8000/api/v1/auth/me";

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [token, setTokenState] = useState<string | null>(null);
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchCurrentUser = useCallback(async (activeToken: string): Promise<User> => {
        const res = await fetch(ME_URL, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${activeToken}`,
                "Content-Type": "application/json",
                "Cache-Control": "no-store",
            },
            cache: "no-store",
        });

        if (!res.ok) {
            throw new Error("Failed to fetch current user");
        }

        const data = (await res.json()) as User;

        return {
            ...data,
            roles: Array.isArray(data.roles)
                ? data.roles
                : data.role
                    ? [data.role]
                    : [],
        };
    }, []);

    const clearAuth = useCallback(() => {
        if (typeof window !== "undefined") {
            sessionStorage.removeItem(TOKEN_KEY);
        }
        setTokenState(null);
        setUser(null);
    }, []);

    const refreshUser = useCallback(async (): Promise<User | null> => {
        if (typeof window === "undefined") {
            setTokenState(null);
            setUser(null);
            return null;
        }

        const activeToken = sessionStorage.getItem(TOKEN_KEY);

        if (!activeToken) {
            setTokenState(null);
            setUser(null);
            return null;
        }

        try {
            const currentUser = await fetchCurrentUser(activeToken);
            setTokenState(activeToken);
            setUser(currentUser);
            return currentUser;
        } catch {
            clearAuth();
            return null;
        }
    }, [clearAuth, fetchCurrentUser]);

    const setToken = useCallback(
        async (value: string | null): Promise<User | null> => {
            setLoading(true);

            if (!value) {
                clearAuth();
                setLoading(false);
                return null;
            }

            try {
                setUser(null);
                setTokenState(null);

                if (typeof window !== "undefined") {
                    sessionStorage.removeItem(TOKEN_KEY);
                    sessionStorage.setItem(TOKEN_KEY, value);
                }

                setTokenState(value);

                const currentUser = await fetchCurrentUser(value);
                setUser(currentUser);

                return currentUser;
            } catch {
                clearAuth();
                throw new Error("Unable to authenticate user with provided token");
            } finally {
                setLoading(false);
            }
        },
        [clearAuth, fetchCurrentUser]
    );

    const logout = useCallback(() => {
        clearAuth();
        setLoading(false);
    }, [clearAuth]);

    useEffect(() => {
        let mounted = true;

        async function initAuth() {
            setLoading(true);

            if (typeof window === "undefined") {
                if (mounted) {
                    setTokenState(null);
                    setUser(null);
                    setLoading(false);
                }
                return;
            }

            const storedToken = sessionStorage.getItem(TOKEN_KEY);

            if (!storedToken) {
                if (mounted) {
                    setTokenState(null);
                    setUser(null);
                    setLoading(false);
                }
                return;
            }

            try {
                const currentUser = await fetchCurrentUser(storedToken);

                if (mounted) {
                    setTokenState(storedToken);
                    setUser(currentUser);
                }
            } catch {
                if (mounted) {
                    sessionStorage.removeItem(TOKEN_KEY);
                    setTokenState(null);
                    setUser(null);
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }

        void initAuth();

        return () => {
            mounted = false;
        };
    }, [fetchCurrentUser]);

    const hasRole = useCallback(
        (role: UserRole) => {
            if (!user) return false;
            return Array.isArray(user.roles) && user.roles.includes(role);
        },
        [user]
    );

    const isPlatformAdmin = hasRole("platform_admin");
    const isSchoolAdmin = hasRole("school_admin");
    const isTeacher = hasRole("teacher");
    const isStudent = hasRole("student");

    const value = useMemo<AuthContextType>(
        () => ({
            token,
            user,
            loading,
            setToken,
            refreshUser,
            logout,
            hasRole,
            isPlatformAdmin,
            isSchoolAdmin,
            isTeacher,
            isStudent,
        }),
        [
            token,
            user,
            loading,
            setToken,
            refreshUser,
            logout,
            hasRole,
            isPlatformAdmin,
            isSchoolAdmin,
            isTeacher,
            isStudent,
        ]
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