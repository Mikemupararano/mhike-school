"use client";

import React, { useEffect, useMemo, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import {
    AssignmentOut,
    AssignmentSubmissionOut,
    getMyStudentAssignments,
    getMySubmission,
    submitAssignment,
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

export default function StudentAssignmentsPage() {
    const router = useRouter();
    const { user, loading: authLoading, refreshUser } = useAuth();

    const [me, setMe] = useState<AuthMeOut | null>(null);
    const [assignments, setAssignments] = useState<AssignmentOut[]>([]);
    const [submissions, setSubmissions] = useState<Record<number, AssignmentSubmissionOut | null>>({});
    const [loading, setLoading] = useState(true);
    const [busyId, setBusyId] = useState<number | null>(null);
    const [error, setError] = useState("");

    const displayName = useMemo(() => {
        return me?.full_name?.trim() || user?.full_name?.trim() || "Student";
    }, [me, user]);

    const displaySchoolName = useMemo(() => {
        return me?.school_name?.trim() || user?.school_name?.trim() || "Your School";
    }, [me, user]);

    async function loadData() {
        const assignmentData = await getMyStudentAssignments();
        setAssignments(assignmentData);

        const entries = await Promise.all(
            assignmentData.map(async (assignment) => {
                try {
                    const submission = await getMySubmission(assignment.id);
                    return [assignment.id, submission] as const;
                } catch {
                    return [assignment.id, null] as const;
                }
            })
        );

        setSubmissions(Object.fromEntries(entries));
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

                if (currentUser.role !== "student") {
                    router.replace("/dashboard");
                    return;
                }

                setMe(currentUser as AuthMeOut);
                await loadData();
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to load assignments");
            } finally {
                setLoading(false);
            }
        }

        void init();
    }, [authLoading, refreshUser, router]);

    async function onSubmitAssignment(assignmentId: number) {
        const submissionText = window.prompt("Enter your submission text");
        if (submissionText === null) return;

        const attachmentUrl = window.prompt("Attachment URL (optional)") ?? "";

        try {
            setBusyId(assignmentId);
            setError("");
            await submitAssignment(assignmentId, {
                submission_text: submissionText,
                attachment_url: attachmentUrl || null,
            });
            await loadData();
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to submit assignment");
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
                { label: "Dashboard", href: "/dashboard", icon: "/icons/dashboard.svg" },
                { label: "Courses", href: "/courses", icon: "/icons/book.svg" },
                { label: "Assignments", href: "/student/assignments", icon: "/icons/quiz.svg" },
                { label: "Notifications", href: "/notifications", icon: "/icons/bell.svg" },
                { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
            ]}
        >
            <div style={{ display: "grid", gap: 18 }}>
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
                            {displaySchoolName} · Student assignments
                        </div>
                        <h1
                            style={{
                                fontSize: 44,
                                lineHeight: 1.1,
                                margin: "12px 0 10px 0",
                                fontWeight: 900,
                            }}
                        >
                            My assignments
                        </h1>

                        <p style={{ fontSize: 18, margin: 0, opacity: 0.95 }}>
                            View due work, submit responses, and track feedback.
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

                <section style={cardStyle()}>
                    <h2 style={{ marginTop: 0, fontSize: 26, fontWeight: 900 }}>
                        Assignments
                    </h2>

                    {assignments.length === 0 ? (
                        <div style={{ color: "#6B7280" }}>No assignments available yet.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 12 }}>
                            {assignments.map((assignment) => {
                                const submission = submissions[assignment.id];

                                return (
                                    <div
                                        key={assignment.id}
                                        style={{
                                            border: "1px solid #E5E7EB",
                                            borderRadius: 16,
                                            padding: 14,
                                            background: "#F8FAFC",
                                        }}
                                    >
                                        <div style={{ fontSize: 18, fontWeight: 900 }}>
                                            {assignment.title}
                                        </div>

                                        {assignment.description && (
                                            <div style={{ marginTop: 6, color: "#475569" }}>
                                                {assignment.description}
                                            </div>
                                        )}

                                        <div style={{ marginTop: 8, color: "#64748B", fontSize: 14 }}>
                                            Due:{" "}
                                            {assignment.due_date
                                                ? new Date(assignment.due_date).toLocaleString()
                                                : "No due date"}
                                        </div>

                                        <div style={{ marginTop: 4, color: "#64748B", fontSize: 14 }}>
                                            Max score: {assignment.max_score}
                                        </div>

                                        <div style={{ marginTop: 10, fontSize: 14 }}>
                                            Status:{" "}
                                            <strong>{submission ? submission.status : "Not submitted"}</strong>
                                        </div>

                                        {submission?.score !== null &&
                                            submission?.score !== undefined ? (
                                            <div style={{ marginTop: 4, fontSize: 14 }}>
                                                Score: <strong>{submission.score}</strong>
                                            </div>
                                        ) : null}

                                        {submission?.feedback && (
                                            <div style={{ marginTop: 8, color: "#334155" }}>
                                                Feedback: {submission.feedback}
                                            </div>
                                        )}

                                        <button
                                            onClick={() => void onSubmitAssignment(assignment.id)}
                                            disabled={busyId === assignment.id}
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
                                            {busyId === assignment.id
                                                ? "Submitting..."
                                                : submission
                                                    ? "Resubmit"
                                                    : "Submit assignment"}
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </section>
            </div>
        </DashboardShell>
    );
}