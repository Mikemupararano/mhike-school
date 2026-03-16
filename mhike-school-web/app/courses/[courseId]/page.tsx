"use client";

import React, { useEffect, useState } from "react";
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
    published: boolean;
};

export default function CoursePage() {
    const router = useRouter();
    const params = useParams<{ courseId: string }>();
    const courseId = Number(params.courseId);

    const [modules, setModules] = useState<ModuleOut[]>([]);
    const [lessonsByModule, setLessonsByModule] = useState<Record<number, LessonOut[]>>({});
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

            const modulesRes = await apiGet<ModuleOut[]>(`/courses/${courseId}/modules`, token);
            setModules(modulesRes);

            const lessonMap: Record<number, LessonOut[]> = {};

            for (const module of modulesRes) {
                const lessonsRes = await apiGet<LessonOut[]>(`/modules/${module.id}/lessons`, token);
                lessonMap[module.id] = lessonsRes;
            }

            setLessonsByModule(lessonMap);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load course");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        if (!Number.isNaN(courseId)) {
            void loadCourse();
        }
    }, [courseId]);

    return (
        <main style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
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
                Course Overview
            </h1>
            <p style={{ color: "#6B7280", marginTop: 0 }}>Course ID: {courseId}</p>

            {loading && <p>Loading modules and lessons...</p>}
            {error && <p style={{ color: "#991B1B" }}>{error}</p>}

            {!loading && !error && (
                <div style={{ display: "grid", gap: 18 }}>
                    {modules.map((module) => (
                        <section
                            key={module.id}
                            style={{
                                background: "white",
                                border: "1px solid #E5E7EB",
                                borderRadius: 18,
                                padding: 20,
                            }}
                        >
                            <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>
                                {module.title}
                            </h2>

                            <div style={{ marginTop: 14, display: "grid", gap: 10 }}>
                                {(lessonsByModule[module.id] ?? []).map((lesson) => (
                                    <button
                                        key={lesson.id}
                                        onClick={() => router.push(`/lessons/${lesson.id}`)}
                                        style={{
                                            padding: "14px 16px",
                                            borderRadius: 12,
                                            border: "1px solid #E5E7EB",
                                            background: "white",
                                            textAlign: "left",
                                            cursor: "pointer",
                                            fontWeight: 700,
                                        }}
                                    >
                                        {lesson.title}
                                    </button>
                                ))}
                            </div>
                        </section>
                    ))}
                </div>
            )}
        </main>
    );
}