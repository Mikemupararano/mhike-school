"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, clearToken, getToken } from "@/lib/api";

type NextLessonOut = {
    lesson_id: number;
    title: string;
};

type CourseProgressOut = {
    course_id: number;
    title: string;
    published: boolean;
    total_lessons: number;
    completed_lessons: number;
    progress_percent: number;
    next_lesson?: NextLessonOut | null;
};

type DashboardMeOut = {
    student_id: number;
    enrolled_courses: number;
    total_lessons_completed: number;
    courses: CourseProgressOut[];
};

function ProgressBar({ value }: { value: number }) {
    const pct = Math.max(0, Math.min(100, value));

    return (
        <div
            style={{
                width: "100%",
                height: 10,
                background: "#E5E7EB",
                borderRadius: 999,
                overflow: "hidden",
            }}
        >
            <div
                style={{
                    width: `${pct}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #3B82F6, #2563EB)",
                    borderRadius: 999,
                }}
            />
        </div>
    );
}

function StatCard({
    label,
    value,
}: {
    label: string;
    value: React.ReactNode;
}) {
    return (
        <div
            style={{
                background: "white",
                border: "1px solid #E5E7EB",
                borderRadius: 18,
                padding: 18,
                boxShadow: "0 6px 18px rgba(15, 23, 42, 0.04)",
            }}
        >
            <div style={{ color: "#6B7280", fontSize: 13 }}>{label}</div>
            <div style={{ fontSize: 34, fontWeight: 800, marginTop: 8, color: "#111827" }}>
                {value}
            </div>
        </div>
    );
}

function Panel({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <section
            style={{
                background: "white",
                border: "1px solid #E5E7EB",
                borderRadius: 20,
                padding: 20,
                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
            }}
        >
            <h3
                style={{
                    margin: "0 0 16px 0",
                    fontSize: 18,
                    fontWeight: 800,
                    color: "#111827",
                }}
            >
                {title}
            </h3>
            {children}
        </section>
    );
}

export default function DashboardPage() {
    const router = useRouter();
    const [data, setData] = useState<DashboardMeOut | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const studentName = "John";

    const stats = useMemo(() => {
        if (!data) return null;
        return {
            enrolled: data.enrolled_courses,
            completed: data.total_lessons_completed,
            averageProgress:
                data.courses.length > 0
                    ? Math.round(
                        data.courses.reduce((sum, c) => sum + c.progress_percent, 0) /
                        data.courses.length
                    )
                    : 0,
        };
    }, [data]);

    const featuredCourse = data?.courses?.[0] ?? null;

    async function loadDashboard() {
        setError("");
        setLoading(true);

        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        try {
            const res = await apiGet<DashboardMeOut>("/dashboard/me", token);
            setData(res);
        } catch (err: unknown) {
            const message =
                err instanceof Error ? err.message : "Failed to load dashboard";
            setError(message);
            setData(null);

            if (message.includes("401") || message.includes("403")) {
                clearToken();
                router.replace("/login");
            }
        } finally {
            setLoading(false);
        }
    }

    function handleLogout() {
        clearToken();
        router.replace("/login");
    }

    useEffect(() => {
        void loadDashboard();
    }, []);

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F3F6FB",
                color: "#111827",
            }}
        >
            <nav
                style={{
                    background: "linear-gradient(90deg, #1E3A8A, #2563EB)",
                    color: "white",
                    padding: "16px 28px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    boxShadow: "0 10px 30px rgba(37, 99, 235, 0.18)",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div
                        style={{
                            width: 38,
                            height: 38,
                            borderRadius: 12,
                            background: "rgba(255,255,255,0.15)",
                            display: "grid",
                            placeItems: "center",
                            fontSize: 20,
                        }}
                    >
                        🎓
                    </div>
                    <div style={{ fontSize: 28, fontWeight: 800 }}>Mhike School</div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <button
                        onClick={() => void loadDashboard()}
                        style={{
                            padding: "10px 16px",
                            borderRadius: 12,
                            border: "1px solid rgba(255,255,255,0.25)",
                            background: "rgba(255,255,255,0.12)",
                            color: "white",
                            fontWeight: 700,
                            cursor: "pointer",
                        }}
                    >
                        Refresh
                    </button>
                    <button
                        onClick={handleLogout}
                        style={{
                            padding: "10px 16px",
                            borderRadius: 12,
                            border: "none",
                            background: "white",
                            color: "#1E3A8A",
                            fontWeight: 800,
                            cursor: "pointer",
                        }}
                    >
                        Logout
                    </button>
                </div>
            </nav>

            <div style={{ maxWidth: 1250, margin: "0 auto", padding: 24 }}>
                <section
                    style={{
                        background: "linear-gradient(120deg, #1D4ED8, #60A5FA)",
                        borderRadius: 28,
                        color: "white",
                        padding: "32px 36px",
                        display: "grid",
                        gridTemplateColumns: "1.4fr 1fr",
                        gap: 24,
                        alignItems: "center",
                        boxShadow: "0 18px 40px rgba(37, 99, 235, 0.2)",
                    }}
                >
                    <div>
                        <div style={{ fontSize: 18, opacity: 0.9 }}>Student dashboard</div>
                        <h1
                            style={{
                                fontSize: 46,
                                lineHeight: 1.1,
                                margin: "12px 0 10px 0",
                                fontWeight: 900,
                            }}
                        >
                            Welcome back, {studentName}!
                        </h1>
                        <p style={{ fontSize: 18, margin: 0, opacity: 0.95 }}>
                            Continue your learning journey and stay on top of your progress.
                        </p>

                        <div style={{ display: "flex", gap: 12, marginTop: 24, flexWrap: "wrap" }}>
                            <button
                                onClick={() => {
                                    if (featuredCourse?.next_lesson) {
                                        router.push(`/lessons/${featuredCourse.next_lesson.lesson_id}`);
                                    }
                                }}
                                style={{
                                    padding: "14px 20px",
                                    borderRadius: 14,
                                    border: "none",
                                    background: "white",
                                    color: "#1D4ED8",
                                    fontWeight: 800,
                                    cursor: featuredCourse?.next_lesson ? "pointer" : "default",
                                    opacity: featuredCourse?.next_lesson ? 1 : 0.7,
                                }}
                            >
                                {featuredCourse?.next_lesson ? "Resume Course" : "View Progress"}
                            </button>

                            <button
                                onClick={() => router.push("/dashboard")}
                                style={{
                                    padding: "14px 20px",
                                    borderRadius: 14,
                                    border: "1px solid rgba(255,255,255,0.35)",
                                    background: "rgba(255,255,255,0.1)",
                                    color: "white",
                                    fontWeight: 700,
                                    cursor: "pointer",
                                }}
                            >
                                My Dashboard
                            </button>
                        </div>
                    </div>

                    <div
                        style={{
                            minHeight: 220,
                            borderRadius: 24,
                            background:
                                "radial-gradient(circle at top right, rgba(255,255,255,0.35), rgba(255,255,255,0.08))",
                            display: "grid",
                            placeItems: "center",
                            fontSize: 90,
                        }}
                    >
                        📘
                    </div>
                </section>

                {error && (
                    <div
                        style={{
                            marginTop: 18,
                            padding: 14,
                            borderRadius: 14,
                            background: "#FEF2F2",
                            color: "#991B1B",
                            border: "1px solid #FECACA",
                        }}
                    >
                        {error}
                    </div>
                )}

                <section
                    style={{
                        marginTop: 22,
                        display: "grid",
                        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                        gap: 18,
                    }}
                >
                    <StatCard label="Courses enrolled" value={stats?.enrolled ?? (loading ? "…" : 0)} />
                    <StatCard
                        label="Lessons completed"
                        value={stats?.completed ?? (loading ? "…" : 0)}
                    />
                    <StatCard
                        label="Average progress"
                        value={`${stats?.averageProgress ?? (loading ? "…" : 0)}%`}
                    />
                </section>

                <section
                    style={{
                        marginTop: 22,
                        display: "grid",
                        gridTemplateColumns: "1.45fr 1fr 1fr",
                        gap: 18,
                        alignItems: "start",
                    }}
                >
                    <div style={{ display: "grid", gap: 18 }}>
                        <Panel title="My Courses">
                            {loading && <div style={{ color: "#6B7280" }}>Loading courses...</div>}

                            {!loading && data && data.courses.length === 0 && (
                                <div style={{ color: "#6B7280" }}>
                                    You&apos;re not enrolled in any courses yet.
                                </div>
                            )}

                            {!loading && data && data.courses.length > 0 && (
                                <div style={{ display: "grid", gap: 16 }}>
                                    {data.courses.map((course) => (
                                        <div
                                            key={course.course_id}
                                            style={{
                                                border: "1px solid #E5E7EB",
                                                borderRadius: 18,
                                                padding: 16,
                                                background: "#F9FAFB",
                                            }}
                                        >
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent: "space-between",
                                                    gap: 12,
                                                    alignItems: "start",
                                                }}
                                            >
                                                <div>
                                                    <div style={{ fontSize: 22, fontWeight: 800 }}>{course.title}</div>
                                                    <div style={{ color: "#6B7280", marginTop: 6 }}>
                                                        {course.completed_lessons}/{course.total_lessons} lessons •{" "}
                                                        {course.progress_percent}%
                                                    </div>
                                                </div>

                                                <span
                                                    style={{
                                                        fontSize: 12,
                                                        padding: "6px 10px",
                                                        borderRadius: 999,
                                                        background: course.published ? "#DCFCE7" : "#FEF3C7",
                                                        color: course.published ? "#166534" : "#92400E",
                                                        fontWeight: 800,
                                                    }}
                                                >
                                                    {course.published ? "Published" : "Draft"}
                                                </span>
                                            </div>

                                            <div style={{ marginTop: 14 }}>
                                                <ProgressBar value={course.progress_percent} />
                                            </div>

                                            <div
                                                style={{
                                                    marginTop: 14,
                                                    display: "flex",
                                                    justifyContent: "space-between",
                                                    alignItems: "center",
                                                    gap: 12,
                                                }}
                                            >
                                                <div style={{ color: "#4B5563", fontSize: 14 }}>
                                                    {course.next_lesson ? (
                                                        <>
                                                            Next lesson: <b>{course.next_lesson.title}</b>
                                                        </>
                                                    ) : (
                                                        <>All lessons completed 🎉</>
                                                    )}
                                                </div>

                                                <button
                                                    disabled={!course.next_lesson}
                                                    onClick={() => {
                                                        if (course.next_lesson) {
                                                            router.push(`/lessons/${course.next_lesson.lesson_id}`);
                                                        }
                                                    }}
                                                    style={{
                                                        padding: "10px 14px",
                                                        borderRadius: 12,
                                                        border: "none",
                                                        background: course.next_lesson ? "#2563EB" : "#E5E7EB",
                                                        color: course.next_lesson ? "white" : "#6B7280",
                                                        fontWeight: 800,
                                                        cursor: course.next_lesson ? "pointer" : "not-allowed",
                                                    }}
                                                >
                                                    Continue
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </Panel>

                        <Panel title="Quick Links">
                            <div style={{ display: "grid", gap: 12 }}>
                                {[
                                    "My Profile",
                                    "Discussions",
                                    "Support Center",
                                ].map((label) => (
                                    <button
                                        key={label}
                                        style={{
                                            padding: "16px 18px",
                                            borderRadius: 14,
                                            border: "1px solid #DBEAFE",
                                            background: "linear-gradient(90deg, #3B82F6, #2563EB)",
                                            color: "white",
                                            fontWeight: 700,
                                            textAlign: "left",
                                            cursor: "pointer",
                                        }}
                                    >
                                        {label}
                                    </button>
                                ))}
                            </div>
                        </Panel>
                    </div>

                    <div style={{ display: "grid", gap: 18 }}>
                        <Panel title="Upcoming Assignment">
                            <div style={{ color: "#111827", fontWeight: 700, fontSize: 18 }}>
                                Project Report Submission
                            </div>
                            <div style={{ marginTop: 8, color: "#6B7280" }}>Due this week</div>
                            <button
                                style={{
                                    marginTop: 16,
                                    padding: "12px 16px",
                                    borderRadius: 12,
                                    border: "none",
                                    background: "#2563EB",
                                    color: "white",
                                    fontWeight: 800,
                                    cursor: "pointer",
                                }}
                            >
                                Submit
                            </button>
                        </Panel>

                        <Panel title="Course Progress">
                            {loading && <div style={{ color: "#6B7280" }}>Loading progress...</div>}

                            {!loading && data && (
                                <div style={{ display: "grid", gap: 16 }}>
                                    {data.courses.slice(0, 3).map((course) => (
                                        <div key={course.course_id}>
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent: "space-between",
                                                    fontSize: 14,
                                                    marginBottom: 8,
                                                }}
                                            >
                                                <span>{course.title}</span>
                                                <b>{course.progress_percent}%</b>
                                            </div>
                                            <ProgressBar value={course.progress_percent} />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </Panel>
                    </div>

                    <div style={{ display: "grid", gap: 18 }}>
                        <Panel title="Latest Announcement">
                            <div
                                style={{
                                    background: "#F9FAFB",
                                    borderRadius: 14,
                                    padding: 14,
                                    color: "#374151",
                                }}
                            >
                                Live Q&amp;A session tomorrow at 3 PM. Don&apos;t miss it.
                            </div>
                        </Panel>

                        <Panel title="Recent Activity">
                            <div style={{ display: "grid", gap: 14 }}>
                                {[
                                    "Scored 85% on Quiz 2",
                                    "Submitted assignment",
                                    "Enrolled in Physics",
                                ].map((item) => (
                                    <div
                                        key={item}
                                        style={{
                                            display: "flex",
                                            justifyContent: "space-between",
                                            gap: 12,
                                            paddingBottom: 10,
                                            borderBottom: "1px solid #F3F4F6",
                                        }}
                                    >
                                        <span style={{ color: "#374151" }}>{item}</span>
                                        <b style={{ color: "#111827" }}>+ XP</b>
                                    </div>
                                ))}
                            </div>
                        </Panel>

                        <Panel title="Leaderboard">
                            <div style={{ display: "grid", gap: 12 }}>
                                {[
                                    ["1", "Emma W.", "1250 XP"],
                                    ["2", "Alex T.", "1100 XP"],
                                    ["3", "You", "980 XP"],
                                ].map(([rank, name, score]) => (
                                    <div
                                        key={rank}
                                        style={{
                                            display: "grid",
                                            gridTemplateColumns: "36px 1fr auto",
                                            gap: 12,
                                            alignItems: "center",
                                            paddingBottom: 10,
                                            borderBottom: "1px solid #F3F4F6",
                                        }}
                                    >
                                        <div style={{ fontWeight: 900, color: "#2563EB" }}>{rank}</div>
                                        <div>{name}</div>
                                        <div style={{ fontWeight: 800 }}>{score}</div>
                                    </div>
                                ))}
                            </div>
                        </Panel>
                    </div>
                </section>
            </div>
        </main>
    );
}