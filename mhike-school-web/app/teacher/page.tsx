"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, clearToken } from "@/lib/api";
import {
    CourseOut,
    ModuleOut,
    LessonOut,
    getMyCourses,
    createCourse,
    publishCourse,
    listModules,
    createModule,
    listLessons,
    createLesson,
} from "@/lib/teacherApi";

function Card({ children }: { children: React.ReactNode }) {
    return (
        <div
            style={{
                padding: 16,
                borderRadius: 16,
                border: "1px solid #E5E7EB",
                background: "white",
            }}
        >
            {children}
        </div>
    );
}

export default function TeacherPage() {
    const router = useRouter();
    const [token, setToken] = useState("");

    const [courses, setCourses] = useState<CourseOut[]>([]);
    const [selectedCourse, setSelectedCourse] = useState<CourseOut | null>(null);

    const [modules, setModules] = useState<ModuleOut[]>([]);
    const [selectedModule, setSelectedModule] = useState<ModuleOut | null>(null);

    const [lessons, setLessons] = useState<LessonOut[]>([]);

    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    const [courseTitle, setCourseTitle] = useState("");
    const [courseDesc, setCourseDesc] = useState("");

    const [moduleTitle, setModuleTitle] = useState("");
    const [moduleOrder, setModuleOrder] = useState(1);

    const [lessonTitle, setLessonTitle] = useState("");
    const [lessonType, setLessonType] = useState<"text" | "video" | "pdf" | "link">("text");
    const [lessonContent, setLessonContent] = useState("");
    const [lessonOrder, setLessonOrder] = useState(1);

    useEffect(() => {
        const t = getToken();
        if (!t) {
            router.push("/login");
            return;
        }
        setToken(t);
    }, [router]);

    async function loadCourses(t: string) {
        setError("");
        const data = await getMyCourses(t);
        setCourses(data);
        setSelectedCourse(data[0] ?? null);
    }

    async function loadModules(courseId: number) {
        const data = await listModules(courseId, token);
        setModules(data);
        setSelectedModule(data[0] ?? null);
    }

    async function loadLessons(moduleId: number) {
        const data = await listLessons(moduleId, token);
        setLessons(data);
    }

    useEffect(() => {
        if (!token) return;
        (async () => {
            try {
                await loadCourses(token);
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to load teacher dashboard");
            }
        })();
    }, [token]);

    useEffect(() => {
        if (!selectedCourse) {
            setModules([]);
            setSelectedModule(null);
            setLessons([]);
            return;
        }
        (async () => {
            try {
                await loadModules(selectedCourse.id);
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to load modules");
            }
        })();
    }, [selectedCourse]);

    useEffect(() => {
        if (!selectedModule) {
            setLessons([]);
            return;
        }
        (async () => {
            try {
                await loadLessons(selectedModule.id);
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to load lessons");
            }
        })();
    }, [selectedModule]);

    const courseStats = useMemo(() => {
        const published = courses.filter((c) => c.published).length;
        return { total: courses.length, published };
    }, [courses]);

    async function onCreateCourse() {
        if (!token) return;
        setBusy(true);
        setError("");
        try {
            await createCourse(token, {
                title: courseTitle,
                description: courseDesc || null,
            });
            setCourseTitle("");
            setCourseDesc("");
            await loadCourses(token);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to create course");
        } finally {
            setBusy(false);
        }
    }

    async function onPublishCourse() {
        if (!token || !selectedCourse) return;
        setBusy(true);
        setError("");
        try {
            const updated = await publishCourse(token, selectedCourse.id);
            setSelectedCourse(updated);
            await loadCourses(token);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to publish course");
        } finally {
            setBusy(false);
        }
    }

    async function onCreateModule() {
        if (!token || !selectedCourse) return;
        setBusy(true);
        setError("");
        try {
            await createModule(token, selectedCourse.id, {
                title: moduleTitle,
                order: moduleOrder,
            });
            setModuleTitle("");
            setModuleOrder(1);
            await loadModules(selectedCourse.id);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to create module");
        } finally {
            setBusy(false);
        }
    }

    async function onCreateLesson() {
        if (!token || !selectedModule) return;
        setBusy(true);
        setError("");
        try {
            await createLesson(token, selectedModule.id, {
                title: lessonTitle,
                content_type: lessonType,
                content: lessonContent || null,
                order: lessonOrder,
            });
            setLessonTitle("");
            setLessonContent("");
            setLessonOrder(1);
            await loadLessons(selectedModule.id);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to create lesson");
        } finally {
            setBusy(false);
        }
    }

    return (
        <main style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
            <header
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-end",
                    gap: 12,
                }}
            >
                <div>
                    <h1 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>
                        Mhike School • Teacher
                    </h1>
                    <p style={{ color: "#6B7280", marginTop: 6 }}>
                        Create courses, modules, and lessons
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
                        Student view
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
                    marginTop: 16,
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: 14,
                }}
            >
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>My courses</div>
                    <div style={{ fontSize: 26, fontWeight: 900 }}>{courseStats.total}</div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Published</div>
                    <div style={{ fontSize: 26, fontWeight: 900 }}>{courseStats.published}</div>
                </Card>
                <Card>
                    <div style={{ color: "#6B7280", fontSize: 12 }}>Next action</div>
                    <div style={{ fontSize: 16, fontWeight: 900, marginTop: 6 }}>
                        {courses.length === 0 ? "Create your first course" : "Add modules & lessons"}
                    </div>
                </Card>
            </section>

            <section
                style={{
                    marginTop: 16,
                    display: "grid",
                    gridTemplateColumns: "1fr 2fr",
                    gap: 14,
                }}
            >
                <Card>
                    <h2 style={{ marginTop: 0 }}>Create course</h2>
                    <div style={{ display: "grid", gap: 8 }}>
                        <input
                            value={courseTitle}
                            onChange={(e) => setCourseTitle(e.target.value)}
                            placeholder="Course title"
                            style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                        />
                        <textarea
                            value={courseDesc}
                            onChange={(e) => setCourseDesc(e.target.value)}
                            placeholder="Description (optional)"
                            rows={3}
                            style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                        />
                        <button
                            disabled={busy || !courseTitle.trim()}
                            onClick={onCreateCourse}
                            style={{
                                padding: 12,
                                borderRadius: 12,
                                border: "1px solid #E5E7EB",
                                background: "#111827",
                                color: "white",
                                fontWeight: 900,
                            }}
                        >
                            Create
                        </button>
                    </div>
                </Card>

                <Card>
                    <h2 style={{ marginTop: 0 }}>My courses</h2>

                    {courses.length === 0 ? (
                        <div style={{ color: "#6B7280" }}>No courses yet.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 10 }}>
                            <select
                                value={selectedCourse?.id ?? ""}
                                onChange={(e) => {
                                    const id = Number(e.target.value);
                                    setSelectedCourse(courses.find((c) => c.id === id) ?? null);
                                }}
                                style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                            >
                                {courses.map((c) => (
                                    <option key={c.id} value={c.id}>
                                        {c.title} {c.published ? "(Published)" : "(Draft)"}
                                    </option>
                                ))}
                            </select>

                            <div style={{ display: "flex", gap: 10, justifyContent: "space-between" }}>
                                <div style={{ color: "#6B7280" }}>
                                    {selectedCourse?.description ?? "No description"}
                                </div>
                                <button
                                    disabled={busy || !selectedCourse || selectedCourse.published}
                                    onClick={onPublishCourse}
                                    style={{
                                        padding: "10px 12px",
                                        borderRadius: 12,
                                        border: "1px solid #E5E7EB",
                                        background: "#2563EB",
                                        color: "white",
                                        fontWeight: 900,
                                    }}
                                >
                                    Publish
                                </button>
                            </div>
                        </div>
                    )}
                </Card>
            </section>

            <section
                style={{
                    marginTop: 16,
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 14,
                }}
            >
                <Card>
                    <h2 style={{ marginTop: 0 }}>Modules</h2>
                    {!selectedCourse ? (
                        <div style={{ color: "#6B7280" }}>Select a course.</div>
                    ) : (
                        <>
                            <div style={{ display: "grid", gap: 8 }}>
                                <input
                                    value={moduleTitle}
                                    onChange={(e) => setModuleTitle(e.target.value)}
                                    placeholder="Module title"
                                    style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                                />
                                <input
                                    value={moduleOrder}
                                    onChange={(e) => setModuleOrder(Number(e.target.value))}
                                    type="number"
                                    min={1}
                                    style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                                />
                                <button
                                    disabled={busy || !moduleTitle.trim()}
                                    onClick={onCreateModule}
                                    style={{
                                        padding: 12,
                                        borderRadius: 12,
                                        border: "1px solid #E5E7EB",
                                        background: "#111827",
                                        color: "white",
                                        fontWeight: 900,
                                    }}
                                >
                                    Add module
                                </button>
                            </div>

                            <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
                                <div style={{ fontSize: 12, color: "#6B7280" }}>Select module</div>
                                <select
                                    value={selectedModule?.id ?? ""}
                                    onChange={(e) => {
                                        const id = Number(e.target.value);
                                        setSelectedModule(modules.find((m) => m.id === id) ?? null);
                                    }}
                                    style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                                >
                                    {modules.map((m) => (
                                        <option key={m.id} value={m.id}>
                                            {m.order}. {m.title}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </>
                    )}
                </Card>

                <Card>
                    <h2 style={{ marginTop: 0 }}>Lessons</h2>
                    {!selectedModule ? (
                        <div style={{ color: "#6B7280" }}>Select a module.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 8 }}>
                            <input
                                value={lessonTitle}
                                onChange={(e) => setLessonTitle(e.target.value)}
                                placeholder="Lesson title"
                                style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                            />
                            <select
                                value={lessonType}
                                onChange={(e) => setLessonType(e.target.value as "text" | "video" | "pdf" | "link")}
                                style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                            >
                                <option value="text">text</option>
                                <option value="video">video</option>
                                <option value="pdf">pdf</option>
                                <option value="link">link</option>
                            </select>

                            <textarea
                                value={lessonContent}
                                onChange={(e) => setLessonContent(e.target.value)}
                                placeholder="Content (text) or URL (video/pdf/link)"
                                rows={4}
                                style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                            />

                            <input
                                value={lessonOrder}
                                onChange={(e) => setLessonOrder(Number(e.target.value))}
                                type="number"
                                min={1}
                                style={{ padding: 12, borderRadius: 12, border: "1px solid #E5E7EB" }}
                            />

                            <button
                                disabled={busy || !lessonTitle.trim()}
                                onClick={onCreateLesson}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                    background: "#111827",
                                    color: "white",
                                    fontWeight: 900,
                                }}
                            >
                                Add lesson
                            </button>
                        </div>
                    )}
                </Card>

                <Card>
                    <h2 style={{ marginTop: 0 }}>Preview</h2>
                    {!selectedCourse ? (
                        <div style={{ color: "#6B7280" }}>Select a course to see its content.</div>
                    ) : (
                        <>
                            <div style={{ fontWeight: 900 }}>{selectedCourse.title}</div>
                            <div style={{ color: "#6B7280", marginTop: 6 }}>
                                {selectedCourse.published ? "Published" : "Draft"}
                            </div>

                            <div style={{ marginTop: 12 }}>
                                <div style={{ fontSize: 12, color: "#6B7280" }}>Modules</div>
                                <ul style={{ paddingLeft: 18 }}>
                                    {modules.map((m) => (
                                        <li key={m.id}>
                                            {m.order}. {m.title}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            <div style={{ marginTop: 12 }}>
                                <div style={{ fontSize: 12, color: "#6B7280" }}>Lessons in selected module</div>
                                <ul style={{ paddingLeft: 18 }}>
                                    {lessons.map((l) => (
                                        <li key={l.id}>
                                            {l.order}. {l.title}{" "}
                                            <span style={{ color: "#6B7280" }}>({l.content_type})</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </>
                    )}
                </Card>
            </section>
        </main>
    );
}