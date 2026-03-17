"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiPost, getToken } from "@/lib/api";

type LessonOut = {
    id: number;
    title: string;
    content: string;
    content_type: string; // "text" | "video" (or others later)
    order: number;
};

export default function LessonPage() {
    const router = useRouter();
    const params = useParams<{ lessonId: string }>();
    const lessonId = Number(params.lessonId);

    const [lesson, setLesson] = useState<LessonOut | null>(null);
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

            const res = await apiGet<LessonOut>(`/lessons/${lessonId}`, token);
            setLesson(res);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to load lesson";
            setError(msg);

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
        if (!lessonId) return;
        void loadLesson();
    }, [lessonId]);

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
                        {/* Content Renderer */}
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
                    </section>
                </>
            )}
        </main>
    );
}