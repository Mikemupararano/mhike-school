"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import {
    CourseOut,
    ModuleOut,
    LessonOut,
    getCourse,
    listModules,
    listLessons,
    enrollInCourse,
} from "@/lib/courseApi";

type ProgressItem = {
    lesson_id: number;
    completed: boolean;
};

type LessonsByModule = Record<number, LessonOut[]>;

type FlatLesson = LessonOut & {
    moduleId: number;
    moduleTitle: string;
};

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

export default function CourseDetailPage() {
    const params = useParams();
    const router = useRouter();

    const rawCourseId = params?.courseId;
    const courseId = Number(Array.isArray(rawCourseId) ? rawCourseId[0] : rawCourseId);

    const [token, setToken] = useState("");
    const [course, setCourse] = useState<CourseOut | null>(null);
    const [modules, setModules] = useState<ModuleOut[]>([]);
    const [lessonsByModule, setLessonsByModule] = useState<LessonsByModule>({});
    const [completedLessonIds, setCompletedLessonIds] = useState<Set<number>>(new Set());
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    useEffect(() => {
        const t = getToken();
        if (t) {
            setToken(t);
        }
    }, []);

    const loadCourse = useCallback(async () => {
        if (!Number.isFinite(courseId) || courseId <= 0) {
            setError("Invalid course ID.");
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError("");

            const courseData = await getCourse(courseId, token || undefined);
            setCourse(courseData);

            const moduleData = await listModules(courseId, token || undefined);
            const sortedModules = [...moduleData].sort((a, b) => a.order - b.order);
            setModules(sortedModules);

            const lessonEntries = await Promise.all(
                sortedModules.map(async (module) => {
                    const lessons = await listLessons(module.id, token || undefined);
                    const sortedLessons = [...lessons]
                        .filter((lesson) => lesson.published !== false)
                        .sort((a, b) => a.order - b.order);

                    return [module.id, sortedLessons] as const;
                }),
            );

            const lessonMap: LessonsByModule = Object.fromEntries(lessonEntries);
            setLessonsByModule(lessonMap);

            if (token) {
                try {
                    const res = await fetch(
                        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/me/progress`,
                        {
                            headers: {
                                Authorization: `Bearer ${token}`,
                            },
                        },
                    );

                    if (res.ok) {
                        const progressData = (await res.json()) as ProgressItem[];
                        const completedIds = new Set(
                            progressData.filter((item) => item.completed).map((item) => item.lesson_id),
                        );
                        setCompletedLessonIds(completedIds);
                    } else {
                        setCompletedLessonIds(new Set());
                    }
                } catch {
                    setCompletedLessonIds(new Set());
                }
            } else {
                setCompletedLessonIds(new Set());
            }
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load course");
        } finally {
            setLoading(false);
        }
    }, [courseId, token]);

    useEffect(() => {
        void loadCourse();
    }, [loadCourse]);

    const allLessons = useMemo<FlatLesson[]>(
        () =>
            modules.flatMap((module) => {
                const lessons = lessonsByModule[module.id] ?? [];
                return lessons.map((lesson) => ({
                    ...lesson,
                    moduleId: module.id,
                    moduleTitle: module.title,
                }));
            }),
        [modules, lessonsByModule],
    );

    const stats = useMemo(() => {
        return {
            modules: modules.length,
            lessons: allLessons.length,
        };
    }, [modules.length, allLessons.length]);

    const completedCount = useMemo(
        () => allLessons.filter((lesson) => completedLessonIds.has(lesson.id)).length,
        [allLessons, completedLessonIds],
    );

    const progressPercent =
        allLessons.length > 0 ? Math.round((completedCount / allLessons.length) * 100) : 0;

    const nextLesson = allLessons.find((lesson) => !completedLessonIds.has(lesson.id)) ?? null;

    const previousLessonIdByLessonId = useMemo(() => {
        const map = new Map<number, number | null>();

        allLessons.forEach((lesson, index) => {
            map.set(lesson.id, index > 0 ? allLessons[index - 1].id : null);
        });

        return map;
    }, [allLessons]);

    async function onEnroll() {
        if (!token) {
            router.push("/login");
            return;
        }

        if (!Number.isFinite(courseId) || courseId <= 0) {
            setError("Invalid course ID.");
            return;
        }

        try {
            setBusy(true);
            setError("");
            setSuccess("");
            await enrollInCourse(token, courseId);
            setSuccess("Successfully enrolled in course.");
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to enroll");
        } finally {
            setBusy(false);
        }
    }

    if (loading) {
        return (
            <main style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
                <p>Loading course...</p>
                {error && <p style={{ color: "#991B1B" }}>{error}</p>}
            </main>
        );
    }

    if (!course) {
        return (
            <main style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
                <p>Course not found.</p>
                {error && <p style={{ color: "#991B1B" }}>{error}</p>}
            </main>
        );
    }

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F3F6FB",
                padding: "32px 24px",
            }}
        >
            <div style={{ maxWidth: 1000, margin: "0 auto" }}>
                <div style={{ marginBottom: 16 }}>
                    <button
                        type="button"
                        onClick={() => router.push("/courses")}
                        style={{
                            padding: "10px 14px",
                            borderRadius: 12,
                            border: "1px solid #E5E7EB",
                            background: "white",
                            fontWeight: 700,
                            cursor: "pointer",
                        }}
                    >
                        ← Back to courses
                    </button>
                </div>

                <section
                    style={{
                        background: "linear-gradient(120deg, #1D4ED8, #60A5FA)",
                        borderRadius: 24,
                        color: "white",
                        padding: "28px 30px",
                        boxShadow: "0 18px 40px rgba(37, 99, 235, 0.18)",
                    }}
                >
                    <div
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            gap: 16,
                            alignItems: "flex-start",
                            flexWrap: "wrap",
                        }}
                    >
                        <div>
                            <div style={{ fontSize: 16, opacity: 0.9 }}>Course overview</div>

                            <h1
                                style={{
                                    margin: "10px 0 8px 0",
                                    fontSize: 34,
                                    fontWeight: 900,
                                    lineHeight: 1.1,
                                }}
                            >
                                {course.title}
                            </h1>

                            <p style={{ opacity: 0.95, fontSize: 16, margin: 0 }}>
                                {course.description || "No course description yet."}
                            </p>

                            <div style={{ display: "flex", gap: 12, marginTop: 14, flexWrap: "wrap" }}>
                                <span
                                    style={{
                                        padding: "6px 10px",
                                        borderRadius: 999,
                                        background: course.published ? "#DCFCE7" : "#FEF3C7",
                                        color: "#111827",
                                        fontWeight: 700,
                                        fontSize: 12,
                                    }}
                                >
                                    {course.published ? "Published" : "Draft"}
                                </span>
                                <span style={{ fontSize: 14, opacity: 0.95 }}>{stats.modules} modules</span>
                                <span style={{ fontSize: 14, opacity: 0.95 }}>{stats.lessons} lessons</span>
                                <span style={{ fontSize: 14, opacity: 0.95 }}>{progressPercent}% progress</span>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={onEnroll}
                            disabled={busy}
                            style={{
                                padding: "12px 16px",
                                borderRadius: 12,
                                border: "1px solid white",
                                background: "white",
                                color: "#1D4ED8",
                                fontWeight: 800,
                                cursor: busy ? "wait" : "pointer",
                            }}
                        >
                            {busy ? "Enrolling..." : "Enroll"}
                        </button>
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
                            <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>{stats.modules}</div>
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
                                {`${completedCount}/${allLessons.length}`}
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
                                {`${progressPercent}%`}
                            </div>
                        </div>
                    </div>

                    {nextLesson && (
                        <button
                            type="button"
                            onClick={() => router.push(`/courses/${course.id}/lessons/${nextLesson.id}`)}
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

                {success && (
                    <div
                        style={{
                            marginTop: 18,
                            padding: 14,
                            borderRadius: 14,
                            background: "#ECFDF5",
                            color: "#065F46",
                            border: "1px solid #A7F3D0",
                        }}
                    >
                        {success}
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
                    </div>

                    {modules.length === 0 ? (
                        <Card>
                            <div style={{ color: "#6B7280" }}>No modules added yet.</div>
                        </Card>
                    ) : (
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
                                        <div style={{ marginBottom: 12 }}>
                                            <div style={{ color: "#6B7280", fontSize: 12 }}>
                                                Module {module.order}
                                            </div>
                                            <h2 style={{ margin: "6px 0 0 0", color: "#111827" }}>{module.title}</h2>
                                        </div>

                                        {moduleLessons.length === 0 ? (
                                            <div style={{ color: "#6B7280" }}>No lessons in this module yet.</div>
                                        ) : (
                                            <div style={{ display: "grid", gap: 12 }}>
                                                {moduleLessons.map((lesson) => {
                                                    const isCompleted = completedLessonIds.has(lesson.id);
                                                    const previousLessonId = previousLessonIdByLessonId.get(lesson.id) ?? null;
                                                    const isLocked =
                                                        previousLessonId !== null && !completedLessonIds.has(previousLessonId);
                                                    const isNext =
                                                        !isCompleted && !isLocked && nextLesson?.id === lesson.id;

                                                    return (
                                                        <Link
                                                            key={lesson.id}
                                                            href={
                                                                isLocked
                                                                    ? "#"
                                                                    : `/courses/${course.id}/lessons/${lesson.id}`
                                                            }
                                                            onClick={(event) => {
                                                                if (isLocked) {
                                                                    event.preventDefault();
                                                                }
                                                            }}
                                                            aria-disabled={isLocked}
                                                            style={{
                                                                display: "flex",
                                                                justifyContent: "space-between",
                                                                alignItems: "center",
                                                                gap: 12,
                                                                flexWrap: "wrap",
                                                                textDecoration: "none",
                                                                color: "inherit",
                                                                border: isNext
                                                                    ? "1px solid #2563EB"
                                                                    : "1px solid #E5E7EB",
                                                                borderRadius: 16,
                                                                padding: "16px 18px",
                                                                background: isCompleted
                                                                    ? "#ECFDF5"
                                                                    : isNext
                                                                        ? "#EFF6FF"
                                                                        : "white",
                                                                cursor: isLocked ? "not-allowed" : "pointer",
                                                                opacity: isLocked ? 0.65 : 1,
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

                                                                {"content_type" in lesson && lesson.content_type ? (
                                                                    <div
                                                                        style={{
                                                                            color: "#6B7280",
                                                                            fontSize: 13,
                                                                            marginTop: 4,
                                                                        }}
                                                                    >
                                                                        Type: {String(lesson.content_type)}
                                                                    </div>
                                                                ) : null}
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

                                                                {!isLocked && !isCompleted && !isNext && (
                                                                    <span
                                                                        style={{
                                                                            color: "#2563EB",
                                                                            fontWeight: 800,
                                                                            fontSize: 14,
                                                                        }}
                                                                    >
                                                                        Open lesson
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </Link>
                                                    );
                                                })}
                                            </div>
                                        )}
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