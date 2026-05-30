"use client";

import React, {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";

import { apiGet } from "@/lib/api";
import {
    disconnectSocket,
    reconnectSocket,
} from "@/lib/socket";

import { User, UserRole } from "@/types/user";

type AuthContextType = {
    token: string | null;
    user: User | null;
    loading: boolean;
    setToken: (token: string | null) => Promise<User | null>;
    refreshUser: () => Promise<User | null>;
    logout: () => void;
    hasRole: (role: UserRole) => boolean;
    hasAnyRole: (roles: UserRole[]) => boolean;
    isPlatformAdmin: boolean;
    isSchoolAdmin: boolean;
    isTeacher: boolean;
    isStudent: boolean;
    canTeach: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(
    undefined,
);

const TOKEN_KEY = "mhike_token";

function normaliseUser(data: User): User {
    const roles =
        Array.isArray(data.roles) &&
            data.roles.length > 0
            ? data.roles
            : data.role
                ? [data.role]
                : [];

    return {
        ...data,
        roles: Array.from(
            new Set(roles),
        ),
    };
}

export function AuthProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const [token, setTokenState] =
        useState<string | null>(null);

    const [user, setUser] =
        useState<User | null>(null);

    const [loading, setLoading] =
        useState(true);

    const initialiseSocket =
        useCallback(
            (
                currentUser: User,
            ) => {
                reconnectSocket({
                    user_id:
                        currentUser.id,
                    school_id:
                        currentUser.school_id,
                });
            },
            [],
        );

    const fetchCurrentUser =
        useCallback(
            async (
                activeToken: string,
            ): Promise<User> => {
                const currentUser =
                    await apiGet<User>(
                        "/auth/me",
                        activeToken,
                    );

                return normaliseUser(
                    currentUser,
                );
            },
            [],
        );

    const clearAuth =
        useCallback(() => {
            if (
                typeof window !==
                "undefined"
            ) {
                sessionStorage.removeItem(
                    TOKEN_KEY,
                );
            }

            disconnectSocket();

            setTokenState(null);
            setUser(null);
        }, []);

    const refreshUser =
        useCallback(
            async (): Promise<User | null> => {
                if (
                    typeof window ===
                    "undefined"
                ) {
                    clearAuth();
                    return null;
                }

                const activeToken =
                    sessionStorage.getItem(
                        TOKEN_KEY,
                    );

                if (!activeToken) {
                    clearAuth();
                    return null;
                }

                try {
                    const currentUser =
                        await fetchCurrentUser(
                            activeToken,
                        );

                    setTokenState(
                        activeToken,
                    );

                    setUser(
                        currentUser,
                    );

                    initialiseSocket(
                        currentUser,
                    );

                    return currentUser;
                } catch {
                    clearAuth();
                    return null;
                }
            },
            [
                clearAuth,
                fetchCurrentUser,
                initialiseSocket,
            ],
        );

    const setToken =
        useCallback(
            async (
                value: string | null,
            ): Promise<User | null> => {
                setLoading(true);

                if (!value) {
                    clearAuth();
                    setLoading(false);
                    return null;
                }

                try {
                    if (
                        typeof window !==
                        "undefined"
                    ) {
                        sessionStorage.setItem(
                            TOKEN_KEY,
                            value,
                        );
                    }

                    const currentUser =
                        await fetchCurrentUser(
                            value,
                        );

                    setTokenState(
                        value,
                    );

                    setUser(
                        currentUser,
                    );

                    initialiseSocket(
                        currentUser,
                    );

                    return currentUser;
                } catch {
                    clearAuth();

                    throw new Error(
                        "Unable to authenticate user with provided token",
                    );
                } finally {
                    setLoading(false);
                }
            },
            [
                clearAuth,
                fetchCurrentUser,
                initialiseSocket,
            ],
        );

    const logout =
        useCallback(() => {
            clearAuth();
            setLoading(false);
        }, [clearAuth]);

    useEffect(() => {
        let mounted = true;

        async function initAuth() {
            setLoading(true);

            if (
                typeof window ===
                "undefined"
            ) {
                if (mounted) {
                    clearAuth();
                    setLoading(false);
                }

                return;
            }

            const storedToken =
                sessionStorage.getItem(
                    TOKEN_KEY,
                );

            if (!storedToken) {
                if (mounted) {
                    clearAuth();
                    setLoading(false);
                }

                return;
            }

            try {
                const currentUser =
                    await fetchCurrentUser(
                        storedToken,
                    );

                if (mounted) {
                    setTokenState(
                        storedToken,
                    );

                    setUser(
                        currentUser,
                    );

                    initialiseSocket(
                        currentUser,
                    );
                }
            } catch {
                if (mounted) {
                    clearAuth();
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
    }, [
        fetchCurrentUser,
        clearAuth,
        initialiseSocket,
    ]);

    const hasRole =
        useCallback(
            (
                role: UserRole,
            ) =>
                user?.roles?.includes(
                    role,
                ) ?? false,
            [user],
        );

    const hasAnyRole =
        useCallback(
            (
                roles: UserRole[],
            ) =>
                roles.some(
                    (role) =>
                        user?.roles?.includes(
                            role,
                        ),
                ),
            [user],
        );

    const isPlatformAdmin =
        hasRole(
            UserRole.PLATFORM_ADMIN,
        );

    const isSchoolAdmin =
        hasRole(
            UserRole.SCHOOL_ADMIN,
        );

    const isTeacher =
        hasRole(
            UserRole.TEACHER,
        );

    const isStudent =
        hasRole(
            UserRole.STUDENT,
        );

    const canTeach =
        hasAnyRole([
            UserRole.PLATFORM_ADMIN,
            UserRole.SCHOOL_ADMIN,
            UserRole.TEACHER,
        ]);

    const value =
        useMemo<AuthContextType>(
            () => ({
                token,
                user,
                loading,
                setToken,
                refreshUser,
                logout,
                hasRole,
                hasAnyRole,
                isPlatformAdmin,
                isSchoolAdmin,
                isTeacher,
                isStudent,
                canTeach,
            }),
            [
                token,
                user,
                loading,
                setToken,
                refreshUser,
                logout,
                hasRole,
                hasAnyRole,
                isPlatformAdmin,
                isSchoolAdmin,
                isTeacher,
                isStudent,
                canTeach,
            ],
        );

    return (
        <AuthContext.Provider
            value={value}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx =
        useContext(AuthContext);

    if (!ctx) {
        throw new Error(
            "useAuth must be used within an AuthProvider",
        );
    }

    return ctx;
}