"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, clearToken } from "@/lib/api";
import {
    AdminStatsOut,
    AdminUserOut,
    AdminCourseOut,
    getAdminStats,
    getAdminUsers,
    getAdminCourses,
} from "@/lib/adminApi";

function Card({ children }: { children: React.ReactNode }) {
    return (
        <div
            style={{
                background: "white",
                border: "1px solid #E5E7EB",
                borderRadius: 16,
                padding: 16,
            }}
        >
            {children}
        </div>
    );
}

export default function AdminPage() {
    const router = useRouter();

    const [token, setToken] = useState("");
    const [stats, setStats] = useState<AdminStatsOut | null>(null);
    const [users, setUsers] = useState<AdminUserOut[]>([]);
    const [courses, setCourses] = useState<AdminCourseOut[]>([]);
    const [error, setError] = useState("");

    useEffect(() => {
        const t = getToken();
        if (!t) {
            router.push("/login");
            return;
        }
        setToken(t);
    }, [router]);

    useEffect(() => {
        if (!token) return;

        (async () => {
            try {
                setError("");
                const [statsData, usersData, coursesData] = await Promise.all([
                    getAdminStats(token),
                    getAdminUsers(token),
                    getAdminCourses(token),
                ]);

                setStats(statsData);
                setUsers(usersData);
                setCourses(coursesData);
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to load admin dashboard");
            }
        })();
    }, [token]);

    const recentUsers = useMemo(() => users.slice(0, 8), [users]);
    const recentCourses = useMemo(() => courses.slice(0, 8), [courses]);

    return (
        <main style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
            <header
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-end",
                    gap: 12,
                    flexWrap: "wrap",
                }}
            >
                <div>
                    <h1 style={{ fontSize: 30, fontWeight: 900, margin: 0 }}>
                        Mhike School • Admin
                    </h1>
                    <p style={{ color: "#6B7280", marginTop: 6 }}>
                        Manage users, courses, and platform overview
                    </p>
                </div>

                <div style={{ display: "flex", gap: 10 }}>
                    <button
                        onClick={() => router.push("/dashboard")}
                        style={{
                            padding: "10px 12px",
                            borderRadius: 12,
                            border: "1px solid #E5E7EB",
                            background: "white",
                            fontWeight: 800,
                        }}
                    >
                        Dashboard
                    </button>
                    <button
                        onClick={() => {
                            clearToken();
                            router.push("/login");
                        }}
                        style={{
                            padding: "10px 12px",
                            borderRadius: 12,
                            border: "1px solid #E5E7EB",
                            background: "white",
                            fontWeight: 800,
                        }}
                    >
                        Logout
                    </button>
                </div>
            </header>

            {error && (
                <div
                    style={{
                        marginTop: 16,
                        padding: 12,
                        borderRadius: 12,
                        background: "#FEF2F2",
                        color: "#991B1B",
                    }}
                >
                    {error}
                </div>
            )}

            <section
                style={{
                    marginTop: 18,
                    display: "grid",
                    gridTemplateColumns: "repeat(4, 1fr)",
                    gap: 14,
                }}
            >
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Total users</div>
                    <div style={{ fontSize: 28, fontWeight: 900 }}>
                        {stats?.total_users ?? "-"}
                    </div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Students</div>
                    <div style={{ fontSize: 28, fontWeight: 900 }}>
                        {stats?.total_students ?? "-"}
                    </div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Teachers</div>
                    <div style={{ fontSize: 28, fontWeight: 900 }}>
                        {stats?.total_teachers ?? "-"}
                    </div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Admins</div>
                    <div style={{ fontSize: 28, fontWeight: 900 }}>
                        {stats?.total_admins ?? "-"}
                    </div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Courses</div>
                    <div style={{ fontSize: 28, fontWeight: 900 }}>
                        {stats?.total_courses ?? "-"}
                    </div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Published courses</div>
                    <div style={{ fontSize: 28, fontWeight: 900 }}>
                        {stats?.published_courses ?? "-"}
                    </div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Enrollments</div>
                    <div style={{ fontSize: 28, fontWeight: 900 }}>
                        {stats?.total_enrollments ?? "-"}
                    </div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Platform status</div>
                    <div style={{ fontSize: 18, fontWeight: 900, marginTop: 8 }}>Operational</div>
                </Card>
            </section>

            <section
                style={{
                    marginTop: 18,
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 14,
                }}
            >
                <Card>
                    <h2 style={{ marginTop: 0 }}>Users</h2>
                    {recentUsers.length === 0 ? (
                        <div style={{ color: "#6B7280" }}>No users found.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 10 }}>
                            {recentUsers.map((user) => (
                                <div
                                    key={user.id}
                                    style={{
                                        border: "1px solid #E5E7EB",
                                        borderRadius: 12,
                                        padding: 12,
                                    }}
                                >
                                    <div style={{ fontWeight: 800 }}>{user.full_name}</div>
                                    <div style={{ color: "#6B7280", fontSize: 14 }}>{user.email}</div>
                                    <div style={{ marginTop: 6, fontSize: 13 }}>
                                        Role: <strong>{user.role}</strong>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </Card>

                <Card>
                    <h2 style={{ marginTop: 0 }}>Courses</h2>
                    {recentCourses.length === 0 ? (
                        <div style={{ color: "#6B7280" }}>No courses found.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 10 }}>
                            {recentCourses.map((course) => (
                                <div
                                    key={course.id}
                                    style={{
                                        border: "1px solid #E5E7EB",
                                        borderRadius: 12,
                                        padding: 12,
                                    }}
                                >
                                    <div style={{ fontWeight: 800 }}>{course.title}</div>
                                    <div style={{ color: "#6B7280", fontSize: 14 }}>
                                        Teacher ID: {course.teacher_id}
                                    </div>
                                    <div style={{ marginTop: 6, fontSize: 13 }}>
                                        Status:{" "}
                                        <strong>{course.published ? "Published" : "Draft"}</strong>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </Card>
            </section>
        </main>
    );
}