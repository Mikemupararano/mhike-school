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
                background: "#E5E7EB",
                borderRadius: 999,
                height: 10,
            }}
        >
            <div
                style={{
                    width: `${pct}%`,
                    background: "#2563EB",
                    height: 10,
                    borderRadius: 999,
                    transition: "width 250ms ease",
                }}
            />
        </div>
    );
}

export default function DashboardPage() {
    const router = useRouter();

    const [data, setData] = useState<DashboardMeOut | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const stats = useMemo(() => {
        if (!data) return null;

        return {
            enrolled: data.enrolled_courses,
            completed: data.total_lessons_completed,
        };
    }, [data]);

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

            setData(null);
            setError(message);

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
        <main style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
            <header
                style={{
                    display: "flex",
                    alignItems: "flex-end",
                    justifyContent: "space-between",
                    gap: 16,
                    flexWrap: "wrap",
                }}
            >
                <div>
                    <h1 style={{ fontSize: 28, fontWeight: 800, margin: 0 }}>
                        Mhike School
                    </h1>
                    <p style={{ marginTop: 6, color: "#6B7280" }}>
                        Student dashboard
                    </p>
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                    <button
                        onClick={() => void loadDashboard()}
                        style={{
                            padding: "10px 14px",
                            borderRadius: 12,
                            border: "1px solid #E5E7EB",
                            background: "#111827",
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
                            padding: "10px 14px",
                            borderRadius: 12,
                            border: "1px solid #E5E7EB",
                            background: "white",
                            color: "#111827",
                            fontWeight: 700,
                            cursor: "pointer",
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

            {stats && (
                <section
                    style={{
                        marginTop: 18,
                        display: "grid",
                        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                        gap: 14,
                    }}
                >
                    <div
                        style={{
                            padding: 16,
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            background: "white",
                        }}
                    >
                        <div style={{ color: "#6B7280", fontSize: 12 }}>
                            Courses enrolled
                        </div>
                        <div style={{ fontSize: 26, fontWeight: 800 }}>
                            {stats.enrolled}
                        </div>
                    </div>

                    <div
                        style={{
                            padding: 16,
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            background: "white",
                        }}
                    >
                        <div style={{ color: "#6B7280", fontSize: 12 }}>
                            Lessons completed
                        </div>
                        <div style={{ fontSize: 26, fontWeight: 800 }}>
                            {stats.completed}
                        </div>
                    </div>

                    <div
                        style={{
                            padding: 16,
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            background: "white",
                        }}
                    >
                        <div style={{ color: "#6B7280", fontSize: 12 }}>Status</div>
                        <div style={{ fontSize: 16, fontWeight: 800, marginTop: 6 }}>
                            {stats.enrolled === 0 ? "Enroll in a course" : "Keep going 🚀"}
                        </div>
                    </div>
                </section>
            )}

            <section style={{ marginTop: 18 }}>
                <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 10 }}>
                    Your courses
                </h2>

                {loading && (
                    <div
                        style={{
                            padding: 16,
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            color: "#6B7280",
                            background: "white",
                        }}
                    >
                        Loading dashboard...
                    </div>
                )}

                {!loading && !error && data && data.courses.length === 0 && (
                    <div
                        style={{
                            padding: 16,
                            borderRadius: 16,
                            border: "1px solid #E5E7EB",
                            color: "#6B7280",
                            background: "white",
                        }}
                    >
                        You&apos;re not enrolled in any courses yet.
                    </div>
                )}

                {!loading && !error && data && data.courses.length > 0 && (
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                            gap: 14,
                        }}
                    >
                        {data.courses.map((course) => (
                            <div
                                key={course.course_id}
                                style={{
                                    padding: 16,
                                    borderRadius: 16,
                                    border: "1px solid #E5E7EB",
                                    background: "white",
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        gap: 12,
                                    }}
                                >
                                    <div>
                                        <div style={{ fontSize: 16, fontWeight: 800 }}>
                                            {course.title}
                                        </div>
                                        <div
                                            style={{
                                                color: "#6B7280",
                                                fontSize: 13,
                                                marginTop: 4,
                                            }}
                                        >
                                            {course.completed_lessons}/{course.total_lessons} lessons •{" "}
                                            {course.progress_percent}%
                                        </div>
                                    </div>

                                    <span
                                        style={{
                                            fontSize: 12,
                                            padding: "6px 10px",
                                            borderRadius: 999,
                                            background: course.published ? "#ECFDF5" : "#FFFBEB",
                                            color: course.published ? "#065F46" : "#92400E",
                                            height: "fit-content",
                                            fontWeight: 700,
                                        }}
                                    >
                                        {course.published ? "Published" : "Draft"}
                                    </span>
                                </div>

                                <div style={{ marginTop: 12 }}>
                                    <ProgressBar value={course.progress_percent} />
                                </div>

                                <div
                                    style={{
                                        marginTop: 12,
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        gap: 12,
                                    }}
                                >
                                    <div style={{ color: "#6B7280", fontSize: 13 }}>
                                        {course.next_lesson ? (
                                            <>
                                                Next: <b>{course.next_lesson.title}</b>
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
                                            padding: "10px 12px",
                                            borderRadius: 12,
                                            border: "1px solid #E5E7EB",
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
            </section>
        </main>
    );
}