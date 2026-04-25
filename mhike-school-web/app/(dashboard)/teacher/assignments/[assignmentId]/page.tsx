"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import {
    AssignmentOut,
    AssignmentSubmissionOut,
    getAssignment,
    gradeSubmission,
    listAssignmentSubmissions,
} from "@/lib/assignmentApi";
import { UserRole } from "@/types/user";

export default function TeacherAssignmentDetailPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherAssignmentDetailContent />
        </RoleGate>
    );
}

function TeacherAssignmentDetailContent() {
    const params = useParams<{ assignmentId: string }>();
    const assignmentId = Number(params.assignmentId);

    const [assignment, setAssignment] = useState<AssignmentOut | null>(null);
    const [submissions, setSubmissions] = useState<AssignmentSubmissionOut[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [busyId, setBusyId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    async function loadData() {
        if (!assignmentId || Number.isNaN(assignmentId)) {
            setError("Invalid assignment ID.");
            setIsLoading(false);
            return;
        }

        try {
            setError(null);

            const [assignmentData, submissionsData] = await Promise.all([
                getAssignment(assignmentId),
                listAssignmentSubmissions(assignmentId),
            ]);

            setAssignment(assignmentData);
            setSubmissions(submissionsData);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load assignment.",
            );
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadData();
    }, [assignmentId]);

    async function handleGrade(submission: AssignmentSubmissionOut) {
        if (!assignment) return;

        const scoreInput = window.prompt(
            `Enter score 0-${assignment.max_score}`,
            String(submission.score ?? 0),
        );

        if (scoreInput === null) return;

        const parsedScore = Number(scoreInput);

        if (
            Number.isNaN(parsedScore) ||
            parsedScore < 0 ||
            parsedScore > assignment.max_score
        ) {
            setError(`Score must be between 0 and ${assignment.max_score}.`);
            return;
        }

        const feedbackInput = window.prompt(
            "Enter feedback",
            submission.feedback ?? "",
        );

        if (feedbackInput === null) return;

        try {
            setBusyId(submission.id);
            setError(null);

            await gradeSubmission(submission.id, {
                score: parsedScore,
                feedback: feedbackInput,
                status: "graded",
            });

            await loadData();
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to grade submission.",
            );
        } finally {
            setBusyId(null);
        }
    }

    return (
        <div className="p-6">
            <Link
                href="/teacher/assignments"
                className="text-sm font-semibold text-blue-600 hover:underline"
            >
                ← Back to assignments
            </Link>

            {isLoading && <p className="mt-6">Loading assignment...</p>}

            {error && (
                <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                    {error}
                </div>
            )}

            {!isLoading && assignment && (
                <>
                    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h1 className="text-3xl font-extrabold">
                            {assignment.title}
                        </h1>

                        <p className="mt-3 text-slate-600">
                            {assignment.description || "No description."}
                        </p>

                        <div className="mt-4 text-sm text-slate-500">
                            Due:{" "}
                            {assignment.due_date
                                ? new Date(assignment.due_date).toLocaleString()
                                : "No due date"}
                        </div>

                        <div className="mt-1 text-sm text-slate-500">
                            Max score: {assignment.max_score}
                        </div>
                    </section>

                    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h2 className="text-2xl font-extrabold">Submissions</h2>

                        {submissions.length === 0 ? (
                            <p className="mt-4 text-slate-500">
                                No submissions yet.
                            </p>
                        ) : (
                            <div className="mt-4 space-y-4">
                                {submissions.map((submission) => (
                                    <div
                                        key={submission.id}
                                        className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                                    >
                                        <div className="font-bold">
                                            Student ID: {submission.student_id}
                                        </div>

                                        <p className="mt-2 text-slate-600">
                                            {submission.submission_text ||
                                                "No text submission."}
                                        </p>

                                        {submission.attachment_url && (
                                            <a
                                                href={submission.attachment_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="mt-2 inline-block text-sm font-semibold text-blue-600 hover:underline"
                                            >
                                                Open attachment
                                            </a>
                                        )}

                                        <div className="mt-3 text-sm text-slate-500">
                                            Status: {submission.status}
                                        </div>

                                        <div className="text-sm text-slate-500">
                                            Score:{" "}
                                            {submission.score ?? "Not graded"}
                                        </div>

                                        {submission.feedback && (
                                            <p className="mt-2 text-sm text-slate-700">
                                                Feedback: {submission.feedback}
                                            </p>
                                        )}

                                        <button
                                            onClick={() => void handleGrade(submission)}
                                            disabled={busyId === submission.id}
                                            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {busyId === submission.id
                                                ? "Saving..."
                                                : "Grade submission"}
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </>
            )}
        </div>
    );
}