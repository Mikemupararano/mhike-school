"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
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

type AuthMeOut = {
    id: number;
    full_name?: string | null;
    email: string;
    role: "student" | "teacher" | "admin" | string;
    school_id?: number | null;
    school_name?: string | null;
    is_active?: boolean;
};

function cardStyle(): React.CSSProperties {
    return {
        background: "#FFFFFF",
        border: "1px solid #E5E7EB",
        borderRadius: 20,
        padding: 18,
        boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
    };
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
                ...cardStyle(),
                minHeight: 110,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
            }}
        >
            <div style={{ color: "#6B7280", fontSize: 13 }}>{label}</div>
            <div style={{ fontSize: 30, fontWeight: 900, color: "#0F172A" }}>{value}</div>
        </div>
    );
}

function SectionCard({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <section style={cardStyle()}>
            <h2
                style={{
                    marginTop: 0,
                    marginBottom: 14,
                    fontSize: 22,
                    fontWeight: 900,
                    color: "#0F172A",
                }}
            >
                {title}
            </h2>
            {children}
        </section>
    );
}

export default function TeacherPage() {
    const router = useRouter();
    const { user, loading: authLoading, refreshUser, logout } = useAuth();

    const [me, setMe] = useState<AuthMeOut | null>(null);
    const [courses, setCourses] = useState<CourseOut[]>([]);
    const [selectedCourse, setSelectedCourse] = useState<CourseOut | null>(null);
    const [modules, setModules] = useState<ModuleOut[]>([]);
    const [selectedModule, setSelectedModule] = useState<ModuleOut | null>(null);
    const [lessons, setLessons] = useState<LessonOut[]>([]);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const [loading, setLoading] = useState(true);

    const [courseTitle, setCourseTitle] = useState("");
    const [courseDesc, setCourseDesc] = useState("");

    const [moduleTitle, setModuleTitle] = useState("");
    const [moduleOrder, setModuleOrder] = useState(1);

    const [lessonTitle, setLessonTitle] = useState("");
    const [lessonType, setLessonType] = useState<"text" | "video" | "pdf" | "link">("text");
    const [lessonContent, setLessonContent] = useState("");
    const [lessonOrder, setLessonOrder] = useState(1);

    const displayName = useMemo(() => {
        return me?.full_name?.trim() || user?.full_name?.trim() || "Teacher";
    }, [me, user]);

    const displaySchoolName = useMemo(() => {
        return me?.school_name?.trim() || user?.school_name?.trim() || "Your School";
    }, [me, user]);

    const displayInitial = useMemo(() => {
        return displayName.charAt(0).toUpperCase();
    }, [displayName]);

    async function loadCourses() {
        const data = await getMyCourses();
        setCourses(data);
        setSelectedCourse((prev) => {
            if (!data.length) return null;
            if (prev) {
                const match = data.find((c) => c.id === prev.id);
                if (match) return match;
            }
            return data[0];
        });
    }

    async function loadModules(courseId: number) {
        const data = await listModules(courseId);
        setModules(data);
        setSelectedModule((prev) => {
            if (!data.length) return null;
            if (prev) {
                const match = data.find((m) => m.id === prev.id);
                if (match) return match;
            }
            return data[0];
        });
    }

    async function loadLessons(moduleId: number) {
        const data = await listLessons(moduleId);
        setLessons(data);
    }

    useEffect(() => {
        async function init() {
            if (authLoading) return;

            setLoading(true);
            setError("");

            try {
                const currentUser = await refreshUser();

                if (!currentUser) {
                    router.replace("/login");
                    return;
                }

                if (currentUser.role === "admin") {
                    router.replace("/admin");
                    return;
                }

                if (currentUser.role === "student") {
                    router.replace("/dashboard");
                    return;
                }

                if (currentUser.role !== "teacher") {
                    setError("Unsupported user role.");
                    return;
                }

                if (currentUser.is_active === false) {
                    logout();
                    router.replace("/login");
                    return;
                }

                setMe(currentUser as AuthMeOut);
                await loadCourses();
            } catch (e: unknown) {
                const message =
                    e instanceof Error ? e.message : "Failed to load teacher dashboard";
                setError(message);

                if (
                    message.includes("401") ||
                    message.includes("403") ||
                    message.toLowerCase().includes("forbidden")
                ) {
                    logout();
                    router.replace("/login");
                    return;
                }
            } finally {
                setLoading(false);
            }
        }

        void init();
    }, [authLoading, refreshUser, router, logout]);

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

    useEffect(() => {
        if (!user || !me) return;

        if (
            user.role === "teacher" &&
            user.school_id != null &&
            me.school_id != null &&
            user.school_id !== me.school_id
        ) {
            logout();
            router.replace("/login");
        }
    }, [user, me, logout, router]);

    const courseStats = useMemo(() => {
        const published = courses.filter((c) => c.published).length;
        return {
            total: courses.length,
            published,
            drafts: Math.max(0, courses.length - published),
        };
    }, [courses]);

    async function onCreateCourse() {
        if (!courseTitle.trim()) return;

        setBusy(true);
        setError("");

        try {
            await createCourse({
                title: courseTitle,
                description: courseDesc || null,
            });
            setCourseTitle("");
            setCourseDesc("");
            await loadCourses();
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to create course");
        } finally {
            setBusy(false);
        }
    }

    async function onPublishCourse() {
        if (!selectedCourse) return;

        setBusy(true);
        setError("");

        try {
            const updated = await publishCourse(selectedCourse.id);
            setSelectedCourse(updated);
            await loadCourses();
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to publish course");
        } finally {
            setBusy(false);
        }
    }

    async function onCreateModule() {
        if (!selectedCourse || !moduleTitle.trim()) return;

        setBusy(true);
        setError("");

        try {
            await createModule(selectedCourse.id, {
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
        if (!selectedModule || !lessonTitle.trim()) return;

        setBusy(true);
        setError("");

        try {
            await createLesson(selectedModule.id, {
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

    if (authLoading || loading) {
        return (
            <main style={{ maxWidth: 1280, margin: "0 auto", padding: 24 }}>
                <div style={cardStyle()}>
                    <div style={{ fontSize: 18, fontWeight: 800 }}>
                        Loading teacher dashboard...
                    </div>
                </div>
            </main>
        );
    }

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F1F5F9",
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
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 10,
                            padding: "8px 12px",
                            borderRadius: 999,
                            background: "rgba(255,255,255,0.12)",
                            border: "1px solid rgba(255,255,255,0.18)",
                        }}
                    >
                        <div
                            style={{
                                width: 30,
                                height: 30,
                                borderRadius: "50%",
                                background: "#DBEAFE",
                                color: "#1D4ED8",
                                display: "grid",
                                placeItems: "center",
                                fontWeight: 900,
                            }}
                        >
                            {displayInitial}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
                            <span style={{ fontWeight: 700 }}>{displayName}</span>
                            <span style={{ fontSize: 12, opacity: 0.85 }}>{displaySchoolName}</span>
                        </div>
                    </div>

                    <button
                        onClick={() => void loadCourses()}
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
                        onClick={() => router.push("/dashboard")}
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
                        Student view
                    </button>

                    <button
                        onClick={() => {
                            logout();
                            router.replace("/login");
                        }}
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
                        padding: "24px 30px",
                        display: "grid",
                        gridTemplateColumns: "1.4fr 1fr",
                        gap: 24,
                        alignItems: "center",
                        boxShadow: "0 18px 40px rgba(37, 99, 235, 0.2)",
                    }}
                >
                    <div>
                        <div style={{ fontSize: 18, opacity: 0.9 }}>
                            {displaySchoolName} · Teacher dashboard
                        </div>
                        <h1
                            style={{
                                fontSize: 44,
                                lineHeight: 1.1,
                                margin: "12px 0 10px 0",
                                fontWeight: 900,
                            }}
                        >
                            Welcome back, {displayName}!
                        </h1>

                        <p style={{ fontSize: 18, margin: 0, opacity: 0.95 }}>
                            Create courses, organize modules, and build lessons for your learners.
                        </p>
                    </div>

                    <div
                        style={{
                            minHeight: 190,
                            borderRadius: 24,
                            background:
                                "radial-gradient(circle at top right, rgba(255,255,255,0.35), rgba(255,255,255,0.08))",
                            display: "grid",
                            placeItems: "center",
                            fontSize: 90,
                        }}
                    >
                        🧑‍🏫
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
                    <StatCard label="My courses" value={courseStats.total} />
                    <StatCard label="Published" value={courseStats.published} />
                    <StatCard
                        label="Next action"
                        value={
                            courses.length === 0 ? "Create your first course" : "Add modules and lessons"
                        }
                    />
                </section>

                <section
                    style={{
                        marginTop: 22,
                        display: "grid",
                        gridTemplateColumns: "1fr 2fr",
                        gap: 18,
                    }}
                >
                    <SectionCard title="Create course">
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
                                    border: "none",
                                    background: "#2563EB",
                                    color: "white",
                                    fontWeight: 900,
                                    cursor: "pointer",
                                    opacity: busy || !courseTitle.trim() ? 0.7 : 1,
                                }}
                            >
                                Create
                            </button>
                        </div>
                    </SectionCard>

                    <SectionCard title="My courses">
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

                                <div
                                    style={{
                                        display: "flex",
                                        gap: 10,
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        flexWrap: "wrap",
                                    }}
                                >
                                    <div style={{ color: "#6B7280" }}>
                                        {selectedCourse?.description ?? "No description"}
                                    </div>
                                    <button
                                        disabled={busy || !selectedCourse || selectedCourse.published}
                                        onClick={onPublishCourse}
                                        style={{
                                            padding: "10px 12px",
                                            borderRadius: 12,
                                            border: "none",
                                            background: "#2563EB",
                                            color: "white",
                                            fontWeight: 900,
                                            cursor: "pointer",
                                            opacity:
                                                busy || !selectedCourse || selectedCourse.published ? 0.7 : 1,
                                        }}
                                    >
                                        Publish
                                    </button>
                                </div>
                            </div>
                        )}
                    </SectionCard>
                </section>

                <section
                    style={{
                        marginTop: 22,
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr 1fr",
                        gap: 18,
                    }}
                >
                    <SectionCard title="Modules">
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
                                            border: "none",
                                            background: "#2563EB",
                                            color: "white",
                                            fontWeight: 900,
                                            cursor: "pointer",
                                            opacity: busy || !moduleTitle.trim() ? 0.7 : 1,
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
                                        <option value="">Choose module</option>
                                        {modules.map((m) => (
                                            <option key={m.id} value={m.id}>
                                                {m.order}. {m.title}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </>
                        )}
                    </SectionCard>

                    <SectionCard title="Lessons">
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
                                    onChange={(e) =>
                                        setLessonType(
                                            e.target.value as "text" | "video" | "pdf" | "link"
                                        )
                                    }
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
                                        border: "none",
                                        background: "#2563EB",
                                        color: "white",
                                        fontWeight: 900,
                                        cursor: "pointer",
                                        opacity: busy || !lessonTitle.trim() ? 0.7 : 1,
                                    }}
                                >
                                    Add lesson
                                </button>
                            </div>
                        )}
                    </SectionCard>

                    <SectionCard title="Preview">
                        {!selectedCourse ? (
                            <div style={{ color: "#6B7280" }}>
                                Select a course to see its content.
                            </div>
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
                                    <div style={{ fontSize: 12, color: "#6B7280" }}>
                                        Lessons in selected module
                                    </div>
                                    <ul style={{ paddingLeft: 18 }}>
                                        {lessons.map((l) => (
                                            <li key={l.id}>
                                                {l.order}. {l.title}{" "}
                                                <span style={{ color: "#6B7280" }}>
                                                    ({l.content_type})
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </>
                        )}
                    </SectionCard>
                </section>
            </div>
        </main>
    );
}