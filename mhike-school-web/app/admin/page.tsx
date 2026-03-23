"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearToken, getToken } from "@/lib/api";
import {
    AdminCourseOut,
    AdminCoursesResponse,
    AdminStatsOut,
    AdminUserOut,
    AdminUsersResponse,
    deleteCourseAdmin,
    getAdminCourses,
    getAdminStats,
    getAdminUsers,
    setCoursePublished,
    toggleUserActive,
    updateUserRole,
} from "@/lib/adminApi";

function cardStyle(): React.CSSProperties {
    return {
        background: "#FFFFFF",
        border: "1px solid #E5E7EB",
        borderRadius: 20,
        padding: 18,
        boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
    };
}

function actionButtonStyle(
    kind: "primary" | "secondary" | "danger" = "secondary"
): React.CSSProperties {
    const styles: Record<string, React.CSSProperties> = {
        primary: {
            background: "#2563EB",
            color: "#FFFFFF",
            border: "1px solid #2563EB",
        },
        secondary: {
            background: "#FFFFFF",
            color: "#0F172A",
            border: "1px solid #E5E7EB",
        },
        danger: {
            background: "#FEF2F2",
            color: "#991B1B",
            border: "1px solid #FECACA",
        },
    };

    return {
        padding: "8px 12px",
        borderRadius: 10,
        fontWeight: 800,
        fontSize: 13,
        cursor: "pointer",
        ...styles[kind],
    };
}

function StatCard({
    label,
    value,
    tone = "default",
}: {
    label: string;
    value: string | number;
    tone?: "default" | "blue" | "green";
}) {
    const background =
        tone === "blue"
            ? "linear-gradient(135deg, #1D4ED8 0%, #60A5FA 100%)"
            : tone === "green"
                ? "linear-gradient(135deg, #059669 0%, #6EE7B7 100%)"
                : "#FFFFFF";

    const color = tone === "default" ? "#0F172A" : "#FFFFFF";
    const subColor = tone === "default" ? "#6B7280" : "rgba(255,255,255,0.85)";

    return (
        <div
            style={{
                ...cardStyle(),
                background,
                color,
                minHeight: 120,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
            }}
        >
            <div style={{ fontSize: 13, color: subColor }}>{label}</div>
            <div style={{ fontSize: 34, fontWeight: 900, lineHeight: 1 }}>
                {value}
            </div>
        </div>
    );
}

function Badge({
    text,
    kind = "neutral",
}: {
    text: string;
    kind?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
    const styles: Record<string, React.CSSProperties> = {
        neutral: {
            background: "#F3F4F6",
            color: "#374151",
        },
        success: {
            background: "#DCFCE7",
            color: "#166534",
        },
        warning: {
            background: "#FEF3C7",
            color: "#92400E",
        },
        danger: {
            background: "#FEE2E2",
            color: "#991B1B",
        },
        info: {
            background: "#DBEAFE",
            color: "#1D4ED8",
        },
    };

    return (
        <span
            style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "6px 10px",
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 800,
                ...styles[kind],
            }}
        >
            {text}
        </span>
    );
}

function roleBadge(role: string) {
    if (role === "admin") return <Badge text="Admin" kind="danger" />;
    if (role === "teacher") return <Badge text="Teacher" kind="info" />;
    return <Badge text="Student" kind="neutral" />;
}

function courseBadge(published: boolean) {
    return published ? (
        <Badge text="Published" kind="success" />
    ) : (
        <Badge text="Draft" kind="warning" />
    );
}

function TopNavbar({
    currentUserName,
    onRefresh,
    onLogout,
    refreshing,
}: {
    currentUserName: string;
    onRefresh: () => void;
    onLogout: () => void;
    refreshing: boolean;
}) {
    return (
        <nav
            style={{
                background: "linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%)",
                color: "#FFFFFF",
                padding: "14px 24px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 16,
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                position: "sticky",
                top: 0,
                zIndex: 50,
            }}
        >
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    minWidth: 0,
                }}
            >
                <div
                    style={{
                        width: 28,
                        height: 28,
                        borderRadius: 8,
                        background: "rgba(255,255,255,0.12)",
                        display: "grid",
                        placeItems: "center",
                        fontWeight: 900,
                        fontSize: 14,
                    }}
                >
                    🎓
                </div>

                <Link
                    href="/dashboard"
                    style={{
                        color: "#FFFFFF",
                        textDecoration: "none",
                        fontSize: 18,
                        fontWeight: 900,
                        whiteSpace: "nowrap",
                    }}
                >
                    Mhike School
                </Link>
            </div>

            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    flexWrap: "wrap",
                    justifyContent: "flex-end",
                }}
            >
                <div
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 12px",
                        borderRadius: 999,
                        background: "rgba(255,255,255,0.12)",
                        border: "1px solid rgba(255,255,255,0.14)",
                        color: "#FFFFFF",
                        fontWeight: 700,
                    }}
                >
                    <div
                        style={{
                            width: 24,
                            height: 24,
                            borderRadius: "50%",
                            background: "#DBEAFE",
                            color: "#1D4ED8",
                            display: "grid",
                            placeItems: "center",
                            fontSize: 12,
                            fontWeight: 900,
                        }}
                    >
                        {currentUserName?.charAt(0)?.toUpperCase() || "A"}
                    </div>
                    <span>{currentUserName || "Admin User"}</span>
                </div>

                <button
                    onClick={onRefresh}
                    disabled={refreshing}
                    style={{
                        padding: "10px 14px",
                        borderRadius: 12,
                        border: "none",
                        background: "#FFFFFF",
                        color: "#1D4ED8",
                        fontWeight: 800,
                        cursor: "pointer",
                    }}
                >
                    {refreshing ? "Refreshing..." : "Refresh"}
                </button>

                <button
                    onClick={onLogout}
                    style={{
                        padding: "10px 14px",
                        borderRadius: 12,
                        border: "none",
                        background: "#FFFFFF",
                        color: "#0F172A",
                        fontWeight: 800,
                        cursor: "pointer",
                    }}
                >
                    Logout
                </button>
            </div>
        </nav>
    );
}

export default function AdminPage() {
    const router = useRouter();

    const [token, setToken] = useState("");
    const [stats, setStats] = useState<AdminStatsOut | null>(null);
    const [usersRes, setUsersRes] = useState<AdminUsersResponse | null>(null);
    const [coursesRes, setCoursesRes] = useState<AdminCoursesResponse | null>(
        null
    );
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [busyKey, setBusyKey] = useState("");

    useEffect(() => {
        const t = getToken();

        if (!t) {
            setLoading(false);
            router.push("/login");
            return;
        }

        setToken(t);
    }, [router]);

    async function loadDashboard(authToken: string, silent = false) {
        if (!silent) setLoading(true);
        if (silent) setRefreshing(true);
        setError("");

        try {
            const [statsData, usersData, coursesData] = await Promise.all([
                getAdminStats(authToken),
                getAdminUsers(authToken, { skip: 0, limit: 8 }),
                getAdminCourses(authToken, { skip: 0, limit: 8 }),
            ]);

            setStats(statsData);
            setUsersRes(usersData);
            setCoursesRes(coursesData);
        } catch (e: unknown) {
            const message =
                e instanceof Error ? e.message : "Failed to load admin dashboard";

            setError(message);

            if (
                message.includes("401") ||
                message.includes("403") ||
                message.toLowerCase().includes("forbidden")
            ) {
                clearToken();
                router.push("/login");
            }
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }

    useEffect(() => {
        if (!token) return;
        void loadDashboard(token);
    }, [token]);

    async function handleRoleChange(
        userId: number,
        role: "student" | "teacher" | "admin"
    ) {
        if (!token) return;

        const key = `role-${userId}-${role}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await updateUserRole(token, userId, role);
            setSuccess("User role updated.");
            await loadDashboard(token, true);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to update user role");
        } finally {
            setBusyKey("");
        }
    }

    async function handleToggleActive(userId: number, nextActive: boolean) {
        if (!token) return;

        const key = `active-${userId}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await toggleUserActive(token, userId, nextActive);
            setSuccess(nextActive ? "User activated." : "User deactivated.");
            await loadDashboard(token, true);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to update user status");
        } finally {
            setBusyKey("");
        }
    }

    async function handleSetPublished(courseId: number, published: boolean) {
        if (!token) return;

        const key = `publish-${courseId}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await setCoursePublished(token, courseId, published);
            setSuccess(published ? "Course published." : "Course unpublished.");
            await loadDashboard(token, true);
        } catch (e: unknown) {
            setError(
                e instanceof Error ? e.message : "Failed to update course publication"
            );
        } finally {
            setBusyKey("");
        }
    }

    async function handleDeleteCourse(courseId: number, title: string) {
        if (!token) return;

        const confirmed = window.confirm(`Delete "${title}"?`);
        if (!confirmed) return;

        const key = `delete-${courseId}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await deleteCourseAdmin(token, courseId);
            setSuccess("Course deleted.");
            await loadDashboard(token, true);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to delete course");
        } finally {
            setBusyKey("");
        }
    }

    const users: AdminUserOut[] = usersRes?.items ?? [];
    const courses: AdminCourseOut[] = coursesRes?.items ?? [];

    const recentUsers = useMemo(() => users.slice(0, 8), [users]);
    const recentCourses = useMemo(() => courses.slice(0, 8), [courses]);

    const derived = useMemo(() => {
        const draftCourses = Math.max(
            0,
            (stats?.total_courses ?? 0) - (stats?.published_courses ?? 0)
        );

        const publishedRate =
            stats && stats.total_courses > 0
                ? Math.round((stats.published_courses / stats.total_courses) * 100)
                : 0;

        return {
            draftCourses,
            publishedRate,
        };
    }, [stats]);

    const handleLogout = () => {
        clearToken();
        router.push("/login");
    };

    if (loading) {
        return (
            <main
                style={{
                    minHeight: "100vh",
                    background: "#F1F5F9",
                }}
            >
                <TopNavbar
                    currentUserName="Admin User"
                    onRefresh={() => { }}
                    onLogout={handleLogout}
                    refreshing={false}
                />
                <div style={{ maxWidth: 1280, margin: "0 auto", padding: 24 }}>
                    <div style={cardStyle()}>
                        <div style={{ fontSize: 18, fontWeight: 800 }}>
                            Loading admin dashboard...
                        </div>
                    </div>
                </div>
            </main>
        );
    }

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F1F5F9",
            }}
        >
            <TopNavbar
                currentUserName="Admin User"
                onRefresh={() => {
                    if (token) void loadDashboard(token, true);
                }}
                onLogout={handleLogout}
                refreshing={refreshing}
            />

            <div style={{ maxWidth: 1280, margin: "0 auto", padding: 24 }}>
                <header
                    style={{
                        background:
                            "linear-gradient(135deg, #1E3A8A 0%, #2563EB 55%, #60A5FA 100%)",
                        borderRadius: 24,
                        padding: 24,
                        color: "white",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "stretch",
                        gap: 18,
                        flexWrap: "wrap",
                    }}
                >
                    <div style={{ flex: 1, minWidth: 320 }}>
                        <div style={{ fontSize: 14, opacity: 0.9, marginBottom: 8 }}>
                            Admin dashboard
                        </div>

                        <h1
                            style={{
                                margin: 0,
                                fontSize: 44,
                                fontWeight: 900,
                                lineHeight: 1.05,
                            }}
                        >
                            Manage Mhike School
                        </h1>

                        <p
                            style={{
                                marginTop: 12,
                                marginBottom: 0,
                                fontSize: 17,
                                color: "rgba(255,255,255,0.88)",
                                maxWidth: 700,
                            }}
                        >
                            Monitor users, courses, publications, and enrollments from one
                            place.
                        </p>

                        <div
                            style={{
                                display: "flex",
                                gap: 12,
                                marginTop: 18,
                                flexWrap: "wrap",
                            }}
                        >
                            <Link
                                href="/dashboard"
                                style={{
                                    textDecoration: "none",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    padding: "12px 16px",
                                    borderRadius: 14,
                                    fontWeight: 800,
                                    background: "#FFFFFF",
                                    color: "#1D4ED8",
                                }}
                            >
                                Main Dashboard
                            </Link>

                            <Link
                                href="/teacher"
                                style={{
                                    textDecoration: "none",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    padding: "12px 16px",
                                    borderRadius: 14,
                                    fontWeight: 800,
                                    background: "rgba(255,255,255,0.12)",
                                    color: "#FFFFFF",
                                    border: "1px solid rgba(255,255,255,0.22)",
                                }}
                            >
                                Teacher View
                            </Link>
                        </div>
                    </div>

                    <div
                        style={{
                            minWidth: 260,
                            background: "rgba(255,255,255,0.14)",
                            border: "1px solid rgba(255,255,255,0.18)",
                            borderRadius: 22,
                            padding: 18,
                            display: "flex",
                            flexDirection: "column",
                            justifyContent: "space-between",
                            gap: 14,
                        }}
                    >
                        <div>
                            <div style={{ fontSize: 13, opacity: 0.9 }}>System snapshot</div>
                            <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>
                                {stats?.total_users ?? 0} users
                            </div>
                            <div style={{ marginTop: 8 }}>
                                <Badge text="Operational" kind="success" />
                            </div>
                        </div>

                        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                            <button
                                onClick={() => token && void loadDashboard(token, true)}
                                disabled={refreshing}
                                style={{
                                    padding: "10px 14px",
                                    borderRadius: 12,
                                    border: "none",
                                    background: "#FFFFFF",
                                    color: "#1D4ED8",
                                    fontWeight: 800,
                                    cursor: "pointer",
                                }}
                            >
                                {refreshing ? "Refreshing..." : "Refresh"}
                            </button>

                            <button
                                onClick={handleLogout}
                                style={{
                                    padding: "10px 14px",
                                    borderRadius: 12,
                                    border: "1px solid rgba(255,255,255,0.22)",
                                    background: "rgba(255,255,255,0.12)",
                                    color: "white",
                                    fontWeight: 800,
                                    cursor: "pointer",
                                }}
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </header>

                {error && (
                    <div
                        style={{
                            marginTop: 16,
                            padding: 14,
                            borderRadius: 16,
                            background: "#FEF2F2",
                            color: "#991B1B",
                            border: "1px solid #FECACA",
                            fontWeight: 600,
                        }}
                    >
                        {error}
                    </div>
                )}

                {success && (
                    <div
                        style={{
                            marginTop: 16,
                            padding: 14,
                            borderRadius: 16,
                            background: "#ECFDF5",
                            color: "#065F46",
                            border: "1px solid #A7F3D0",
                            fontWeight: 600,
                        }}
                    >
                        {success}
                    </div>
                )}

                <section
                    style={{
                        marginTop: 18,
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                        gap: 14,
                    }}
                >
                    <StatCard label="Total users" value={stats?.total_users ?? 0} tone="blue" />
                    <StatCard label="Total students" value={stats?.total_students ?? 0} />
                    <StatCard label="Total teachers" value={stats?.total_teachers ?? 0} />
                    <StatCard label="Total admins" value={stats?.total_admins ?? 0} />
                    <StatCard label="Total courses" value={stats?.total_courses ?? 0} />
                    <StatCard
                        label="Published courses"
                        value={stats?.published_courses ?? 0}
                        tone="green"
                    />
                    <StatCard label="Draft courses" value={derived.draftCourses} />
                    <StatCard
                        label="Total enrollments"
                        value={stats?.total_enrollments ?? 0}
                    />
                </section>

                <section
                    style={{
                        marginTop: 18,
                        display: "grid",
                        gridTemplateColumns: "minmax(0, 1.25fr) minmax(320px, 1fr)",
                        gap: 14,
                        alignItems: "start",
                    }}
                >
                    <div style={{ display: "grid", gap: 14 }}>
                        <div style={cardStyle()}>
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    gap: 12,
                                    marginBottom: 14,
                                    flexWrap: "wrap",
                                }}
                            >
                                <div>
                                    <h2
                                        style={{
                                            margin: 0,
                                            fontSize: 24,
                                            fontWeight: 900,
                                        }}
                                    >
                                        Users
                                    </h2>
                                    <p style={{ margin: "6px 0 0 0", color: "#6B7280" }}>
                                        Manage roles and account status
                                    </p>
                                </div>
                                <Badge text={`${usersRes?.total ?? 0} total`} kind="info" />
                            </div>

                            {recentUsers.length === 0 ? (
                                <div style={{ color: "#6B7280" }}>No users found.</div>
                            ) : (
                                <div style={{ display: "grid", gap: 10 }}>
                                    {recentUsers.map((user) => (
                                        <div
                                            key={user.id}
                                            style={{
                                                border: "1px solid #E5E7EB",
                                                borderRadius: 16,
                                                padding: 14,
                                                background: "#F8FAFC",
                                                display: "grid",
                                                gap: 12,
                                            }}
                                        >
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent: "space-between",
                                                    gap: 12,
                                                    alignItems: "center",
                                                    flexWrap: "wrap",
                                                }}
                                            >
                                                <div>
                                                    <div
                                                        style={{
                                                            fontWeight: 900,
                                                            fontSize: 16,
                                                            color: "#0F172A",
                                                        }}
                                                    >
                                                        {user.full_name || "Unnamed user"}
                                                    </div>
                                                </div>

                                                <div
                                                    style={{
                                                        display: "flex",
                                                        gap: 8,
                                                        alignItems: "center",
                                                        flexWrap: "wrap",
                                                    }}
                                                >
                                                    {roleBadge(user.role)}
                                                    {user.is_active === false ? (
                                                        <Badge text="Inactive" kind="danger" />
                                                    ) : (
                                                        <Badge text="Active" kind="success" />
                                                    )}
                                                </div>
                                            </div>

                                            <div
                                                style={{
                                                    display: "flex",
                                                    gap: 8,
                                                    flexWrap: "wrap",
                                                }}
                                            >
                                                <button
                                                    onClick={() => void handleRoleChange(user.id, "student")}
                                                    disabled={busyKey !== ""}
                                                    style={actionButtonStyle()}
                                                >
                                                    Make Student
                                                </button>

                                                <button
                                                    onClick={() => void handleRoleChange(user.id, "teacher")}
                                                    disabled={busyKey !== ""}
                                                    style={actionButtonStyle("primary")}
                                                >
                                                    Promote Teacher
                                                </button>

                                                <button
                                                    onClick={() => void handleRoleChange(user.id, "admin")}
                                                    disabled={busyKey !== ""}
                                                    style={actionButtonStyle("danger")}
                                                >
                                                    Make Admin
                                                </button>

                                                <button
                                                    onClick={() =>
                                                        void handleToggleActive(
                                                            user.id,
                                                            user.is_active === false
                                                        )
                                                    }
                                                    disabled={busyKey !== ""}
                                                    style={actionButtonStyle()}
                                                >
                                                    {user.is_active === false ? "Activate" : "Deactivate"}
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div style={cardStyle()}>
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    gap: 12,
                                    marginBottom: 14,
                                    flexWrap: "wrap",
                                }}
                            >
                                <div>
                                    <h2
                                        style={{
                                            margin: 0,
                                            fontSize: 24,
                                            fontWeight: 900,
                                        }}
                                    >
                                        Courses
                                    </h2>
                                    <p style={{ margin: "6px 0 0 0", color: "#6B7280" }}>
                                        Moderate publication state and delete courses
                                    </p>
                                </div>
                                <Badge text={`${coursesRes?.total ?? 0} total`} kind="info" />
                            </div>

                            {recentCourses.length === 0 ? (
                                <div style={{ color: "#6B7280" }}>No courses found.</div>
                            ) : (
                                <div style={{ display: "grid", gap: 10 }}>
                                    {recentCourses.map((course) => (
                                        <div
                                            key={course.id}
                                            style={{
                                                border: "1px solid #E5E7EB",
                                                borderRadius: 16,
                                                padding: 14,
                                                background: "#F8FAFC",
                                                display: "grid",
                                                gap: 12,
                                            }}
                                        >
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent: "space-between",
                                                    alignItems: "flex-start",
                                                    gap: 10,
                                                    flexWrap: "wrap",
                                                }}
                                            >
                                                <div>
                                                    <div
                                                        style={{
                                                            fontWeight: 900,
                                                            fontSize: 16,
                                                            color: "#0F172A",
                                                        }}
                                                    >
                                                        {course.title}
                                                    </div>

                                                    <div
                                                        style={{
                                                            marginTop: 6,
                                                            color: "#6B7280",
                                                            fontSize: 14,
                                                        }}
                                                    >
                                                        {course.teacher_name
                                                            ? `Teacher: ${course.teacher_name}`
                                                            : `Teacher ID: ${course.teacher_id}`}
                                                    </div>

                                                    {course.description && (
                                                        <div
                                                            style={{
                                                                marginTop: 8,
                                                                color: "#475569",
                                                                fontSize: 14,
                                                            }}
                                                        >
                                                            {course.description}
                                                        </div>
                                                    )}
                                                </div>

                                                <div>{courseBadge(course.published)}</div>
                                            </div>

                                            <div
                                                style={{
                                                    display: "flex",
                                                    gap: 8,
                                                    flexWrap: "wrap",
                                                }}
                                            >
                                                <button
                                                    onClick={() =>
                                                        void handleSetPublished(course.id, !course.published)
                                                    }
                                                    disabled={busyKey !== ""}
                                                    style={actionButtonStyle(
                                                        course.published ? "secondary" : "primary"
                                                    )}
                                                >
                                                    {course.published ? "Unpublish" : "Publish"}
                                                </button>

                                                <button
                                                    onClick={() =>
                                                        void handleDeleteCourse(course.id, course.title)
                                                    }
                                                    disabled={busyKey !== ""}
                                                    style={actionButtonStyle("danger")}
                                                >
                                                    Delete Course
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div style={{ display: "grid", gap: 14 }}>
                        <div style={cardStyle()}>
                            <h2
                                style={{
                                    marginTop: 0,
                                    marginBottom: 10,
                                    fontSize: 24,
                                    fontWeight: 900,
                                }}
                            >
                                Publishing overview
                            </h2>

                            <div style={{ color: "#6B7280", marginBottom: 16 }}>
                                Quick view of course publishing health across the platform.
                            </div>

                            <div
                                style={{
                                    marginBottom: 10,
                                    display: "flex",
                                    justifyContent: "space-between",
                                }}
                            >
                                <span style={{ color: "#475569", fontWeight: 700 }}>
                                    Published rate
                                </span>
                                <span style={{ fontWeight: 900 }}>{derived.publishedRate}%</span>
                            </div>

                            <div
                                style={{
                                    height: 12,
                                    width: "100%",
                                    background: "#E5E7EB",
                                    borderRadius: 999,
                                    overflow: "hidden",
                                }}
                            >
                                <div
                                    style={{
                                        width: `${derived.publishedRate}%`,
                                        height: "100%",
                                        background:
                                            "linear-gradient(90deg, #2563EB 0%, #60A5FA 100%)",
                                    }}
                                />
                            </div>

                            <div
                                style={{
                                    display: "grid",
                                    gap: 10,
                                    marginTop: 18,
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        padding: "12px 14px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <span style={{ color: "#475569", fontWeight: 700 }}>
                                        Published
                                    </span>
                                    <strong>{stats?.published_courses ?? 0}</strong>
                                </div>

                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        padding: "12px 14px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <span style={{ color: "#475569", fontWeight: 700 }}>
                                        Draft
                                    </span>
                                    <strong>{derived.draftCourses}</strong>
                                </div>

                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        padding: "12px 14px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <span style={{ color: "#475569", fontWeight: 700 }}>
                                        Enrollments
                                    </span>
                                    <strong>{stats?.total_enrollments ?? 0}</strong>
                                </div>
                            </div>
                        </div>

                        <div style={cardStyle()}>
                            <h2
                                style={{
                                    marginTop: 0,
                                    marginBottom: 10,
                                    fontSize: 24,
                                    fontWeight: 900,
                                }}
                            >
                                Quick actions
                            </h2>

                            <div style={{ display: "grid", gap: 10 }}>
                                <Link
                                    href="/teacher"
                                    style={{
                                        textDecoration: "none",
                                        padding: "14px 16px",
                                        borderRadius: 14,
                                        background: "linear-gradient(90deg, #2563EB 0%, #3B82F6 100%)",
                                        color: "#FFFFFF",
                                        fontWeight: 800,
                                    }}
                                >
                                    Open teacher dashboard
                                </Link>

                                <Link
                                    href="/courses"
                                    style={{
                                        textDecoration: "none",
                                        padding: "14px 16px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        color: "#0F172A",
                                        fontWeight: 800,
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    Browse course catalog
                                </Link>

                                <button
                                    onClick={() => token && void loadDashboard(token, true)}
                                    disabled={refreshing}
                                    style={{
                                        textAlign: "left",
                                        padding: "14px 16px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        color: "#0F172A",
                                        fontWeight: 800,
                                        border: "1px solid #E5E7EB",
                                        cursor: "pointer",
                                    }}
                                >
                                    {refreshing ? "Refreshing admin data..." : "Refresh admin data"}
                                </button>
                            </div>
                        </div>

                        <div style={cardStyle()}>
                            <h2
                                style={{
                                    marginTop: 0,
                                    marginBottom: 10,
                                    fontSize: 24,
                                    fontWeight: 900,
                                }}
                            >
                                Platform summary
                            </h2>

                            <div style={{ display: "grid", gap: 10 }}>
                                <div
                                    style={{
                                        padding: 14,
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <div style={{ fontSize: 13, color: "#6B7280" }}>User mix</div>
                                    <div
                                        style={{
                                            marginTop: 6,
                                            fontWeight: 800,
                                            color: "#0F172A",
                                        }}
                                    >
                                        {stats?.total_students ?? 0} students •{" "}
                                        {stats?.total_teachers ?? 0} teachers •{" "}
                                        {stats?.total_admins ?? 0} admins
                                    </div>
                                </div>

                                <div
                                    style={{
                                        padding: 14,
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <div style={{ fontSize: 13, color: "#6B7280" }}>
                                        Course health
                                    </div>
                                    <div
                                        style={{
                                            marginTop: 6,
                                            fontWeight: 800,
                                            color: "#0F172A",
                                        }}
                                    >
                                        {stats?.total_courses ?? 0} total courses with{" "}
                                        {stats?.published_courses ?? 0} published
                                    </div>
                                </div>

                                <div
                                    style={{
                                        padding: 14,
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <div style={{ fontSize: 13, color: "#6B7280" }}>
                                        Learning activity
                                    </div>
                                    <div
                                        style={{
                                            marginTop: 6,
                                            fontWeight: 800,
                                            color: "#0F172A",
                                        }}
                                    >
                                        {stats?.total_enrollments ?? 0} enrollments recorded on the
                                        platform
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </main>
    );
}