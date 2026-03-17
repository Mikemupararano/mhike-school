"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiPost, getToken } from "@/lib/api";

type LessonOut = {
    id: number;
    title: string;
    content: string;
    content_type: string;
    order: number;
    module_id: number;
};

type LessonListItem = {
    id: number;
    title: string;
    order: number;
};

export default function LessonPage() {
    const router = useRouter();
    const params = useParams<{ lessonId: string }>();
    const lessonId = Number(params.lessonId);

    const [lesson, setLesson] = useState<LessonOut | null>(null);
    const [lessons, setLessons] = useState<LessonListItem[]>([]);
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

            const listRes = await apiGet<LessonListItem[]>(
                `/modules/${lessonRes.module_id}/lessons`,
                token
            );
            setLessons(listRes);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to load lesson";
            setError(msg);
            setLesson(null);
            setLessons([]);

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

    const currentIndex = lessons.findIndex((l) => l.id === lesson?.id);
    const prevLesson = currentIndex > 0 ? lessons[currentIndex - 1] : null;
    const nextLesson =
        currentIndex >= 0 && currentIndex < lessons.length - 1
            ? lessons[currentIndex + 1]
            : null;

    return (
        <main style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
            <button
                onClick={() => router.push("/dashboard")}
                style={{
                    marginBottom: 16,
                    padding: "10px 14px",
                    borderRadius: 10,
                    border: "1px solid #E5E7EB",
                    background: "white",
                    cursor: "pointer",
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
                    }}
                >
                    {error}
                </div>
            )}

            {!loading && lesson && (
                <>
                    <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 8 }}>
                        {lesson.title}
                    </h1>

                    <section
                        style={{
                            marginTop: 20,
                            background: "white",
                            border: "1px solid #E5E7EB",
                            borderRadius: 18,
                            padding: 20,
                        }}
                    >
                        <div
                            style={{
                                minHeight: 220,
                                borderRadius: 16,
                                background: "#EFF6FF",
                                display: "grid",
                                placeItems: "center",
                                padding: 16,
                            }}
                        >
                            {lesson.content_type === "video" ? (
                                <video
                                    src={lesson.content}
                                    controls
                                    style={{ width: "100%", borderRadius: 12 }}
                                />
                            ) : (
                                <div
                                    style={{
                                        color: "#374151",
                                        lineHeight: 1.6,
                                        width: "100%",
                                        whiteSpace: "pre-wrap",
                                    }}
                                >
                                    {lesson.content}
                                </div>
                            )}
                        </div>

                        <button
                            onClick={markComplete}
                            disabled={saving}
                            style={{
                                marginTop: 18,
                                padding: "12px 16px",
                                borderRadius: 12,
                                border: "none",
                                background: "#2563EB",
                                color: "white",
                                fontWeight: 800,
                                cursor: saving ? "not-allowed" : "pointer",
                                opacity: saving ? 0.75 : 1,
                            }}
                        >
                            {saving ? "Saving..." : "Mark Lesson Complete"}
                        </button>

                        {message && (
                            <div
                                style={{
                                    marginTop: 14,
                                    padding: 12,
                                    borderRadius: 12,
                                    background: "#F9FAFB",
                                    border: "1px solid #E5E7EB",
                                }}
                            >
                                {message}
                            </div>
                        )}

                        <div
                            style={{
                                marginTop: 24,
                                display: "flex",
                                justifyContent: "space-between",
                                gap: 12,
                            }}
                        >
                            <button
                                disabled={!prevLesson}
                                onClick={() => prevLesson && router.push(`/lessons/${prevLesson.id}`)}
                                style={{
                                    padding: "12px 16px",
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                    background: prevLesson ? "white" : "#F3F4F6",
                                    color: "#111827",
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
                    </section>
                </>
            )}
        </main>
    );
}