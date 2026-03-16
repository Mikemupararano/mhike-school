"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiPost, getToken } from "@/lib/api";

export default function LessonPage() {
    const router = useRouter();
    const params = useParams<{ lessonId: string }>();
    const lessonId = Number(params.lessonId);

    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");

    async function markComplete() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        try {
            setLoading(true);
            setMessage("");

            await apiPost(`/lessons/${lessonId}/progress`, {}, token);
            setMessage("Lesson marked as complete.");
        } catch (err: unknown) {
            setMessage(err instanceof Error ? err.message : "Failed to update progress");
        } finally {
            setLoading(false);
        }
    }

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

            <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 8 }}>
                Lesson {lessonId}
            </h1>
            <p style={{ color: "#6B7280", marginTop: 0 }}>
                Lesson content page placeholder.
            </p>

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
                        fontSize: 60,
                    }}
                >
                    🎥
                </div>

                <div style={{ marginTop: 18, color: "#374151", lineHeight: 1.6 }}>
                    This is where your lesson video, lesson notes, text content, or downloadable
                    resources will appear.
                </div>

                <button
                    onClick={markComplete}
                    disabled={loading}
                    style={{
                        marginTop: 18,
                        padding: "12px 16px",
                        borderRadius: 12,
                        border: "none",
                        background: "#2563EB",
                        color: "white",
                        fontWeight: 800,
                        cursor: loading ? "not-allowed" : "pointer",
                        opacity: loading ? 0.75 : 1,
                    }}
                >
                    {loading ? "Saving..." : "Mark Lesson Complete"}
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
        </main>
    );
}