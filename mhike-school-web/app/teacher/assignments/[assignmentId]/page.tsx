"use client";

import React, { useEffect, useMemo, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import {
    AssignmentOut,
    AssignmentSubmissionOut,
    getAssignment,
    gradeSubmission,
    listAssignmentSubmissions,
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

type AuthMeOut = {
    id: number;
    full_name?: string | null;
    email: string;
    role: "student" | "teacher" | "admin" | "platform_admin" | string;
    school_id?: number | null;
    school_name?: string | null;
};

export default function TeacherAssignmentDetailPage() {
    const params = useParams<{ assignmentId: string }>();
    const router = useRouter();
    const { user, loading: authLoading, refreshUser, logout } = useAuth();

    const [me, setMe] = useState<AuthMeOut | null>(null);
    const [assignment, setAssignment] = useState<AssignmentOut | null>(null);
    const [submissions, setSubmissions] = useState<AssignmentSubmissionOut[]>([]);
    const [loading, setLoading] = useState(true);
    const [busyId, setBusyId] = useState<number | null>(null);
    const [error, setError] = useState("");

    const displayName = useMemo(() => {
        return me?.full_name?.trim() || user?.full_name?.trim() || "Teacher";
    }, [me, user]);

    const displaySchoolName = useMemo(() => {
        return me?.school_name?.trim() || user?.school_name?.trim() || "Your School";
    }, [me, user]);

    async function loadData() {
        const id = Number(params.assignmentId);
        const [assignmentData, submissionsData] = await Promise.all([
            getAssignment(id),
            listAssignmentSubmissions(id),
        ]);
        setAssignment(assignmentData);
        setSubmissions(submissionsData);
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

                setMe(currentUser as AuthMeOut);
                await loadData();
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to load assignment");
            } finally {
                setLoading(false);
            }
        }

        void init();
    }, [authLoading, refreshUser, router, params.assignmentId]);

    async function onGrade(submission: AssignmentSubmissionOut) {
        if (!assignment) return;

        const scoreInput = window.prompt(
            `Enter score (0-${assignment.max_score})`,
            String(submission.score ?? 0)
        );
        if (scoreInput === null) return;

        const feedbackInput = window.prompt(
            "Enter feedback",
            submission.feedback ?? ""
        );
        if (feedbackInput === null) return;

        const parsedScore = Number(scoreInput);
        if (Number.isNaN(parsedScore)) {
            setError("Invalid score.");
            return;
        }

        try {
            setBusyId(submission.id);
            setError("");
            await gradeSubmission(submission.id, {
                score: parsedScore,
                feedback: feedbackInput,
                status: "graded",
            });
            await loadData();
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to grade submission");
        } finally {
            setBusyId(null);
        }
    }

    if (authLoading || loading) {
        return (
            <main style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
                Loading...
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
            <div style={{ display: "grid", gap: 18 }}>
                <button
                    onClick={() => router.push("/teacher/assignments")}
                    style={{
                        width: "fit-content",
                        padding: "10px 14px",
                        borderRadius: 12,
                        border: "1px solid #E5E7EB",
                        background: "#FFFFFF",
                        cursor: "pointer",
                        fontWeight: 800,
                    }}
                >
                    ← Back to assignments
                </button>

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

                {assignment && (
                    <section style={cardStyle()}>
                        <h1 style={{ marginTop: 0, fontSize: 32, fontWeight: 900 }}>
                            {assignment.title}
                        </h1>
                        <p style={{ color: "#475569" }}>
                            {assignment.description || "No description."}
                        </p>
                        <div style={{ color: "#64748B" }}>
                            Due:{" "}
                            {assignment.due_date
                                ? new Date(assignment.due_date).toLocaleString()
                                : "No due date"}
                        </div>
                        <div style={{ color: "#64748B", marginTop: 6 }}>
                            Max score: {assignment.max_score}
                        </div>
                    </section>
                )}

                <section style={cardStyle()}>
                    <h2 style={{ marginTop: 0, fontSize: 26, fontWeight: 900 }}>
                        Submissions
                    </h2>

                    {submissions.length === 0 ? (
                        <div style={{ color: "#6B7280" }}>No submissions yet.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 12 }}>
                            {submissions.map((submission) => (
                                <div
                                    key={submission.id}
                                    style={{
                                        border: "1px solid #E5E7EB",
                                        borderRadius: 16,
                                        padding: 14,
                                        background: "#F8FAFC",
                                    }}
                                >
                                    <div style={{ fontWeight: 800 }}>
                                        Student ID: {submission.student_id}
                                    </div>

                                    <div style={{ marginTop: 8, color: "#475569" }}>
                                        {submission.submission_text || "No text submission."}
                                    </div>

                                    {submission.attachment_url && (
                                        <div style={{ marginTop: 8 }}>
                                            <a
                                                href={submission.attachment_url}
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                Open attachment
                                            </a>
                                        </div>
                                    )}

                                    <div style={{ marginTop: 8, fontSize: 14, color: "#64748B" }}>
                                        Status: {submission.status}
                                    </div>
                                    <div style={{ marginTop: 4, fontSize: 14, color: "#64748B" }}>
                                        Score: {submission.score ?? "Not graded"}
                                    </div>

                                    {submission.feedback && (
                                        <div style={{ marginTop: 6, color: "#334155" }}>
                                            Feedback: {submission.feedback}
                                        </div>
                                    )}

                                    <button
                                        onClick={() => void onGrade(submission)}
                                        disabled={busyId === submission.id}
                                        style={{
                                            marginTop: 12,
                                            padding: "10px 14px",
                                            borderRadius: 12,
                                            border: "1px solid #2563EB",
                                            background: "#2563EB",
                                            color: "#FFFFFF",
                                            fontWeight: 800,
                                            cursor: "pointer",
                                        }}
                                    >
                                        {busyId === submission.id ? "Saving..." : "Grade submission"}
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </DashboardShell>
    );
}