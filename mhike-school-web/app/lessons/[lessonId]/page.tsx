"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiPost, getToken } from "@/lib/api";

type LessonOut = {
    id: number;
    title: string;
    content: string | null;
    content_type: string;
    order: number;
    module_id: number;
};

type LessonListItem = {
    id: number;
    title: string;
    order: number;
    published?: boolean;
};

type ProgressItem = {
    lesson_id: number;
    completed: boolean;
};

export default function LessonPage() {
    const router = useRouter();
    const params = useParams<{ lessonId: string }>();
    const lessonId = Number(params.lessonId);

    const [lesson, setLesson] = useState<LessonOut | null>(null);
    const [lessons, setLessons] = useState<LessonListItem[]>([]);
    const [completedLessonIds, setCompletedLessonIds] = useState<Set<number>>(new Set());
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    async function loadLesson() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        try {
            setLoading(true);
            setError("");
            setMessage("");

            const lessonRes = await apiGet<LessonOut>(`/lessons/${lessonId}`, token);
            setLesson(lessonRes);

            const [listRes, progressRes] = await Promise.all([
                apiGet<LessonListItem[]>(`/modules/${lessonRes.module_id}/lessons`, token),
                apiGet<ProgressItem[]>("/me/progress", token),
            ]);

            const sortedLessons = [...listRes].sort((a, b) => a.order - b.order);
            setLessons(sortedLessons);

            const completedIds = new Set(
                progressRes.filter((item) => item.completed).map((item) => item.lesson_id)
            );
            setCompletedLessonIds(completedIds);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to load lesson";
            setError(msg);
            setLesson(null);
            setLessons([]);
            setCompletedLessonIds(new Set());

            if (msg.includes("401") || msg.includes("403")) {
                router.replace("/login");
            }
        } finally {
            setLoading(false);
        }
    }

    async function markComplete() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        try {
            setSaving(true);
            setMessage("");

            await apiPost(`/lessons/${lessonId}/progress`, {}, token);

            setCompletedLessonIds((prev) => {
                const next = new Set(prev);
                next.add(lessonId);
                return next;
            });

            setMessage("Lesson marked as complete.");
        } catch (err: unknown) {
            setMessage(err instanceof Error ? err.message : "Failed to update progress");
        } finally {
            setSaving(false);
        }
    }

    useEffect(() => {
        if (!lessonId || Number.isNaN(lessonId)) return;
        void loadLesson();
    }, [lessonId]);

    const currentIndex = useMemo(
        () => lessons.findIndex((l) => l.id === lesson?.id),
        [lessons, lesson]
    );

    const prevLesson = currentIndex > 0 ? lessons[currentIndex - 1] : null;
    const nextLesson =
        currentIndex >= 0 && currentIndex < lessons.length - 1
            ? lessons[currentIndex + 1]
            : null;

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F3F6FB",
                padding: "32px 24px",
            }}
        >
            <div style={{ maxWidth: 1400, margin: "0 auto" }}>
                <button
                    onClick={() => router.push("/dashboard")}
                    style={{
                        marginBottom: 20,
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

                {loading && <div>Loading lesson...</div>}

                {error && (
                    <div
                        style={{
                            marginBottom: 16,
                            padding: 12,
                            borderRadius: 12,
                            background: "#FEF2F2",
                            color: "#991B1B",
                            border: "1px solid #FECACA",
                        }}
                    >
                        {error}
                    </div>
                )}

                {!loading && lesson && (
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "360px 1fr",
                            gap: 24,
                            alignItems: "start",
                        }}
                    >
                        <aside
                            style={{
                                background: "white",
                                border: "1px solid #E5E7EB",
                                borderRadius: 18,
                                padding: 18,
                                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
                                position: "sticky",
                                top: 24,
                            }}
                        >
                            <h2
                                style={{
                                    margin: "0 0 14px 0",
                                    fontSize: 20,
                                    fontWeight: 900,
                                    color: "#111827",
                                }}
                            >
                                Lesson Navigation
                            </h2>

                            <div style={{ color: "#6B7280", fontSize: 14, marginBottom: 14 }}>
                                Module {lesson.module_id} • {lessons.length} lessons
                            </div>

                            <div style={{ display: "grid", gap: 10 }}>
                                {lessons.map((item, index) => {
                                    const isCurrent = item.id === lesson.id;
                                    const isCompleted = completedLessonIds.has(item.id);

                                    return (
                                        <button
                                            key={item.id}
                                            onClick={() => router.push(`/lessons/${item.id}`)}
                                            style={{
                                                width: "100%",
                                                padding: "14px 14px",
                                                borderRadius: 14,
                                                border: isCurrent ? "1px solid #2563EB" : "1px solid #E5E7EB",
                                                background: isCurrent ? "#EFF6FF" : isCompleted ? "#ECFDF5" : "white",
                                                textAlign: "left",
                                                cursor: "pointer",
                                            }}
                                        >
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent: "space-between",
                                                    alignItems: "center",
                                                    gap: 8,
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        fontSize: 12,
                                                        color: isCurrent ? "#2563EB" : "#6B7280",
                                                        fontWeight: 800,
                                                    }}
                                                >
                                                    Lesson {index + 1}
                                                </div>

                                                {isCompleted && (
                                                    <span
                                                        style={{
                                                            fontSize: 11,
                                                            fontWeight: 800,
                                                            color: "#166534",
                                                            background: "#DCFCE7",
                                                            padding: "4px 8px",
                                                            borderRadius: 999,
                                                        }}
                                                    >
                                                        Completed
                                                    </span>
                                                )}
                                            </div>

                                            <div
                                                style={{
                                                    marginTop: 4,
                                                    fontWeight: isCurrent ? 800 : 700,
                                                    color: "#111827",
                                                    lineHeight: 1.4,
                                                }}
                                            >
                                                {item.title}
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </aside>

                        <section
                            style={{
                                background: "white",
                                border: "1px solid #E5E7EB",
                                borderRadius: 18,
                                padding: 28,
                                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
                            }}
                        >
                            <h1
                                style={{
                                    fontSize: 40,
                                    fontWeight: 900,
                                    margin: "0 0 10px 0",
                                    color: "#111827",
                                    lineHeight: 1.1,
                                }}
                            >
                                {lesson.title}
                            </h1>

                            <div style={{ color: "#6B7280", marginBottom: 20, fontSize: 15 }}>
                                Lesson {lesson.order} • Type: {lesson.content_type}
                            </div>

                            <div
                                style={{
                                    minHeight: 320,
                                    borderRadius: 16,
                                    background: "#EFF6FF",
                                    display: "grid",
                                    placeItems: "center",
                                    padding: 28,
                                }}
                            >
                                {lesson.content_type === "video" ? (
                                    <video
                                        src={lesson.content ?? ""}
                                        controls
                                        style={{ width: "100%", borderRadius: 12 }}
                                    />
                                ) : (
                                    <div
                                        style={{
                                            color: "#374151",
                                            lineHeight: 1.9,
                                            width: "100%",
                                            maxWidth: 900,
                                            margin: "0 auto",
                                            whiteSpace: "pre-wrap",
                                            fontSize: 18,
                                        }}
                                    >
                                        {lesson.content || "No content available for this lesson yet."}
                                    </div>
                                )}
                            </div>

                            <div
                                style={{
                                    marginTop: 20,
                                    display: "flex",
                                    gap: 12,
                                    flexWrap: "wrap",
                                }}
                            >
                                <button
                                    onClick={markComplete}
                                    disabled={saving || completedLessonIds.has(lesson.id)}
                                    style={{
                                        padding: "12px 16px",
                                        borderRadius: 12,
                                        border: "none",
                                        background: completedLessonIds.has(lesson.id) ? "#E5E7EB" : "#2563EB",
                                        color: completedLessonIds.has(lesson.id) ? "#6B7280" : "white",
                                        fontWeight: 800,
                                        cursor:
                                            saving || completedLessonIds.has(lesson.id)
                                                ? "not-allowed"
                                                : "pointer",
                                        opacity: saving ? 0.75 : 1,
                                    }}
                                >
                                    {completedLessonIds.has(lesson.id)
                                        ? "Completed"
                                        : saving
                                            ? "Saving..."
                                            : "Mark Lesson Complete"}
                                </button>

                                <button
                                    disabled={!prevLesson}
                                    onClick={() => prevLesson && router.push(`/lessons/${prevLesson.id}`)}
                                    style={{
                                        padding: "12px 16px",
                                        borderRadius: 12,
                                        border: "1px solid #E5E7EB",
                                        background: prevLesson ? "white" : "#F3F4F6",
                                        color: "#111827",
                                        fontWeight: 700,
                                        cursor: prevLesson ? "pointer" : "not-allowed",
                                    }}
                                >
                                    ← Previous
                                </button>

                                <button
                                    disabled={!nextLesson}
                                    onClick={() => nextLesson && router.push(`/lessons/${nextLesson.id}`)}
                                    style={{
                                        padding: "12px 16px",
                                        borderRadius: 12,
                                        border: "none",
                                        background: nextLesson ? "#2563EB" : "#E5E7EB",
                                        color: nextLesson ? "white" : "#6B7280",
                                        fontWeight: 800,
                                        cursor: nextLesson ? "pointer" : "not-allowed",
                                    }}
                                >
                                    Next →
                                </button>
                            </div>

                            {message && (
                                <div
                                    style={{
                                        marginTop: 14,
                                        padding: 12,
                                        borderRadius: 12,
                                        background: "#F9FAFB",
                                        border: "1px solid #E5E7EB",
                                        color: "#111827",
                                    }}
                                >
                                    {message}
                                </div>
                            )}
                        </section>
                    </div>
                )}
            </div>
        </main>
    );
}