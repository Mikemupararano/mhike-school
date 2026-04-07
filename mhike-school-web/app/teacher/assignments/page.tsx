"use client";

import React, { useEffect, useMemo, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { getMyCourses, CourseOut } from "@/lib/teacherApi";
import {
    AssignmentOut,
    createAssignment,
    deleteAssignment,
    getMyTeacherAssignments,
    publishAssignment,
} from "@/lib/assignmentApi";

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

type AuthMeOut = {
    id: number;
    full_name?: string | null;
    email: string;
    role: "student" | "teacher" | "admin" | "platform_admin" | string;
    school_id?: number | null;
    school_name?: string | null;
    is_active?: boolean;
};

export default function TeacherAssignmentsPage() {
    const router = useRouter();
    const { user, loading: authLoading, refreshUser, logout } = useAuth();

    const [me, setMe] = useState<AuthMeOut | null>(null);
    const [courses, setCourses] = useState<CourseOut[]>([]);
    const [assignments, setAssignments] = useState<AssignmentOut[]>([]);
    const [selectedCourseId, setSelectedCourseId] = useState("");
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [dueDate, setDueDate] = useState("");
    const [maxScore, setMaxScore] = useState(100);

    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const displayName = useMemo(() => {
        return me?.full_name?.trim() || user?.full_name?.trim() || "Teacher";
    }, [me, user]);

    const displaySchoolName = useMemo(() => {
        return me?.school_name?.trim() || user?.school_name?.trim() || "Your School";
    }, [me, user]);

    async function loadData() {
        const [myCourses, myAssignments] = await Promise.all([
            getMyCourses(),
            getMyTeacherAssignments(),
        ]);
        setCourses(myCourses);
        setAssignments(myAssignments);
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

                if (!["teacher", "admin", "platform_admin"].includes(currentUser.role)) {
                    router.replace("/dashboard");
                    return;
                }

                if (currentUser.is_active === false) {
                    logout();
                    router.replace("/login");
                    return;
                }

                setMe(currentUser as AuthMeOut);
                await loadData();
            } catch (e: unknown) {
                const message =
                    e instanceof Error ? e.message : "Failed to load assignments";
                setError(message);
            } finally {
                setLoading(false);
            }
        }

        void init();
    }, [authLoading, refreshUser, router, logout]);

    const stats = useMemo(() => {
        const published = assignments.filter((a) => a.is_published).length;
        return {
            total: assignments.length,
            published,
            drafts: Math.max(0, assignments.length - published),
        };
    }, [assignments]);

    async function onCreateAssignment() {
        if (!title.trim() || !selectedCourseId) return;

        setBusy(true);
        setError("");
        setSuccess("");

        try {
            await createAssignment({
                title: title.trim(),
                description: description.trim() || null,
                course_id: Number(selectedCourseId),
                due_date: dueDate ? new Date(dueDate).toISOString() : null,
                max_score: maxScore,
            });

            setTitle("");
            setDescription("");
            setDueDate("");
            setMaxScore(100);
            setSelectedCourseId("");

            await loadData();
            setSuccess("Assignment created successfully.");
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to create assignment");
        } finally {
            setBusy(false);
        }
    }

    async function onTogglePublish(assignment: AssignmentOut) {
        setBusy(true);
        setError("");
        setSuccess("");

        try {
            await publishAssignment(assignment.id, {
                is_published: !assignment.is_published,
            });
            await loadData();
            setSuccess(
                assignment.is_published
                    ? "Assignment unpublished."
                    : "Assignment published."
            );
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to update assignment");
        } finally {
            setBusy(false);
        }
    }

    async function onDeleteAssignment(assignment: AssignmentOut) {
        const confirmed = window.confirm(`Delete "${assignment.title}"?`);
        if (!confirmed) return;

        setBusy(true);
        setError("");
        setSuccess("");

        try {
            await deleteAssignment(assignment.id);
            await loadData();
            setSuccess("Assignment deleted.");
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to delete assignment");
        } finally {
            setBusy(false);
        }
    }

    if (authLoading || loading) {
        return (
            <main style={{ maxWidth: 1280, margin: "0 auto", padding: 24 }}>
                <div style={cardStyle()}>
                    <div style={{ fontSize: 18, fontWeight: 800 }}>
                        Loading assignments...
                    </div>
                </div>
            </main>
        );
    }

    return (
        <DashboardShell
            userName={displayName}
            schoolName={displaySchoolName}
            onRefresh={() => void loadData()}
            sidebarItems={[
                { label: "Dashboard", href: "/teacher", icon: "/icons/dashboard.svg" },
                { label: "Courses", href: "/courses", icon: "/icons/book.svg" },
                { label: "Assignments", href: "/teacher/assignments", icon: "/icons/quiz.svg" },
                { label: "Classes", href: "/teacher/classes", icon: "/icons/class.svg" },
                { label: "Notifications", href: "/notifications", icon: "/icons/bell.svg" },
                { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
            ]}
        >
            <div style={{ display: "grid", gap: 22 }}>
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
                            {displaySchoolName} · Teacher assignments
                        </div>
                        <h1
                            style={{
                                fontSize: 44,
                                lineHeight: 1.1,
                                margin: "12px 0 10px 0",
                                fontWeight: 900,
                            }}
                        >
                            Manage assignments
                        </h1>

                        <p style={{ fontSize: 18, margin: 0, opacity: 0.95 }}>
                            Create, publish, review, and grade learner work.
                        </p>
                    </div>

                    <div
                        style={{
                            minHeight: 180,
                            borderRadius: 24,
                            background:
                                "radial-gradient(circle at top right, rgba(255,255,255,0.35), rgba(255,255,255,0.08))",
                            display: "grid",
                            placeItems: "center",
                        }}
                    >
                        <img
                            src="/branding/logo-dark.png"
                            alt="Mhike School"
                            style={{ width: 140, height: "auto", objectFit: "contain" }}
                        />
                    </div>
                </section>

                {error && (
                    <div
                        style={{
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
                        display: "grid",
                        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                        gap: 18,
                    }}
                >
                    <StatCard label="Total assignments" value={stats.total} />
                    <StatCard label="Published" value={stats.published} />
                    <StatCard label="Drafts" value={stats.drafts} />
                </section>

                <section
                    style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1.5fr",
                        gap: 18,
                        alignItems: "start",
                    }}
                >
                    <SectionCard title="Create assignment">
                        <div style={{ display: "grid", gap: 10 }}>
                            <select
                                value={selectedCourseId}
                                onChange={(e) => setSelectedCourseId(e.target.value)}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                }}
                            >
                                <option value="">Select course</option>
                                {courses.map((course) => (
                                    <option key={course.id} value={course.id}>
                                        {course.title}
                                    </option>
                                ))}
                            </select>

                            <input
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="Assignment title"
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                }}
                            />

                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Description"
                                rows={4}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                }}
                            />

                            <input
                                type="datetime-local"
                                value={dueDate}
                                onChange={(e) => setDueDate(e.target.value)}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                }}
                            />

                            <input
                                type="number"
                                min={1}
                                value={maxScore}
                                onChange={(e) => setMaxScore(Number(e.target.value))}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                }}
                            />

                            <button
                                disabled={busy || !title.trim() || !selectedCourseId}
                                onClick={onCreateAssignment}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "none",
                                    background: "#2563EB",
                                    color: "white",
                                    fontWeight: 900,
                                    cursor: "pointer",
                                    opacity: busy || !title.trim() || !selectedCourseId ? 0.7 : 1,
                                }}
                            >
                                Create assignment
                            </button>
                        </div>
                    </SectionCard>

                    <SectionCard title="My assignments">
                        {assignments.length === 0 ? (
                            <div style={{ color: "#6B7280" }}>No assignments yet.</div>
                        ) : (
                            <div style={{ display: "grid", gap: 12 }}>
                                {assignments.map((assignment) => (
                                    <div
                                        key={assignment.id}
                                        style={{
                                            border: "1px solid #E5E7EB",
                                            borderRadius: 16,
                                            padding: 14,
                                            background: "#F8FAFC",
                                        }}
                                    >
                                        <div
                                            style={{
                                                display: "flex",
                                                justifyContent: "space-between",
                                                gap: 12,
                                                alignItems: "flex-start",
                                                flexWrap: "wrap",
                                            }}
                                        >
                                            <div>
                                                <div
                                                    style={{
                                                        fontSize: 18,
                                                        fontWeight: 900,
                                                        color: "#0F172A",
                                                    }}
                                                >
                                                    {assignment.title}
                                                </div>

                                                {assignment.description && (
                                                    <div style={{ marginTop: 6, color: "#475569" }}>
                                                        {assignment.description}
                                                    </div>
                                                )}

                                                <div
                                                    style={{
                                                        marginTop: 8,
                                                        color: "#64748B",
                                                        fontSize: 14,
                                                    }}
                                                >
                                                    Due:{" "}
                                                    {assignment.due_date
                                                        ? new Date(assignment.due_date).toLocaleString()
                                                        : "No due date"}
                                                </div>

                                                <div
                                                    style={{
                                                        marginTop: 4,
                                                        color: "#64748B",
                                                        fontSize: 14,
                                                    }}
                                                >
                                                    Max score: {assignment.max_score}
                                                </div>
                                            </div>

                                            <div
                                                style={{
                                                    padding: "6px 10px",
                                                    borderRadius: 999,
                                                    fontSize: 12,
                                                    fontWeight: 800,
                                                    background: assignment.is_published
                                                        ? "#DCFCE7"
                                                        : "#FEF3C7",
                                                    color: assignment.is_published
                                                        ? "#166534"
                                                        : "#92400E",
                                                }}
                                            >
                                                {assignment.is_published ? "Published" : "Draft"}
                                            </div>
                                        </div>

                                        <div
                                            style={{
                                                display: "flex",
                                                gap: 8,
                                                flexWrap: "wrap",
                                                marginTop: 12,
                                            }}
                                        >
                                            <button
                                                onClick={() =>
                                                    router.push(`/teacher/assignments/${assignment.id}`)
                                                }
                                                style={{
                                                    padding: "10px 14px",
                                                    borderRadius: 12,
                                                    border: "1px solid #E5E7EB",
                                                    background: "#FFFFFF",
                                                    color: "#0F172A",
                                                    fontWeight: 800,
                                                    cursor: "pointer",
                                                }}
                                            >
                                                View submissions
                                            </button>

                                            <button
                                                onClick={() => void onTogglePublish(assignment)}
                                                disabled={busy}
                                                style={{
                                                    padding: "10px 14px",
                                                    borderRadius: 12,
                                                    border: "none",
                                                    background: "#2563EB",
                                                    color: "white",
                                                    fontWeight: 800,
                                                    cursor: "pointer",
                                                    opacity: busy ? 0.7 : 1,
                                                }}
                                            >
                                                {assignment.is_published ? "Unpublish" : "Publish"}
                                            </button>

                                            <button
                                                onClick={() => void onDeleteAssignment(assignment)}
                                                disabled={busy}
                                                style={{
                                                    padding: "10px 14px",
                                                    borderRadius: 12,
                                                    border: "1px solid #FECACA",
                                                    background: "#FEF2F2",
                                                    color: "#991B1B",
                                                    fontWeight: 800,
                                                    cursor: "pointer",
                                                    opacity: busy ? 0.7 : 1,
                                                }}
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </SectionCard>
                </section>
            </div>
        </DashboardShell>
    );
}