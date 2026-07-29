"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import StudentSubmissionModal from "@/components/assignments/StudentSubmissionModal";
import DashboardShell from "@/components/layout/DashboardShell";
import { useStudentAssignments } from "@/hooks/useStudentAssignments";
import { useAuth } from "@/providers/AuthProvider";
import { UserRole } from "@/types/user";

type AuthMeOut = {
    id: number;
    full_name?: string | null;
    email: string;
    role?: UserRole | string | null;
    roles?: UserRole[];
    school_id?: number | null;
    school_name?: string | null;
};

type SubmissionLike = {
    status?: string | null;
    score?: number | null;
    feedback?: string | null;
};

function hasStudentRole(user: AuthMeOut | null): boolean {
    if (!user) return false;

    if (user.roles?.includes(UserRole.STUDENT)) {
        return true;
    }

    return (
        user.role === UserRole.STUDENT ||
        user.role === "student"
    );
}

function formatDateTime(value?: string | null): string {
    if (!value) return "No due date";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Date unavailable";
    }

    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

function formatStatus(status?: string | null): string {
    if (!status) return "Not submitted";

    return status
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (character) =>
            character.toUpperCase(),
        );
}

function getStatusClasses(
    submission?: SubmissionLike | null,
): string {
    if (!submission) {
        return "border-amber-200 bg-amber-50 text-amber-800";
    }

    const status =
        submission.status?.toLowerCase() ?? "";

    if (
        status.includes("mark") ||
        status.includes("grade") ||
        status.includes("complete")
    ) {
        return "border-emerald-200 bg-emerald-50 text-emerald-800";
    }

    if (
        status.includes("return") ||
        status.includes("late") ||
        status.includes("overdue")
    ) {
        return "border-rose-200 bg-rose-50 text-rose-800";
    }

    return "border-blue-200 bg-blue-50 text-blue-800";
}

function AssignmentSkeleton() {
    return (
        <div
            aria-hidden="true"
            className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5"
        >
            <div className="h-5 w-2/5 rounded bg-slate-200" />
            <div className="mt-4 h-4 w-full rounded bg-slate-100" />
            <div className="mt-2 h-4 w-4/5 rounded bg-slate-100" />
            <div className="mt-5 flex gap-3">
                <div className="h-8 w-28 rounded-full bg-slate-100" />
                <div className="h-8 w-24 rounded-full bg-slate-100" />
            </div>
            <div className="mt-5 h-11 w-40 rounded-xl bg-slate-200" />
        </div>
    );
}

export default function StudentAssignmentsPage() {
    const router = useRouter();
    const {
        user,
        loading: authLoading,
        refreshUser,
    } = useAuth();

    const {
        assignments,
        submissions,
        isLoading,
        busyId,
        error,
        refresh,
        submitStudentAssignment,
    } = useStudentAssignments();

    const [me, setMe] =
        useState<AuthMeOut | null>(null);
    const [authError, setAuthError] =
        useState("");
    const [
        selectedAssignmentId,
        setSelectedAssignmentId,
    ] = useState<number | null>(null);

    const selectedAssignment =
        assignments.find(
            (assignment) =>
                assignment.id ===
                selectedAssignmentId,
        ) ?? null;

    const displayName = useMemo(() => {
        return (
            me?.full_name?.trim() ||
            user?.full_name?.trim() ||
            "Student"
        );
    }, [me, user]);

    const displaySchoolName = useMemo(() => {
        return (
            me?.school_name?.trim() ||
            user?.school_name?.trim() ||
            "Your School"
        );
    }, [me, user]);

    const verifyStudentAccess =
        useCallback(async () => {
            try {
                setAuthError("");

                const currentUser =
                    await refreshUser();

                if (!currentUser) {
                    router.replace("/login");
                    return;
                }

                const authenticatedUser =
                    currentUser as AuthMeOut;

                if (
                    !hasStudentRole(
                        authenticatedUser,
                    )
                ) {
                    router.replace("/dashboard");
                    return;
                }

                setMe(authenticatedUser);
            } catch (err) {
                setAuthError(
                    err instanceof Error
                        ? err.message
                        : "Failed to verify student access.",
                );
            }
        }, [refreshUser, router]);

    useEffect(() => {
        if (authLoading) return;

        void verifyStudentAccess();
    }, [authLoading, verifyStudentAccess]);

    const assignmentIds = useMemo(
        () =>
            new Set(
                assignments.map(
                    (assignment) => assignment.id,
                ),
            ),
        [assignments],
    );

    const submittedCount = useMemo(() => {
        return Object.entries(submissions).filter(
            ([assignmentId, submission]) =>
                assignmentIds.has(
                    Number(assignmentId),
                ) && Boolean(submission),
        ).length;
    }, [assignmentIds, submissions]);

    const scoredSubmissions = useMemo(() => {
        return Object.entries(submissions)
            .filter(([assignmentId]) =>
                assignmentIds.has(
                    Number(assignmentId),
                ),
            )
            .map(([, submission]) => submission)
            .filter(
                (
                    submission,
                ): submission is typeof submission & {
                    score: number;
                } =>
                    typeof submission?.score ===
                    "number",
            );
    }, [assignmentIds, submissions]);

    const averageScore = useMemo(() => {
        if (scoredSubmissions.length === 0) {
            return null;
        }

        const total = scoredSubmissions.reduce(
            (sum, submission) =>
                sum + submission.score,
            0,
        );

        return total / scoredSubmissions.length;
    }, [scoredSubmissions]);

    const outstandingCount = Math.max(
        assignments.length - submittedCount,
        0,
    );

    async function handleSubmitAssignment(
        submissionText: string,
        attachmentUrl?: string,
    ) {
        if (selectedAssignmentId === null) {
            return;
        }

        await submitStudentAssignment(
            selectedAssignmentId,
            submissionText,
            attachmentUrl,
        );

        setSelectedAssignmentId(null);
    }

    async function handleRetry(): Promise<void> {
        await Promise.allSettled([
            verifyStudentAccess(),
            refresh(),
        ]);
    }

    if (authLoading) {
        return (
            <main className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
                <div className="h-56 animate-pulse rounded-3xl bg-slate-200" />

                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {Array.from({ length: 4 }).map(
                        (_, index) => (
                            <div
                                key={index}
                                className="h-28 animate-pulse rounded-2xl bg-slate-100"
                            />
                        ),
                    )}
                </div>

                <div className="grid gap-4">
                    {Array.from({ length: 3 }).map(
                        (_, index) => (
                            <AssignmentSkeleton
                                key={index}
                            />
                        ),
                    )}
                </div>
            </main>
        );
    }

    return (
        <DashboardShell
            userName={displayName}
            schoolName={displaySchoolName}
            onRefresh={() => void refresh()}
        >
            <main className="space-y-6">
                <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-800 via-blue-700 to-sky-500 p-6 text-white shadow-[0_20px_45px_rgba(30,64,175,0.24)] sm:p-8">
                    <div className="relative z-10 grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(220px,0.7fr)] lg:items-center">
                        <div>
                            <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-100">
                                {displaySchoolName} · Student
                                assignments
                            </p>

                            <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
                                My assignments
                            </h1>

                            <p className="mt-4 max-w-2xl text-base leading-7 text-blue-50 sm:text-lg">
                                View work set by your teachers,
                                submit responses, and keep track
                                of scores and feedback.
                            </p>
                        </div>

                        <div className="hidden min-h-44 place-items-center rounded-3xl border border-white/20 bg-white/10 p-5 backdrop-blur-sm sm:grid">
                            <Image
                                src="/branding/logo-dark.png"
                                alt="Mhike School"
                                width={140}
                                height={140}
                                className="h-auto w-28 object-contain sm:w-36"
                                priority
                            />
                        </div>
                    </div>

                    <div
                        aria-hidden="true"
                        className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-white/10 blur-2xl"
                    />
                    <div
                        aria-hidden="true"
                        className="absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-sky-300/20 blur-3xl"
                    />
                </section>

                {(authError || error) && (
                    <section
                        role="alert"
                        aria-live="assertive"
                        className="rounded-2xl border border-rose-200 bg-rose-50 p-5"
                    >
                        <h2 className="text-base font-bold text-rose-900">
                            We could not load everything
                        </h2>

                        <p className="mt-1 text-sm leading-6 text-rose-800">
                            {authError || error}
                        </p>

                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void handleRetry();
                            }}
                            className="mt-4 inline-flex items-center justify-center rounded-xl border border-rose-300 bg-white px-4 py-2.5 text-sm font-bold text-rose-800 transition hover:bg-rose-100 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2"
                        >
                            Try again
                        </button>
                    </section>
                )}

                <section
                    aria-label="Assignment summary"
                    className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
                >
                    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                        <p className="text-sm font-semibold text-slate-500">
                            Total assignments
                        </p>
                        <p className="mt-2 text-3xl font-black text-slate-950">
                            {assignments.length}
                        </p>
                    </article>

                    <article className="rounded-2xl border border-blue-200 bg-blue-50 p-5 shadow-sm">
                        <p className="text-sm font-semibold text-blue-700">
                            Submitted
                        </p>
                        <p className="mt-2 text-3xl font-black text-blue-950">
                            {submittedCount}
                        </p>
                    </article>

                    <article className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
                        <p className="text-sm font-semibold text-amber-700">
                            Awaiting submission
                        </p>
                        <p className="mt-2 text-3xl font-black text-amber-950">
                            {outstandingCount}
                        </p>
                    </article>

                    <article className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
                        <p className="text-sm font-semibold text-emerald-700">
                            Average score
                        </p>
                        <p className="mt-2 text-3xl font-black text-emerald-950">
                            {averageScore === null
                                ? "—"
                                : averageScore.toLocaleString(
                                    "en-GB",
                                    {
                                        maximumFractionDigits: 1,
                                    },
                                )}
                        </p>
                    </article>
                </section>

                <section
                    aria-labelledby="assignments-heading"
                    className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
                >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                            <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                                Coursework
                            </p>

                            <h2
                                id="assignments-heading"
                                className="mt-1 text-2xl font-black text-slate-950"
                            >
                                Assignments
                            </h2>

                            <p className="mt-2 text-base text-slate-600">
                                Review the instructions and submit
                                your work before the due date.
                            </p>
                        </div>

                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => void refresh()}
                            disabled={isLoading}
                            className="inline-flex shrink-0 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isLoading
                                ? "Refreshing..."
                                : "Refresh assignments"}
                        </button>
                    </div>

                    <div className="mt-6">
                        {isLoading ? (
                            <div
                                aria-label="Loading assignments"
                                className="grid gap-4"
                            >
                                {Array.from({
                                    length: 3,
                                }).map((_, index) => (
                                    <AssignmentSkeleton
                                        key={index}
                                    />
                                ))}
                            </div>
                        ) : assignments.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
                                <div
                                    aria-hidden="true"
                                    className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-blue-100 text-2xl font-black text-blue-700"
                                >
                                    ✓
                                </div>

                                <h3 className="mt-4 text-lg font-bold text-slate-950">
                                    No assignments available
                                </h3>

                                <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-600">
                                    Your teachers have not
                                    published any assignments yet.
                                    New work will appear here when
                                    it becomes available.
                                </p>
                            </div>
                        ) : (
                            <div className="grid gap-4">
                                {assignments.map(
                                    (assignment) => {
                                        const submission =
                                            submissions[
                                            assignment.id
                                            ];

                                        return (
                                            <article
                                                key={
                                                    assignment.id
                                                }
                                                className="rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-blue-200 hover:bg-white hover:shadow-md sm:p-6"
                                            >
                                                <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                                                    <div className="min-w-0 flex-1">
                                                        <div className="flex flex-wrap items-center gap-2">
                                                            <span
                                                                className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${getStatusClasses(
                                                                    submission,
                                                                )}`}
                                                            >
                                                                {formatStatus(
                                                                    submission?.status,
                                                                )}
                                                            </span>

                                                            <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-bold text-slate-700">
                                                                Max
                                                                score:{" "}
                                                                {
                                                                    assignment.max_score
                                                                }
                                                            </span>
                                                        </div>

                                                        <h3 className="mt-4 text-xl font-black text-slate-950">
                                                            {
                                                                assignment.title
                                                            }
                                                        </h3>

                                                        {assignment.description && (
                                                            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600 sm:text-base">
                                                                {
                                                                    assignment.description
                                                                }
                                                            </p>
                                                        )}

                                                        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                                                            <div className="rounded-xl border border-slate-200 bg-white p-3">
                                                                <dt className="font-semibold text-slate-500">
                                                                    Due
                                                                </dt>
                                                                <dd className="mt-1 font-bold text-slate-900">
                                                                    {formatDateTime(
                                                                        assignment.due_date,
                                                                    )}
                                                                </dd>
                                                            </div>

                                                            <div className="rounded-xl border border-slate-200 bg-white p-3">
                                                                <dt className="font-semibold text-slate-500">
                                                                    Score
                                                                </dt>
                                                                <dd className="mt-1 font-bold text-slate-900">
                                                                    {typeof submission?.score ===
                                                                        "number"
                                                                        ? `${submission.score} / ${assignment.max_score}`
                                                                        : "Not marked"}
                                                                </dd>
                                                            </div>
                                                        </dl>

                                                        {submission?.feedback && (
                                                            <div className="mt-4 rounded-xl border border-violet-200 bg-violet-50 p-4">
                                                                <p className="text-xs font-bold uppercase tracking-wide text-violet-700">
                                                                    Teacher
                                                                    feedback
                                                                </p>
                                                                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-violet-950">
                                                                    {
                                                                        submission.feedback
                                                                    }
                                                                </p>
                                                            </div>
                                                        )}
                                                    </div>

                                                    <button
                                                        type="button"
                                                        data-custom-button="true"
                                                        onClick={() =>
                                                            setSelectedAssignmentId(
                                                                assignment.id,
                                                            )
                                                        }
                                                        disabled={
                                                            busyId ===
                                                            assignment.id
                                                        }
                                                        className="inline-flex w-full shrink-0 items-center justify-center rounded-xl bg-blue-700 px-5 py-3 text-sm font-bold text-white transition hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
                                                    >
                                                        {busyId ===
                                                            assignment.id
                                                            ? "Submitting..."
                                                            : submission
                                                                ? "Resubmit"
                                                                : "Submit assignment"}
                                                    </button>
                                                </div>
                                            </article>
                                        );
                                    },
                                )}
                            </div>
                        )}
                    </div>
                </section>
            </main>

            <StudentSubmissionModal
                isOpen={Boolean(selectedAssignment)}
                assignmentTitle={
                    selectedAssignment?.title ?? ""
                }
                isSubmitting={
                    selectedAssignmentId !== null &&
                    busyId === selectedAssignmentId
                }
                onClose={() =>
                    setSelectedAssignmentId(null)
                }
                onSubmit={handleSubmitAssignment}
            />
        </DashboardShell>
    );
}
