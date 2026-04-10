"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost, saveToken } from "@/lib/api";
import { getCurrentUser } from "@/lib/authApi";

type LoginResponse = {
    access_token: string;
    token_type?: string;
};

export default function LoginPage() {
    const router = useRouter();

    const [mode, setMode] = useState<"school_user" | "platform_admin">("school_user");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [schoolId, setSchoolId] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const needsSchoolId = mode === "school_user";

    const subtitle = useMemo(() => {
        return needsSchoolId
            ? "Students, teachers, and school admins sign in with their school ID."
            : "Platform administrators sign in without a school ID.";
    }, [needsSchoolId]);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");

        if (!email.trim() || !password.trim()) {
            setError("Please enter your email and password.");
            return;
        }

        if (needsSchoolId && !schoolId.trim()) {
            setError("Please enter your school ID.");
            return;
        }

        try {
            setLoading(true);

            const payload =
                mode === "platform_admin"
                    ? {
                        email: email.trim(),
                        password,
                    }
                    : {
                        email: email.trim(),
                        password,
                        school_id: Number(schoolId),
                    };

            const res = await apiPost<LoginResponse>("/auth/login", payload);
            saveToken(res.access_token);

            const user = await getCurrentUser(res.access_token);

            if (user.role === "platform_admin") {
                router.push("/admin");
            } else if (user.role === "admin" || user.role === "school_admin") {
                router.push("/school-admin");
            } else if (user.role === "teacher") {
                router.push("/teacher");
            } else {
                router.push("/student");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <main
            style={{
                minHeight: "100vh",
                display: "grid",
                placeItems: "center",
                padding: 32,
                background:
                    "radial-gradient(circle at 18% 18%, rgba(37,99,235,0.12), transparent 28%), radial-gradient(circle at 82% 24%, rgba(59,130,246,0.10), transparent 30%), linear-gradient(180deg, #F8FAFC 0%, #EEF4FA 100%)",
            }}
        >
            <div
                style={{
                    width: "100%",
                    maxWidth: 1280,
                    display: "grid",
                    gridTemplateColumns: "1.1fr 0.95fr",
                    gap: 32,
                    alignItems: "stretch",
                }}
            >
                <section
                    style={{
                        borderRadius: 36,
                        padding: 48,
                        background:
                            "linear-gradient(135deg, #0F172A 0%, #1D4ED8 55%, #60A5FA 100%)",
                        color: "#FFFFFF",
                        boxShadow: "0 40px 100px rgba(29,78,216,0.35)",
                        position: "relative",
                        overflow: "hidden",
                        minHeight: 700,
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "space-between",
                    }}
                >
                    <div
                        style={{
                            position: "absolute",
                            inset: 0,
                            background:
                                "radial-gradient(circle at 80% 20%, rgba(255,255,255,0.18), transparent 18%), radial-gradient(circle at 22% 82%, rgba(255,255,255,0.10), transparent 22%)",
                            pointerEvents: "none",
                        }}
                    />

                    <div style={{ position: "relative", zIndex: 1 }}>
                        <div
                            style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 12,
                                padding: "12px 16px",
                                borderRadius: 999,
                                background: "rgba(255,255,255,0.12)",
                                border: "1px solid rgba(255,255,255,0.18)",
                                fontSize: 15,
                                fontWeight: 800,
                                backdropFilter: "blur(12px)",
                                WebkitBackdropFilter: "blur(12px)",
                            }}
                        >
                            <span
                                style={{
                                    width: 12,
                                    height: 12,
                                    borderRadius: "50%",
                                    background: "#93C5FD",
                                    boxShadow: "0 0 18px rgba(147,197,253,0.9)",
                                    flexShrink: 0,
                                }}
                            />
                            Mhike School
                        </div>

                        <h1
                            style={{
                                margin: "34px 0 18px",
                                fontSize: 64,
                                lineHeight: 0.98,
                                fontWeight: 900,
                                letterSpacing: "-0.05em",
                                maxWidth: 620,
                            }}
                        >
                            A premium learning platform for modern schools.
                        </h1>

                        <p
                            style={{
                                margin: 0,
                                fontSize: 22,
                                lineHeight: 1.65,
                                color: "rgba(255,255,255,0.9)",
                                maxWidth: 580,
                            }}
                        >
                            Bring together students, teachers, school admins, and platform
                            administrators in one polished, role-aware experience.
                        </p>
                    </div>

                    <div
                        style={{
                            position: "relative",
                            zIndex: 1,
                            display: "grid",
                            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                            gap: 16,
                        }}
                    >
                        {[
                            ["Secure sign-in", "Role-based access"],
                            ["Multi-school ready", "Tenant-aware dashboards"],
                            ["Elegant workflows", "Fast and focused UI"],
                        ].map(([title, desc]) => (
                            <div
                                key={title}
                                style={{
                                    borderRadius: 24,
                                    padding: 22,
                                    background: "rgba(255,255,255,0.10)",
                                    border: "1px solid rgba(255,255,255,0.14)",
                                    backdropFilter: "blur(12px)",
                                    WebkitBackdropFilter: "blur(12px)",
                                    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08)",
                                }}
                            >
                                <div
                                    style={{
                                        fontSize: 18,
                                        fontWeight: 900,
                                        marginBottom: 8,
                                        lineHeight: 1.25,
                                    }}
                                >
                                    {title}
                                </div>
                                <div
                                    style={{
                                        fontSize: 15,
                                        lineHeight: 1.6,
                                        color: "rgba(255,255,255,0.82)",
                                    }}
                                >
                                    {desc}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                <section
                    style={{
                        borderRadius: 36,
                        padding: 40,
                        background: "rgba(255,255,255,0.9)",
                        border: "1px solid rgba(255,255,255,0.7)",
                        boxShadow: "0 30px 80px rgba(15,23,42,0.12)",
                        backdropFilter: "blur(20px)",
                        WebkitBackdropFilter: "blur(20px)",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "center",
                    }}
                >
                    <div style={{ marginBottom: 28 }}>
                        <h2
                            style={{
                                margin: 0,
                                fontSize: 48,
                                lineHeight: 1.05,
                                fontWeight: 900,
                                letterSpacing: "-0.04em",
                                color: "#0F172A",
                            }}
                        >
                            Welcome back
                        </h2>

                        <p
                            style={{
                                margin: "14px 0 0",
                                fontSize: 18,
                                lineHeight: 1.65,
                                color: "#64748B",
                            }}
                        >
                            Sign in to continue to your dashboard.
                        </p>
                    </div>

                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: 8,
                            padding: 6,
                            borderRadius: 20,
                            background: "#EEF4FF",
                            border: "1px solid #D6E4FF",
                            marginBottom: 24,
                        }}
                    >
                        <button
                            type="button"
                            onClick={() => setMode("school_user")}
                            style={{
                                height: 56,
                                borderRadius: 16,
                                border: "none",
                                cursor: "pointer",
                                fontWeight: 900,
                                fontSize: 16,
                                background:
                                    mode === "school_user"
                                        ? "linear-gradient(135deg, #2563EB, #3B82F6)"
                                        : "transparent",
                                color: mode === "school_user" ? "#FFFFFF" : "#1E293B",
                                boxShadow:
                                    mode === "school_user"
                                        ? "0 8px 20px rgba(37,99,235,0.25)"
                                        : "none",
                                transition: "all 0.2s ease",
                            }}
                        >
                            School User
                        </button>

                        <button
                            type="button"
                            onClick={() => setMode("platform_admin")}
                            style={{
                                height: 56,
                                borderRadius: 16,
                                border: "none",
                                cursor: "pointer",
                                fontWeight: 900,
                                fontSize: 16,
                                background:
                                    mode === "platform_admin"
                                        ? "linear-gradient(135deg, #2563EB, #3B82F6)"
                                        : "transparent",
                                color: mode === "platform_admin" ? "#FFFFFF" : "#1E293B",
                                boxShadow:
                                    mode === "platform_admin"
                                        ? "0 8px 20px rgba(37,99,235,0.25)"
                                        : "none",
                                transition: "all 0.2s ease",
                            }}
                        >
                            Platform Admin
                        </button>
                    </div>

                    <div
                        style={{
                            marginBottom: 24,
                            padding: "18px 18px",
                            borderRadius: 20,
                            background: "#F8FAFC",
                            border: "1px solid #E2E8F0",
                            color: "#475569",
                            fontSize: 16,
                            lineHeight: 1.65,
                        }}
                    >
                        {subtitle}
                    </div>

                    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 18 }}>
                        <label style={{ display: "grid", gap: 10 }}>
                            <span
                                style={{
                                    fontSize: 15,
                                    fontWeight: 900,
                                    color: "#0F172A",
                                }}
                            >
                                Email
                            </span>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@school.com"
                                autoComplete="email"
                                style={inputStyle}
                            />
                        </label>

                        <label style={{ display: "grid", gap: 10 }}>
                            <span
                                style={{
                                    fontSize: 15,
                                    fontWeight: 900,
                                    color: "#0F172A",
                                }}
                            >
                                Password
                            </span>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                autoComplete="current-password"
                                style={inputStyle}
                            />
                        </label>

                        {needsSchoolId ? (
                            <label style={{ display: "grid", gap: 10 }}>
                                <span
                                    style={{
                                        fontSize: 15,
                                        fontWeight: 900,
                                        color: "#0F172A",
                                    }}
                                >
                                    School ID
                                </span>
                                <input
                                    type="number"
                                    value={schoolId}
                                    onChange={(e) => setSchoolId(e.target.value)}
                                    placeholder="Enter your school ID"
                                    inputMode="numeric"
                                    style={inputStyle}
                                />
                            </label>
                        ) : null}

                        {error ? (
                            <div
                                style={{
                                    padding: "16px 18px",
                                    borderRadius: 18,
                                    background: "#FEF2F2",
                                    border: "1px solid #FECACA",
                                    color: "#991B1B",
                                    fontSize: 15,
                                    fontWeight: 700,
                                    lineHeight: 1.55,
                                }}
                            >
                                {error}
                            </div>
                        ) : null}

                        <button
                            type="submit"
                            disabled={loading}
                            style={{
                                height: 60,
                                borderRadius: 20,
                                border: "none",
                                cursor: loading ? "not-allowed" : "pointer",
                                background: "linear-gradient(135deg, #1D4ED8, #2563EB)",
                                color: "#FFFFFF",
                                fontWeight: 900,
                                fontSize: 18,
                                boxShadow: "0 20px 40px rgba(37, 99, 235, 0.35)",
                                opacity: loading ? 0.75 : 1,
                                transition: "all 0.2s ease",
                            }}
                            onMouseEnter={(e) => {
                                if (!loading) {
                                    e.currentTarget.style.transform = "translateY(-2px)";
                                }
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.transform = "translateY(0)";
                            }}
                        >
                            {loading ? "Signing in..." : "Sign in"}
                        </button>
                    </form>
                </section>
            </div>
        </main>
    );
}

const inputStyle: React.CSSProperties = {
    height: 60,
    borderRadius: 18,
    border: "1px solid #CBD5E1",
    background: "#FFFFFF",
    padding: "0 18px",
    fontSize: 16,
    color: "#0F172A",
    outline: "none",
    boxShadow: "inset 0 1px 2px rgba(15, 23, 42, 0.04)",
};