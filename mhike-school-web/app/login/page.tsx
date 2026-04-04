"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";

type TokenOut = {
    access_token: string;
    token_type: string;
};

type AuthUser = {
    id: number;
    full_name?: string | null;
    email: string;
    role: "student" | "teacher" | "admin" | string;
    school_id?: number | null;
    school_name?: string | null;
    is_active?: boolean;
};

function getHomeRoute(role: string) {
    if (role === "admin") return "/admin";
    if (role === "teacher") return "/teacher";
    return "/dashboard";
}

export default function LoginPage() {
    const router = useRouter();
    const { setToken, logout } = useAuth();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [schoolId, setSchoolId] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setError("");

        const trimmedEmail = email.trim().toLowerCase();
        const trimmedPassword = password.trim();
        const trimmedSchoolId = schoolId.trim();
        const parsedSchoolId = Number(trimmedSchoolId);

        if (!trimmedEmail || !trimmedPassword || !trimmedSchoolId) {
            setError("Please enter your email, password, and school ID.");
            return;
        }

        if (!Number.isInteger(parsedSchoolId) || parsedSchoolId <= 0) {
            setError("Please enter a valid school ID.");
            return;
        }

        setLoading(true);

        try {
            logout();

            const res = await apiPost<TokenOut>("/auth/login", {
                email: trimmedEmail,
                password: trimmedPassword,
                school_id: parsedSchoolId,
            });

            if (!res.access_token) {
                throw new Error("No access token returned from the server.");
            }

            const currentUser = (await setToken(res.access_token)) as AuthUser | null;

            if (!currentUser) {
                throw new Error("Unable to load authenticated user.");
            }

            if (currentUser.is_active === false) {
                throw new Error("Account is inactive");
            }

            router.replace(getHomeRoute(currentUser.role));
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Login failed";

            if (
                message.includes("401") ||
                message.toLowerCase().includes("invalid credentials") ||
                message.toLowerCase().includes("invalid email or password") ||
                message.toLowerCase().includes("invalid token")
            ) {
                setError("Invalid email, password, or school ID.");
            } else if (
                message.includes("403") ||
                message.toLowerCase().includes("forbidden") ||
                message.toLowerCase().includes("inactive")
            ) {
                setError("Your account is not allowed to sign in.");
            } else if (
                message.includes("404") ||
                message.toLowerCase().includes("school not found")
            ) {
                setError("School not found.");
            } else {
                setError(message || "Login failed. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    }

    return (
        <main
            style={{
                minHeight: "100vh",
                display: "grid",
                placeItems: "start center",
                padding: "48px 24px",
            }}
        >
            <div style={{ width: "100%", maxWidth: 460 }}>
                <h1
                    style={{
                        fontSize: 28,
                        fontWeight: 800,
                        margin: 0,
                        color: "#111827",
                    }}
                >
                    Mhike School
                </h1>

                <p
                    style={{
                        marginTop: 8,
                        marginBottom: 24,
                        color: "#6B7280",
                        fontSize: 15,
                    }}
                >
                    Login to your dashboard
                </p>

                <form onSubmit={onSubmit}>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="Email"
                        autoComplete="email"
                        disabled={loading}
                        required
                        style={{
                            width: "100%",
                            padding: "14px 16px",
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            outline: "none",
                            marginBottom: 12,
                            fontSize: 16,
                            background: "white",
                            boxSizing: "border-box",
                        }}
                    />

                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Password"
                        autoComplete="current-password"
                        disabled={loading}
                        required
                        style={{
                            width: "100%",
                            padding: "14px 16px",
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            outline: "none",
                            marginBottom: 12,
                            fontSize: 16,
                            background: "white",
                            boxSizing: "border-box",
                        }}
                    />

                    <input
                        type="number"
                        value={schoolId}
                        onChange={(e) => setSchoolId(e.target.value)}
                        placeholder="School ID"
                        disabled={loading}
                        required
                        min={1}
                        style={{
                            width: "100%",
                            padding: "14px 16px",
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            outline: "none",
                            marginBottom: 12,
                            fontSize: 16,
                            background: "white",
                            boxSizing: "border-box",
                        }}
                    />

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: "100%",
                            padding: "14px 16px",
                            borderRadius: 16,
                            border: "1px solid #111827",
                            background: loading ? "#374151" : "#0F172A",
                            color: "white",
                            fontWeight: 800,
                            fontSize: 16,
                            cursor: loading ? "not-allowed" : "pointer",
                            opacity: loading ? 0.85 : 1,
                        }}
                    >
                        {loading ? "Signing in..." : "Login"}
                    </button>
                </form>

                {error && (
                    <div
                        style={{
                            marginTop: 14,
                            padding: "12px 14px",
                            borderRadius: 12,
                            background: "#FEF2F2",
                            color: "#991B1B",
                            fontSize: 14,
                        }}
                    >
                        {error}
                    </div>
                )}

                <p
                    style={{
                        marginTop: 16,
                        color: "#6B7280",
                        fontSize: 14,
                        lineHeight: 1.5,
                    }}
                >
                    Use your school account to sign in.
                </p>
            </div>
        </main>
    );
}