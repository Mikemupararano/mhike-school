"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, getToken } from "@/lib/api";

type ModuleOut = {
    id: number;
    title: string;
    order: number;
};

type LessonOut = {
    id: number;
    title: string;
    order: number;
    published?: boolean;
};

type ProgressItem = {
    lesson_id: number;
    completed: boolean;
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
                    transition: "width 250ms ease",
                }}
            />
        </div>
    );
}

export default function CoursePage() {
    const router = useRouter();
    const params = useParams<{ courseId: string }>();
    const courseId = Number(params.courseId);

    const [modules, setModules] = useState<ModuleOut[]>([]);
    const [lessonsByModule, setLessonsByModule] = useState<Record<number, LessonOut[]>>({});
    const [completedLessonIds, setCompletedLessonIds] = useState<Set<number>>(new Set());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    async function loadCourse() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        try {
            setLoading(true);
            setError("");

            const [modulesRes, progressRes] = await Promise.all([
                apiGet<ModuleOut[]>(`/courses/${courseId}/modules`, token),
                apiGet<ProgressItem[]>("/me/progress", token),
            ]);

            const sortedModules = [...modulesRes].sort((a, b) => a.order - b.order);
            setModules(sortedModules);

            const completedIds = new Set(
                progressRes.filter((item) => item.completed).map((item) => item.lesson_id)
            );
            setCompletedLessonIds(completedIds);

            const lessonMap: Record<number, LessonOut[]> = {};

            for (const module of sortedModules) {
                const lessonsRes = await apiGet<LessonOut[]>(`/modules/${module.id}/lessons`, token);
                lessonMap[module.id] = [...lessonsRes].sort((a, b) => a.order - b.order);
            }

            setLessonsByModule(lessonMap);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load course");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        if (!courseId || Number.isNaN(courseId)) return;
        void loadCourse();
    }, [courseId]);

    const allLessons = useMemo(
        () =>
            modules.flatMap((module) => {
                const lessons = lessonsByModule[module.id] ?? [];
                return lessons.map((lesson) => ({
                    ...lesson,
                    moduleId: module.id,
                    moduleTitle: module.title,
                }));
            }),
        [modules, lessonsByModule]
    );

    const totalLessons = allLessons.length;
    const completedCount = allLessons.filter((lesson) =>
        completedLessonIds.has(lesson.id)
    ).length;
    const progressPercent =
        totalLessons > 0 ? Math.round((completedCount / totalLessons) * 100) : 0;

    const nextLesson =
        allLessons.find((lesson) => !completedLessonIds.has(lesson.id)) ?? null;

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F3F6FB",
                padding: "32px 24px",
            }}
        >
            <div style={{ maxWidth: 1200, margin: "0 auto" }}>
                <button
                    onClick={() => router.push("/dashboard")}
                    style={{
                        marginBottom: 18,
                        padding: "10px 14px",
                        borderRadius: 10,
                        border: "1px solid #E5E7EB",
                        background: "white",
                        cursor: "pointer",
                        fontWeight: 700,
                    }}
                >
                    ← Back to Dashboard
                </button>

                <section
                    style={{
                        background: "linear-gradient(120deg, #1D4ED8, #60A5FA)",
                        borderRadius: 24,
                        color: "white",
                        padding: "28px 30px",
                        boxShadow: "0 18px 40px rgba(37, 99, 235, 0.18)",
                    }}
                >
                    <div style={{ fontSize: 16, opacity: 0.9 }}>Course overview</div>
                    <h1
                        style={{
                            margin: "10px 0 8px 0",
                            fontSize: 40,
                            fontWeight: 900,
                            lineHeight: 1.1,
                        }}
                    >
                        Course {courseId}
                    </h1>
                    <div style={{ opacity: 0.95, fontSize: 17 }}>
                        Track your lesson progress and continue learning from where you left off.
                    </div>

                    <div
                        style={{
                            marginTop: 20,
                            display: "grid",
                            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                            gap: 14,
                        }}
                    >
                        <div
                            style={{
                                background: "rgba(255,255,255,0.14)",
                                borderRadius: 16,
                                padding: 16,
                            }}
                        >
                            <div style={{ fontSize: 13, opacity: 0.9 }}>Modules</div>
                            <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>
                                {loading ? "…" : modules.length}
                            </div>
                        </div>

                        <div
                            style={{
                                background: "rgba(255,255,255,0.14)",
                                borderRadius: 16,
                                padding: 16,
                            }}
                        >
                            <div style={{ fontSize: 13, opacity: 0.9 }}>Lessons completed</div>
                            <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>
                                {loading ? "…" : `${completedCount}/${totalLessons}`}
                            </div>
                        </div>

                        <div
                            style={{
                                background: "rgba(255,255,255,0.14)",
                                borderRadius: 16,
                                padding: 16,
                            }}
                        >
                            <div style={{ fontSize: 13, opacity: 0.9 }}>Progress</div>
                            <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>
                                {loading ? "…" : `${progressPercent}%`}
                            </div>
                        </div>
                    </div>

                    {!loading && nextLesson && (
                        <button
                            onClick={() => router.push(`/lessons/${nextLesson.id}`)}
                            style={{
                                marginTop: 18,
                                padding: "12px 18px",
                                borderRadius: 12,
                                border: "none",
                                background: "white",
                                color: "#1D4ED8",
                                fontWeight: 900,
                                cursor: "pointer",
                            }}
                        >
                            Continue: {nextLesson.title}
                        </button>
                    )}
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
                        background: "white",
                        border: "1px solid #E5E7EB",
                        borderRadius: 22,
                        padding: 22,
                        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
                    }}
                >
                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            gap: 12,
                            flexWrap: "wrap",
                            marginBottom: 18,
                        }}
                    >
                        <div>
                            <h2
                                style={{
                                    margin: 0,
                                    fontSize: 24,
                                    fontWeight: 900,
                                    color: "#111827",
                                }}
                            >
                                Learning Path
                            </h2>
                            <div style={{ color: "#6B7280", marginTop: 6 }}>
                                Work through each lesson in order.
                            </div>
                        </div>

                        {!loading && (
                            <div style={{ minWidth: 220 }}>
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        fontSize: 13,
                                        marginBottom: 8,
                                        color: "#6B7280",
                                    }}
                                >
                                    <span>Course progress</span>
                                    <b style={{ color: "#111827" }}>{progressPercent}%</b>
                                </div>
                                <ProgressBar value={progressPercent} />
                            </div>
                        )}
                    </div>

                    {loading && <div style={{ color: "#6B7280" }}>Loading modules and lessons...</div>}

                    {!loading && modules.length === 0 && (
                        <div style={{ color: "#6B7280" }}>No modules found for this course yet.</div>
                    )}

                    {!loading && modules.length > 0 && (
                        <div style={{ display: "grid", gap: 18 }}>
                            {modules.map((module) => {
                                const moduleLessons = lessonsByModule[module.id] ?? [];

                                return (
                                    <section
                                        key={module.id}
                                        style={{
                                            border: "1px solid #E5E7EB",
                                            borderRadius: 18,
                                            padding: 18,
                                            background: "#F9FAFB",
                                        }}
                                    >
                                        <h3
                                            style={{
                                                margin: "0 0 12px 0",
                                                fontSize: 22,
                                                fontWeight: 900,
                                                color: "#111827",
                                            }}
                                        >
                                            {module.title}
                                        </h3>

                                        <div style={{ display: "grid", gap: 12 }}>
                                            {moduleLessons.map((lesson, index) => {
                                                const isCompleted = completedLessonIds.has(lesson.id);
                                                const previousLesson =
                                                    index > 0 ? moduleLessons[index - 1] : null;
                                                const isLocked =
                                                    !!previousLesson && !completedLessonIds.has(previousLesson.id);
                                                const isNext =
                                                    !isCompleted &&
                                                    !isLocked &&
                                                    nextLesson?.id === lesson.id;

                                                return (
                                                    <button
                                                        key={lesson.id}
                                                        disabled={isLocked}
                                                        onClick={() => router.push(`/lessons/${lesson.id}`)}
                                                        style={{
                                                            width: "100%",
                                                            padding: "16px 18px",
                                                            borderRadius: 16,
                                                            border: isNext
                                                                ? "1px solid #2563EB"
                                                                : "1px solid #E5E7EB",
                                                            background: isCompleted
                                                                ? "#ECFDF5"
                                                                : isNext
                                                                    ? "#EFF6FF"
                                                                    : "white",
                                                            textAlign: "left",
                                                            cursor: isLocked ? "not-allowed" : "pointer",
                                                            opacity: isLocked ? 0.65 : 1,
                                                        }}
                                                    >
                                                        <div
                                                            style={{
                                                                display: "flex",
                                                                justifyContent: "space-between",
                                                                alignItems: "center",
                                                                gap: 12,
                                                                flexWrap: "wrap",
                                                            }}
                                                        >
                                                            <div>
                                                                <div
                                                                    style={{
                                                                        fontSize: 12,
                                                                        fontWeight: 800,
                                                                        color: "#6B7280",
                                                                    }}
                                                                >
                                                                    Lesson {lesson.order}
                                                                </div>
                                                                <div
                                                                    style={{
                                                                        marginTop: 4,
                                                                        fontSize: 17,
                                                                        fontWeight: 800,
                                                                        color: "#111827",
                                                                    }}
                                                                >
                                                                    {lesson.title}
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
                                                                {isCompleted && (
                                                                    <span
                                                                        style={{
                                                                            fontSize: 12,
                                                                            fontWeight: 800,
                                                                            color: "#166534",
                                                                            background: "#DCFCE7",
                                                                            padding: "6px 10px",
                                                                            borderRadius: 999,
                                                                        }}
                                                                    >
                                                                        ✅ Completed
                                                                    </span>
                                                                )}

                                                                {!isCompleted && isNext && (
                                                                    <span
                                                                        style={{
                                                                            fontSize: 12,
                                                                            fontWeight: 800,
                                                                            color: "#1D4ED8",
                                                                            background: "#DBEAFE",
                                                                            padding: "6px 10px",
                                                                            borderRadius: 999,
                                                                        }}
                                                                    >
                                                                        ▶ Continue here
                                                                    </span>
                                                                )}

                                                                {isLocked && (
                                                                    <span
                                                                        style={{
                                                                            fontSize: 12,
                                                                            fontWeight: 800,
                                                                            color: "#92400E",
                                                                            background: "#FEF3C7",
                                                                            padding: "6px 10px",
                                                                            borderRadius: 999,
                                                                        }}
                                                                    >
                                                                        🔒 Locked
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </section>
                                );
                            })}
                        </div>
                    )}
                </section>
            </div>
        </main>
    );
}