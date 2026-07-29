"use client";

import Link from "next/link";
import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import AttendanceHistoryTable from "@/components/parent/AttendanceHistoryTable";
import AttendanceSummaryCards from "@/components/parent/AttendanceSummaryCards";
import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

import {
    getParentStudentProgress,
    type StudentProgressSummary,
} from "@/lib/services/parentProgress";

function formatPercentage(value: number | null | undefined): string {
    if (
        value === null ||
        value === undefined ||
        !Number.isFinite(value)
    ) {
        return "N/A";
    }

    return `${Math.round(value)}%`;
}

function formatCount(value: number | null | undefined): string {
    if (
        value === null ||
        value === undefined ||
        !Number.isFinite(value)
    ) {
        return "0";
    }

    return new Intl.NumberFormat("en-GB").format(value);
}

function formatRefreshTime(value: Date): string {
    return value.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

type QuickAction = {
    href: string;
    title: string;
    description: string;
    icon: React.ReactNode;
};

function ReportIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-6 w-6"
            stroke="currentColor"
            strokeWidth="1.8"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7.5 3.75h6.879a2.25 2.25 0 0 1 1.591.659l2.621 2.621a2.25 2.25 0 0 1 .659 1.591V18a2.25 2.25 0 0 1-2.25 2.25H7.5A2.25 2.25 0 0 1 5.25 18V6A2.25 2.25 0 0 1 7.5 3.75Z"
            />
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M14.25 3.75V7.5h3.75M8.25 11.25h7.5M8.25 14.25h7.5M8.25 17.25h4.5"
            />
        </svg>
    );
}

function GradesIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-6 w-6"
            stroke="currentColor"
            strokeWidth="1.8"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.5 19.5h15M6.75 16.5V9.75M12 16.5V5.25M17.25 16.5v-4.5"
            />
        </svg>
    );
}

function AttendanceIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-6 w-6"
            stroke="currentColor"
            strokeWidth="1.8"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6.75 3.75v2.5M17.25 3.75v2.5M4.5 8.25h15M6 5.25h12A1.5 1.5 0 0 1 19.5 6.75v11.5A1.5 1.5 0 0 1 18 19.75H6a1.5 1.5 0 0 1-1.5-1.5V6.75A1.5 1.5 0 0 1 6 5.25Z"
            />
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m8.25 13 2.25 2.25 5.25-5.25"
            />
        </svg>
    );
}

function TimetableIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-6 w-6"
            stroke="currentColor"
            strokeWidth="1.8"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.5 5.25h15v13.5h-15V5.25Z"
            />
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.5 9.75h15M9.75 5.25v13.5M14.25 5.25v13.5"
            />
        </svg>
    );
}

function RefreshIcon({ spinning = false }: { spinning?: boolean }) {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className={`h-5 w-5 ${spinning ? "animate-spin" : ""}`}
            stroke="currentColor"
            strokeWidth="1.8"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M20.25 6.75v4.5h-4.5M3.75 17.25v-4.5h4.5"
            />
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6.12 8.25A7.5 7.5 0 0 1 18.9 6.9l1.35 1.35M17.88 15.75A7.5 7.5 0 0 1 5.1 17.1l-1.35-1.35"
            />
        </svg>
    );
}

const QUICK_ACTIONS: QuickAction[] = [
    {
        href: "/parent/reports",
        title: "Reports",
        description: "View published academic reports and teacher comments.",
        icon: <ReportIcon />,
    },
    {
        href: "/parent/grades",
        title: "Grades",
        description: "Review marks, feedback and academic progress.",
        icon: <GradesIcon />,
    },
    {
        href: "/parent/attendance",
        title: "Attendance",
        description: "See attendance history, totals and patterns.",
        icon: <AttendanceIcon />,
    },
    {
        href: "/parent/timetable",
        title: "Timetable",
        description: "Check lessons, subjects and daily schedules.",
        icon: <TimetableIcon />,
    },
];

type ProgressCardProps = {
    label: string;
    value: string;
    description: string;
};

function ProgressCard({
    label,
    value,
    description,
}: ProgressCardProps) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-slate-500">{label}</p>
            <p className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950">
                {value}
            </p>
            <p className="mt-1 text-sm leading-6 text-slate-500">
                {description}
            </p>
        </article>
    );
}

export default function ParentDashboardPage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading: childrenLoading,
        error: childrenError,
    } = useParentChildren();

    const [progress, setProgress] =
        useState<StudentProgressSummary | null>(null);
    const [progressLoading, setProgressLoading] = useState(false);
    const [progressError, setProgressError] =
        useState<string | null>(null);
    const [lastUpdatedAt, setLastUpdatedAt] =
        useState<Date | null>(null);

    const loadProgress = useCallback(async () => {
        if (!selectedStudentId) {
            setProgress(null);
            setProgressError(null);
            setLastUpdatedAt(null);
            return;
        }

        try {
            setProgressLoading(true);
            setProgressError(null);

            const data = await getParentStudentProgress(
                selectedStudentId,
            );

            setProgress(data);
            setLastUpdatedAt(new Date());
        } catch (error) {
            setProgress(null);
            setProgressError(
                error instanceof Error
                    ? error.message
                    : "Failed to load the progress summary.",
            );
        } finally {
            setProgressLoading(false);
        }
    }, [selectedStudentId]);

    useEffect(() => {
        void loadProgress();
    }, [loadProgress]);

    const recentHistory = useMemo(
        () => selectedProfile?.history.slice(0, 10) ?? [],
        [selectedProfile],
    );

    const selectedStudentName =
        selectedProfile?.student_name ??
        (selectedProfile
            ? `Student ${selectedProfile.student_id}`
            : "your child");

    const pageLoading = childrenLoading || progressLoading;
    const pageError = childrenError || progressError;

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <header className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                    <div className="flex min-w-0 items-start gap-4">
                        <div className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-white sm:flex">
                            <svg
                                aria-hidden="true"
                                viewBox="0 0 24 24"
                                fill="none"
                                className="h-7 w-7"
                                stroke="currentColor"
                                strokeWidth="1.8"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M15.75 6.75a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM5.25 20.25a6.75 6.75 0 0 1 13.5 0"
                                />
                            </svg>
                        </div>

                        <div className="min-w-0">
                            <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">
                                Parent portal
                            </p>

                            <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950">
                                Parent Dashboard
                            </h1>

                            <p className="mt-2 max-w-3xl text-base leading-7 text-slate-600">
                                View attendance, grades, reports and progress
                                information for your linked children.
                            </p>

                            <div
                                aria-live="polite"
                                aria-atomic="true"
                                className="mt-2 min-h-5 text-sm text-slate-500"
                            >
                                {lastUpdatedAt
                                    ? `Last refreshed at ${formatRefreshTime(
                                        lastUpdatedAt,
                                    )}.`
                                    : ""}
                            </div>
                        </div>
                    </div>

                    <button
                        type="button"
                        data-custom-button="true"
                        disabled={
                            childrenLoading ||
                            progressLoading ||
                            !selectedStudentId
                        }
                        onClick={() => void loadProgress()}
                        className="inline-flex w-fit items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-base font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        <RefreshIcon spinning={progressLoading} />
                        {progressLoading ? "Refreshing..." : "Refresh"}
                    </button>
                </div>
            </header>

            <ParentPageState
                loading={pageLoading}
                error={pageError}
                isEmpty={profiles.length === 0 || !selectedProfile}
                loadingMessage="Loading parent dashboard..."
            >
                {selectedProfile && (
                    <>
                        <ChildSelector
                            profiles={profiles}
                            selectedStudentId={selectedStudentId}
                            onSelectStudent={setSelectedStudentId}
                            title="Linked Students"
                            description="Select one of your linked children to view attendance, grades, reports and academic progress."
                        />

                        <section
                            aria-labelledby="selected-student-heading"
                            className="rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-5 shadow-sm sm:p-6"
                        >
                            <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                                Selected student
                            </p>

                            <div className="mt-2 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                                <div>
                                    <h2
                                        id="selected-student-heading"
                                        className="text-2xl font-extrabold tracking-tight text-slate-950"
                                    >
                                        {selectedStudentName}
                                    </h2>

                                    <p className="mt-1 max-w-2xl text-base leading-7 text-slate-600">
                                        Overview of current academic progress
                                        and recent activity.
                                    </p>
                                </div>

                                <Link
                                    href="/parent/reports"
                                    className="inline-flex w-fit items-center justify-center rounded-xl bg-blue-600 px-4 py-2.5 text-base font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                                >
                                    View latest reports
                                </Link>
                            </div>
                        </section>

                        <AttendanceSummaryCards profile={selectedProfile} />

                        <section
                            aria-label="Student progress summary"
                            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
                        >
                            <ProgressCard
                                label="Attendance"
                                value={formatPercentage(
                                    progress?.attendance_percentage,
                                )}
                                description="Overall recorded attendance."
                            />

                            <ProgressCard
                                label="Assignment Average"
                                value={formatPercentage(
                                    progress?.average_assignment_score,
                                )}
                                description="Average across graded assignments."
                            />

                            <ProgressCard
                                label="Published Reports"
                                value={formatCount(progress?.report_count)}
                                description="Reports currently available to view."
                            />

                            <ProgressCard
                                label="Recent Feedback"
                                value={formatCount(
                                    progress?.recent_feedback_count,
                                )}
                                description="Marked submissions with feedback."
                            />
                        </section>

                        <section
                            aria-label="Latest academic information"
                            className="grid gap-4 lg:grid-cols-2"
                        >
                            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                                <div className="flex items-start gap-3">
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
                                        <ReportIcon />
                                    </div>

                                    <div className="min-w-0">
                                        <p className="text-sm font-bold uppercase tracking-[0.12em] text-slate-500">
                                            Latest Report
                                        </p>

                                        <h2 className="mt-2 text-xl font-bold text-slate-950">
                                            {progress?.latest_report_title ??
                                                "No published report available"}
                                        </h2>
                                    </div>
                                </div>

                                <p className="mt-4 text-base leading-7 text-slate-600">
                                    Open the reports area to read published
                                    teacher feedback and download available
                                    report PDFs.
                                </p>

                                <Link
                                    href="/parent/reports"
                                    className="mt-5 inline-flex rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-base font-semibold text-blue-700 transition hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                                >
                                    View reports
                                </Link>
                            </article>

                            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                                <div className="flex items-start gap-3">
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
                                        <GradesIcon />
                                    </div>

                                    <div>
                                        <p className="text-sm font-bold uppercase tracking-[0.12em] text-slate-500">
                                            Assignments Completed
                                        </p>

                                        <p className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950">
                                            {formatCount(
                                                progress?.assignments_completed,
                                            )}
                                        </p>
                                    </div>
                                </div>

                                <p className="mt-4 text-base leading-7 text-slate-600">
                                    Review marks and recent teacher feedback in
                                    the grades area.
                                </p>

                                <Link
                                    href="/parent/grades"
                                    className="mt-5 inline-flex rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-base font-semibold text-blue-700 transition hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                                >
                                    View grades
                                </Link>
                            </article>
                        </section>

                        <section
                            aria-labelledby="recent-attendance-heading"
                            className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
                        >
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <h2
                                        id="recent-attendance-heading"
                                        className="text-xl font-bold text-slate-950"
                                    >
                                        Recent Attendance
                                    </h2>

                                    <p className="mt-1 text-base leading-7 text-slate-600">
                                        The ten most recent attendance records
                                        for {selectedStudentName}.
                                    </p>
                                </div>

                                <Link
                                    href="/parent/attendance"
                                    className="shrink-0 rounded-md font-semibold text-blue-600 transition hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                                >
                                    View full history
                                </Link>
                            </div>

                            <div className="mt-4">
                                <AttendanceHistoryTable
                                    records={recentHistory}
                                />
                            </div>
                        </section>

                        <section aria-labelledby="quick-actions-heading">
                            <div>
                                <h2
                                    id="quick-actions-heading"
                                    className="text-xl font-bold text-slate-950"
                                >
                                    Quick Actions
                                </h2>

                                <p className="mt-1 text-base leading-7 text-slate-600">
                                    Open the main parent portal sections.
                                </p>
                            </div>

                            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                                {QUICK_ACTIONS.map((action) => (
                                    <Link
                                        key={action.href}
                                        href={action.href}
                                        className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                                    >
                                        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700 transition group-hover:bg-blue-100">
                                            {action.icon}
                                        </div>

                                        <h3 className="mt-4 text-lg font-bold text-slate-950">
                                            {action.title}
                                        </h3>

                                        <p className="mt-2 text-sm leading-6 text-slate-600">
                                            {action.description}
                                        </p>

                                        <p className="mt-4 font-semibold text-blue-600">
                                            Open section{" "}
                                            <span aria-hidden="true">→</span>
                                        </p>
                                    </Link>
                                ))}
                            </div>
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}
