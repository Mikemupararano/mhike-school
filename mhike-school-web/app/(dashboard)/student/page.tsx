"use client";

import Link from "next/link";
import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    getCurrentUser,
    type CurrentUser,
} from "@/lib/authApi";

type CandidateStatus =
    | "allocated"
    | "started"
    | "submitted"
    | "withdrawn"
    | "absent"
    | string;

type DashboardState =
    | {
        status: "loading";
        user: null;
        error: null;
    }
    | {
        status: "ready";
        user: CurrentUser;
        error: null;
    }
    | {
        status: "error";
        user: null;
        error: string;
    };

type AssessmentState =
    | {
        status: "loading";
        items: StudentAssessmentSummary[];
        error: null;
    }
    | {
        status: "ready";
        items: StudentAssessmentSummary[];
        error: null;
    }
    | {
        status: "error";
        items: StudentAssessmentSummary[];
        error: string;
    };

type QuickAction = {
    title: string;
    description: string;
    href: string;
    label: string;
};

type StudentAssessmentSummary = {
    assessment_id: number;
    title: string;
    description: string | null;
    assessment_type: string | null;
    academic_year: string | null;
    term: string | null;
    assessment_status: string;
    candidate_status: CandidateStatus;
    scheduled_at: string | null;
    closes_at: string | null;
    started_at: string | null;
    submitted_at: string | null;
    can_start: boolean;
    can_resume: boolean;
    is_submitted: boolean;
};

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL
    ?? "http://localhost:8000/api/v1";

const QUICK_ACTIONS: QuickAction[] = [
    {
        title: "Assignments",
        description:
            "View your current assignments, deadlines and submission details.",
        href: "/student/student/assignments",
        label: "View assignments",
    },
    {
        title: "Timetable",
        description:
            "Check your lesson order and weekly school timetable.",
        href: "/student/timetable",
        label: "View timetable",
    },
    {
        title: "Assessments",
        description:
            "Start or continue your allocated online assessments.",
        href: "#assessments",
        label: "View assessments",
    },
];

function getAuthToken(): string | null {
    if (
        typeof window
        === "undefined"
    ) {
        return null;
    }

    return window.sessionStorage.getItem(
        "mhike_token",
    );
}

function getFirstName(
    fullName: string | null,
): string {
    const trimmedName =
        fullName?.trim();

    if (!trimmedName) {
        return "Student";
    }

    return (
        trimmedName.split(
            /\s+/,
        )[0]
        ?? "Student"
    );
}

function formatToday(): string {
    return new Intl.DateTimeFormat(
        "en-GB",
        {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
        },
    ).format(
        new Date(),
    );
}

function formatAcademicYear(): string {
    const today =
        new Date();

    const year =
        today.getFullYear();

    const startYear =
        today.getMonth() >= 7
            ? year
            : year - 1;

    return (
        `${startYear}/${String(
            startYear + 1,
        ).slice(-2)}`
    );
}

function formatDateTime(
    value: string | null,
): string {
    if (!value) {
        return "Not set";
    }

    const date =
        new Date(
            value,
        );

    if (
        Number.isNaN(
            date.getTime(),
        )
    ) {
        return value;
    }

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            dateStyle: "medium",
            timeStyle: "short",
        },
    ).format(
        date,
    );
}

function humanise(
    value: string | null | undefined,
): string {
    if (!value) {
        return "Not specified";
    }

    return value
        .replace(
            /[_-]+/g,
            " ",
        )
        .replace(
            /\b\w/g,
            character =>
                character.toUpperCase(),
        );
}

function parseApiError(
    body: unknown,
    fallback: string,
): string {
    if (
        typeof body !== "object"
        || body === null
    ) {
        return fallback;
    }

    const record =
        body as Record<string, unknown>;

    if (
        typeof record.detail === "string"
        && record.detail.trim()
    ) {
        return record.detail;
    }

    if (
        typeof record.message === "string"
        && record.message.trim()
    ) {
        return record.message;
    }

    return fallback;
}

async function loadStudentAssessments():
    Promise<StudentAssessmentSummary[]> {
    const token =
        getAuthToken();

    if (!token) {
        throw new Error(
            "Your session has expired. Please sign in again.",
        );
    }

    const response =
        await fetch(
            `${API_BASE_URL}/student-assessments`,
            {
                headers: {
                    Authorization:
                        `Bearer ${token}`,
                },
                cache: "no-store",
            },
        );

    if (!response.ok) {
        let body: unknown =
            null;

        try {
            body =
                await response.json();
        } catch {
            body = null;
        }

        throw new Error(
            parseApiError(
                body,
                "Unable to load your assessments.",
            ),
        );
    }

    return (
        await response.json()
    ) as StudentAssessmentSummary[];
}

function assessmentPriority(
    assessment: StudentAssessmentSummary,
): number {
    if (
        assessment.can_resume
        && !assessment.is_submitted
    ) {
        return 0;
    }

    if (
        assessment.can_start
        && !assessment.is_submitted
    ) {
        return 1;
    }

    if (
        assessment.is_submitted
    ) {
        return 3;
    }

    return 2;
}

function assessmentStatusLabel(
    assessment: StudentAssessmentSummary,
): string {
    if (
        assessment.is_submitted
    ) {
        return "Submitted";
    }

    if (
        assessment.can_resume
    ) {
        return "In progress";
    }

    if (
        assessment.can_start
    ) {
        return "Ready to start";
    }

    if (
        assessment.candidate_status
        === "withdrawn"
    ) {
        return "Withdrawn";
    }

    if (
        assessment.candidate_status
        === "absent"
    ) {
        return "Absent";
    }

    return humanise(
        assessment.assessment_status,
    );
}

function assessmentStatusClass(
    assessment: StudentAssessmentSummary,
): string {
    if (
        assessment.is_submitted
    ) {
        return (
            "border-emerald-200 "
            + "bg-emerald-50 "
            + "text-emerald-800"
        );
    }

    if (
        assessment.can_resume
    ) {
        return (
            "border-blue-200 "
            + "bg-blue-50 "
            + "text-blue-800"
        );
    }

    if (
        assessment.can_start
    ) {
        return (
            "border-indigo-200 "
            + "bg-indigo-50 "
            + "text-indigo-800"
        );
    }

    return (
        "border-slate-200 "
        + "bg-slate-50 "
        + "text-slate-700"
    );
}

function assessmentActionLabel(
    assessment: StudentAssessmentSummary,
): string | null {
    if (
        assessment.is_submitted
    ) {
        return "View submission";
    }

    if (
        assessment.can_resume
    ) {
        return "Continue assessment";
    }

    if (
        assessment.can_start
    ) {
        return "Open assessment";
    }

    return null;
}

function ArrowIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-5 w-5"
            stroke="currentColor"
            strokeWidth="2"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 12h14M13 6l6 6-6 6"
            />
        </svg>
    );
}

function LoadingState() {
    return (
        <div
            aria-label="Loading student dashboard"
            className="space-y-6"
        >
            <div className="h-64 animate-pulse rounded-3xl bg-slate-200" />

            <div className="grid gap-4 lg:grid-cols-3">
                {Array.from(
                    {
                        length: 3,
                    },
                ).map(
                    (
                        _,
                        index,
                    ) => (
                        <div
                            key={index}
                            className="h-56 animate-pulse rounded-2xl bg-slate-200"
                        />
                    ),
                )}
            </div>

            <div className="h-52 animate-pulse rounded-2xl bg-slate-200" />
        </div>
    );
}

function AssessmentLoadingState() {
    return (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {Array.from(
                {
                    length: 2,
                },
            ).map(
                (
                    _,
                    index,
                ) => (
                    <div
                        key={index}
                        className="h-56 animate-pulse rounded-2xl bg-slate-200"
                    />
                ),
            )}
        </div>
    );
}

export default function StudentPage() {
    const [
        state,
        setState,
    ] =
        useState<DashboardState>({
            status:
                "loading",
            user:
                null,
            error:
                null,
        });

    const [
        assessmentState,
        setAssessmentState,
    ] =
        useState<AssessmentState>({
            status:
                "loading",
            items:
                [],
            error:
                null,
        });

    const loadDashboard =
        useCallback(
            async (): Promise<void> => {
                setState({
                    status:
                        "loading",
                    user:
                        null,
                    error:
                        null,
                });

                setAssessmentState({
                    status:
                        "loading",
                    items:
                        [],
                    error:
                        null,
                });

                try {
                    const user =
                        await getCurrentUser();

                    setState({
                        status:
                            "ready",
                        user,
                        error:
                            null,
                    });

                    try {
                        const assessments =
                            await loadStudentAssessments();

                        setAssessmentState({
                            status:
                                "ready",
                            items:
                                assessments,
                            error:
                                null,
                        });
                    } catch (
                        assessmentError
                    ) {
                        setAssessmentState({
                            status:
                                "error",
                            items:
                                [],
                            error:
                                assessmentError
                                instanceof Error
                                    ? assessmentError
                                        .message
                                    : "Unable to load your assessments.",
                        });
                    }
                } catch (
                    error
                ) {
                    setState({
                        status:
                            "error",
                        user:
                            null,
                        error:
                            error
                            instanceof Error
                                ? error
                                    .message
                                : "Unable to load your dashboard.",
                    });
                }
            },
            [],
        );

    useEffect(
        () => {
            void loadDashboard();
        },
        [
            loadDashboard,
        ],
    );

    const today =
        useMemo(
            () =>
                formatToday(),
            [],
        );

    const academicYear =
        useMemo(
            () =>
                formatAcademicYear(),
            [],
        );

    const sortedAssessments =
        useMemo(
            () =>
                [
                    ...assessmentState.items,
                ].sort(
                    (
                        first,
                        second,
                    ) => {
                        const priority =
                            assessmentPriority(
                                first,
                            )
                            - assessmentPriority(
                                second,
                            );

                        if (
                            priority !== 0
                        ) {
                            return priority;
                        }

                        const firstDate =
                            first.closes_at
                            ?? first.scheduled_at
                            ?? "";

                        const secondDate =
                            second.closes_at
                            ?? second.scheduled_at
                            ?? "";

                        return (
                            firstDate.localeCompare(
                                secondDate,
                            )
                            || first.title.localeCompare(
                                second.title,
                            )
                        );
                    },
                ),
            [
                assessmentState.items,
            ],
        );

    const activeAssessmentCount =
        useMemo(
            () =>
                assessmentState.items.filter(
                    assessment =>
                        (
                            assessment.can_start
                            || assessment.can_resume
                        )
                        && !assessment.is_submitted,
                ).length,
            [
                assessmentState.items,
            ],
        );

    if (
        state.status
        === "loading"
    ) {
        return (
            <main className="p-4 sm:p-6 lg:p-8">
                <LoadingState />
            </main>
        );
    }

    if (
        state.status
        === "error"
    ) {
        return (
            <main className="p-4 sm:p-6 lg:p-8">
                <section
                    role="alert"
                    className="mx-auto max-w-3xl rounded-3xl border border-red-200 bg-red-50 p-6 text-center shadow-sm sm:p-8"
                >
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-red-700">
                        Dashboard unavailable
                    </p>

                    <h1 className="mt-2 text-2xl font-extrabold text-slate-950">
                        We could not load your student account
                    </h1>

                    <p className="mt-3 text-base leading-7 text-slate-700">
                        {state.error}
                    </p>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() => {
                            void loadDashboard();
                        }}
                        className="mt-6 inline-flex items-center justify-center rounded-xl bg-slate-950 px-5 py-2.5 text-base font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                    >
                        Try again
                    </button>
                </section>
            </main>
        );
    }

    const firstName =
        getFirstName(
            state.user.full_name,
        );

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <section className="overflow-hidden rounded-3xl bg-slate-950 text-white shadow-xl">
                <div className="relative p-6 sm:p-8 lg:p-10">
                    <div
                        aria-hidden="true"
                        className="absolute -right-16 -top-20 h-56 w-56 rounded-full bg-blue-500/20 blur-3xl"
                    />

                    <div className="relative flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
                        <div className="max-w-3xl">
                            <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-300">
                                Student dashboard
                            </p>

                            <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
                                Welcome back, {firstName}
                            </h1>

                            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
                                Access your assignments, lesson timetable and
                                online assessments from one place.
                            </p>
                        </div>

                        <dl className="grid shrink-0 gap-3 sm:grid-cols-3 lg:min-w-[29rem]">
                            <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur">
                                <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                                    Today
                                </dt>
                                <dd className="mt-1 text-sm font-semibold text-white">
                                    {today}
                                </dd>
                            </div>

                            <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur">
                                <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                                    Academic year
                                </dt>
                                <dd className="mt-1 text-sm font-semibold text-white">
                                    {academicYear}
                                </dd>
                            </div>

                            <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur">
                                <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                                    Assessments ready
                                </dt>
                                <dd className="mt-1 text-sm font-semibold text-white">
                                    {
                                        assessmentState.status
                                        === "loading"
                                            ? "..."
                                            : activeAssessmentCount
                                    }
                                </dd>
                            </div>
                        </dl>
                    </div>
                </div>
            </section>

            <section
                id="assessments"
                aria-labelledby="student-assessments-heading"
                className="scroll-mt-24"
            >
                <div className="flex flex-wrap items-end justify-between gap-4">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                            Online assessments
                        </p>

                        <h2
                            id="student-assessments-heading"
                            className="mt-1 text-2xl font-extrabold tracking-tight text-slate-950"
                        >
                            Your assessments
                        </h2>

                        <p className="mt-2 text-sm leading-6 text-slate-500">
                            Start new assessments, continue active attempts and
                            see which assessments you have submitted.
                        </p>
                    </div>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() => {
                            void loadDashboard();
                        }}
                        disabled={
                            assessmentState.status
                            === "loading"
                        }
                        className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {
                            assessmentState.status
                            === "loading"
                                ? "Refreshing..."
                                : "Refresh assessments"
                        }
                    </button>
                </div>

                {
                    assessmentState.status
                    === "loading"
                    && (
                        <AssessmentLoadingState />
                    )
                }

                {
                    assessmentState.status
                    === "error"
                    && (
                        <div
                            role="alert"
                            className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-5"
                        >
                            <p className="font-bold text-red-800">
                                Assessments could not be loaded
                            </p>
                            <p className="mt-1 text-sm leading-6 text-red-700">
                                {assessmentState.error}
                            </p>
                        </div>
                    )
                }

                {
                    assessmentState.status
                    === "ready"
                    && sortedAssessments.length
                    === 0
                    && (
                        <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                            <h3 className="text-lg font-bold text-slate-950">
                                No assessments allocated
                            </h3>
                            <p className="mt-2 text-sm leading-6 text-slate-600">
                                There are no online assessments assigned to your
                                account at the moment.
                            </p>
                        </div>
                    )
                }

                {
                    assessmentState.status
                    === "ready"
                    && sortedAssessments.length
                    > 0
                    && (
                        <div className="mt-5 grid gap-4 xl:grid-cols-2">
                            {
                                sortedAssessments.map(
                                    assessment => {
                                        const actionLabel =
                                            assessmentActionLabel(
                                                assessment,
                                            );

                                        return (
                                            <article
                                                key={
                                                    assessment.assessment_id
                                                }
                                                className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-200 hover:shadow-md sm:p-6"
                                            >
                                                <div className="flex flex-wrap items-start justify-between gap-3">
                                                    <div className="min-w-0">
                                                        <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                                            {
                                                                humanise(
                                                                    assessment.assessment_type,
                                                                )
                                                            }
                                                        </p>

                                                        <h3 className="mt-1 text-xl font-extrabold text-slate-950">
                                                            {
                                                                assessment.title
                                                            }
                                                        </h3>
                                                    </div>

                                                    <span
                                                        className={
                                                            (
                                                                "rounded-full border px-3 py-1 "
                                                                + "text-xs font-extrabold "
                                                                + assessmentStatusClass(
                                                                    assessment,
                                                                )
                                                            )
                                                        }
                                                    >
                                                        {
                                                            assessmentStatusLabel(
                                                                assessment,
                                                            )
                                                        }
                                                    </span>
                                                </div>

                                                {
                                                    assessment.description
                                                    && (
                                                        <p className="mt-3 text-sm leading-6 text-slate-600">
                                                            {
                                                                assessment.description
                                                            }
                                                        </p>
                                                    )
                                                }

                                                <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                                                    <div className="rounded-xl bg-slate-50 p-3">
                                                        <dt className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">
                                                            Term
                                                        </dt>
                                                        <dd className="mt-1 font-semibold text-slate-900">
                                                            {
                                                                assessment.term
                                                                ?? "Not specified"
                                                            }
                                                        </dd>
                                                    </div>

                                                    <div className="rounded-xl bg-slate-50 p-3">
                                                        <dt className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">
                                                            Academic year
                                                        </dt>
                                                        <dd className="mt-1 font-semibold text-slate-900">
                                                            {
                                                                assessment.academic_year
                                                                ?? "Not specified"
                                                            }
                                                        </dd>
                                                    </div>

                                                    <div className="rounded-xl bg-slate-50 p-3">
                                                        <dt className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">
                                                            Opens
                                                        </dt>
                                                        <dd className="mt-1 font-semibold text-slate-900">
                                                            {
                                                                formatDateTime(
                                                                    assessment.scheduled_at,
                                                                )
                                                            }
                                                        </dd>
                                                    </div>

                                                    <div className="rounded-xl bg-slate-50 p-3">
                                                        <dt className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">
                                                            Closes
                                                        </dt>
                                                        <dd className="mt-1 font-semibold text-slate-900">
                                                            {
                                                                formatDateTime(
                                                                    assessment.closes_at,
                                                                )
                                                            }
                                                        </dd>
                                                    </div>
                                                </dl>

                                                <div className="mt-auto pt-5">
                                                    {
                                                        actionLabel
                                                        ? (
                                                            <Link
                                                                href={
                                                                    (
                                                                        "/student/student/quizzes/attempts/"
                                                                        + assessment.assessment_id
                                                                    )
                                                                }
                                                                data-custom-button="true"
                                                                className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-5 py-3 text-sm font-extrabold text-white transition hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                                                            >
                                                                {
                                                                    actionLabel
                                                                }
                                                                <ArrowIcon />
                                                            </Link>
                                                        )
                                                        : (
                                                            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600">
                                                                This assessment is not currently available to open.
                                                            </div>
                                                        )
                                                    }
                                                </div>
                                            </article>
                                        );
                                    },
                                )
                            }
                        </div>
                    )
                }
            </section>

            <section
                aria-labelledby="student-quick-actions-heading"
            >
                <div>
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                        Quick access
                    </p>

                    <h2
                        id="student-quick-actions-heading"
                        className="mt-1 text-2xl font-extrabold tracking-tight text-slate-950"
                    >
                        Your learning tools
                    </h2>

                    <p className="mt-2 text-sm leading-6 text-slate-500">
                        Choose an area below to continue with your schoolwork.
                    </p>
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-3">
                    {
                        QUICK_ACTIONS.map(
                            (
                                action,
                                index,
                            ) => (
                                <article
                                    key={
                                        action.href
                                    }
                                    className="group flex min-h-56 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md sm:p-6"
                                >
                                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-xl font-black text-blue-700">
                                        {
                                            index
                                            + 1
                                        }
                                    </div>

                                    <h3 className="mt-5 text-xl font-bold text-slate-950">
                                        {
                                            action.title
                                        }
                                    </h3>

                                    <p className="mt-2 flex-1 text-base leading-7 text-slate-600">
                                        {
                                            action.description
                                        }
                                    </p>

                                    <Link
                                        href={
                                            action.href
                                        }
                                        data-custom-button="true"
                                        className="mt-5 inline-flex w-fit items-center gap-2 rounded-xl text-base font-bold text-blue-700 transition hover:text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-4"
                                    >
                                        {
                                            action.label
                                        }
                                        <ArrowIcon />
                                    </Link>
                                </article>
                            ),
                        )
                    }
                </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-indigo-700">
                        Getting started
                    </p>

                    <h2 className="mt-1 text-xl font-bold text-slate-950">
                        Plan your school day
                    </h2>

                    <div className="mt-5 grid gap-3">
                        {
                            [
                                [
                                    "Check your timetable",
                                    "Review today's lesson order before the school day begins.",
                                ],
                                [
                                    "Review your assignments",
                                    "Open each assignment to check its instructions and submission requirements.",
                                ],
                                [
                                    "Check your assessments",
                                    "Start or continue any available assessment before its closing time.",
                                ],
                            ].map(
                                (
                                    [
                                        title,
                                        description,
                                    ],
                                    index,
                                ) => (
                                    <div
                                        key={
                                            title
                                        }
                                        className="rounded-2xl bg-slate-50 p-4"
                                    >
                                        <p className="font-bold text-slate-900">
                                            {
                                                index
                                                + 1
                                            }. {
                                                title
                                            }
                                        </p>
                                        <p className="mt-1 text-sm leading-6 text-slate-600">
                                            {
                                                description
                                            }
                                        </p>
                                    </div>
                                ),
                            )
                        }
                    </div>
                </article>

                <aside className="rounded-2xl border border-blue-100 bg-blue-50 p-5 shadow-sm sm:p-6">
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                        Your account
                    </p>

                    <h2 className="mt-1 text-xl font-bold text-slate-950">
                        Student details
                    </h2>

                    <dl className="mt-5 space-y-4">
                        <div>
                            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                Name
                            </dt>
                            <dd className="mt-1 break-words font-semibold text-slate-900">
                                {
                                    state.user.full_name
                                    ?? "Not provided"
                                }
                            </dd>
                        </div>

                        <div>
                            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                School
                            </dt>
                            <dd className="mt-1 break-words font-semibold text-slate-900">
                                {
                                    state.user.school_name
                                    ?? "Not assigned"
                                }
                            </dd>
                        </div>

                        <div>
                            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                Email
                            </dt>
                            <dd className="mt-1 break-all font-semibold text-slate-900">
                                {
                                    state.user.email
                                }
                            </dd>
                        </div>
                    </dl>
                </aside>
            </section>
        </main>
    );
}
