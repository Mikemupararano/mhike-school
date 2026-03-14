"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost, setToken } from "@/lib/api";

type TokenOut = {
    access_token: string;
    token_type: string;
};

export default function LoginPage() {
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function onSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const res = await apiPost<TokenOut>("/auth/login", {
                email,
                password,
            });

            setToken(res.access_token);
            router.push("/dashboard");
        } catch (err: any) {
            setError(err?.message ?? "Login failed");
        } finally {
            setLoading(false);
        }
    }

    return (
        <main style={{ maxWidth: 420, margin: "0 auto", padding: 24 }}>
            <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 6 }}>
                Mhike School
            </h1>

            <p style={{ color: "#6B7280", marginTop: 0 }}>
                Login to your dashboard
            </p>

            {error && (
                <div
                    style={{
                        marginTop: 12,
                        padding: 12,
                        borderRadius: 12,
                        background: "#FEF2F2",
                        color: "#991B1B",
                    }}
                >
                    {error}
                </div>
            )}

            <form onSubmit={onSubmit} style={{ marginTop: 14, display: "grid", gap: 10 }}>
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    style={{
                        padding: 12,
                        borderRadius: 12,
                        border: "1px solid #E5E7EB",
                    }}
                />

                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    style={{
                        padding: 12,
                        borderRadius: 12,
                        border: "1px solid #E5E7EB",
                    }}
                />

                <button
                    type="submit"
                    disabled={loading}
                    style={{
                        padding: 12,
                        borderRadius: 12,
                        border: "1px solid #E5E7EB",
                        background: "#111827",
                        color: "white",
                        fontWeight: 800,
                        cursor: "pointer",
                    }}
                >
                    {loading ? "Signing in..." : "Login"}
                </button>
            </form>

            <p style={{ color: "#6B7280", marginTop: 12, fontSize: 13 }}>
                Create users in FastAPI Swagger at <code>/docs</code>, then log in here.
            </p>
        </main>
    );
}