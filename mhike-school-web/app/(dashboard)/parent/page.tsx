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

function getProgressCardValue(
    value: number | null | undefined,
): string {
    if (
        value === null ||
        value === undefined ||
        !Number.isFinite(value)
    ) {
        return "0";
    }

    return String(value);
}

type QuickAction = {
    href: string;
    title: string;
    description: string;
};

const QUICK_ACTIONS: QuickAction[] = [
    {
        href: "/parent/reports",
        title: "Reports",
        description: "View published academic reports.",
    },
    {
        href: "/parent/grades",
        title: "Grades",
        description: "Review marks, feedback and progress.",
    },
    {
        href: "/parent/attendance",
        title: "Attendance",
        description: "See attendance history and patterns.",
    },
    {
        href: "/parent/timetable",
        title: "Timetable",
        description: "Check lessons and daily schedules.",
    },
];

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
        } catch (err) {
            setProgress(null);
            setProgressError(
                err instanceof Error
                    ? err.message
                    : "Failed to load progress summary.",
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
            <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Parent Dashboard
                    </h1>

                    <p className="mt-2 max-w-3xl text-base text-slate-600">
                        View attendance, grades, reports and progress
                        information for your linked children.
                    </p>

                    {lastUpdatedAt && (
                        <p className="mt-2 text-sm text-slate-500">
                            Last refreshed{" "}
                            {lastUpdatedAt.toLocaleTimeString("en-GB", {
                                hour: "2-digit",
                                minute: "2-digit",
                            })}
                            .
                        </p>
                    )}
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
                    className="w-fit rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {progressLoading ? "Refreshing..." : "Refresh"}
                </button>
            </header>

            <ParentPageState
                loading={pageLoading}
                error={pageError}
                isEmpty={
                    profiles.length === 0 ||
                    !selectedProfile
                }
                loadingMessage="Loading parent dashboard..."
            >
                {selectedProfile && (
                    <>
                        <ChildSelector
                            profiles={profiles}
                            selectedStudentId={selectedStudentId}
                            onSelectStudent={setSelectedStudentId}
                            title="Linked Students"
                            description="Select a child to view their dashboard."
                        />

                        <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5 sm:p-6">
                            <p className="text-sm font-bold uppercase tracking-wide text-blue-700">
                                Selected student
                            </p>

                            <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                                <div>
                                    <h2 className="text-2xl font-extrabold text-slate-950">
                                        {selectedStudentName}
                                    </h2>

                                    <p className="mt-1 text-base text-slate-600">
                                        Overview of current academic progress
                                        and recent activity.
                                    </p>
                                </div>

                                <Link
                                    href="/parent/reports"
                                    className="w-fit rounded-xl bg-blue-600 px-4 py-2 text-base font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                                >
                                    View latest reports
                                </Link>
                            </div>
                        </section>

                        <AttendanceSummaryCards
                            profile={selectedProfile}
                        />

                        <section
                            aria-label="Student progress summary"
                            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
                        >
                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Attendance
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {formatPercentage(
                                        progress?.attendance_percentage,
                                    )}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Overall recorded attendance.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Assignment Average
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {formatPercentage(
                                        progress?.average_assignment_score,
                                    )}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Average across graded assignments.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Published Reports
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {getProgressCardValue(
                                        progress?.report_count,
                                    )}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Reports currently available to view.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Recent Feedback
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {getProgressCardValue(
                                        progress?.recent_feedback_count,
                                    )}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Marked submissions with feedback.
                                </p>
                            </div>
                        </section>

                        <section className="grid gap-4 lg:grid-cols-2">
                            <article className="rounded-2xl border bg-white p-6">
                                <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                    Latest Report
                                </p>

                                <h2 className="mt-2 text-xl font-bold text-slate-950">
                                    {progress?.latest_report_title ??
                                        "No published report available"}
                                </h2>

                                <p className="mt-2 text-base text-slate-600">
                                    Open the reports area to read published
                                    teacher feedback and download report PDFs.
                                </p>

                                <Link
                                    href="/parent/reports"
                                    className="mt-5 inline-flex rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-base font-semibold text-blue-700 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-400"
                                >
                                    View reports
                                </Link>
                            </article>

                            <article className="rounded-2xl border bg-white p-6">
                                <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                    Assignments Completed
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {getProgressCardValue(
                                        progress?.assignments_completed,
                                    )}
                                </p>

                                <p className="mt-2 text-base text-slate-600">
                                    Review marks and recent teacher feedback in
                                    the grades area.
                                </p>

                                <Link
                                    href="/parent/grades"
                                    className="mt-5 inline-flex rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-base font-semibold text-blue-700 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-400"
                                >
                                    View grades
                                </Link>
                            </article>
                        </section>

                        <section className="rounded-2xl border bg-white p-4 sm:p-6">
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        Recent Attendance
                                    </h2>

                                    <p className="mt-1 text-base text-slate-600">
                                        The ten most recent attendance records
                                        for {selectedStudentName}.
                                    </p>
                                </div>

                                <Link
                                    href="/parent/attendance"
                                    className="shrink-0 font-semibold text-blue-600 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
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

                        <section>
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Quick Actions
                                </h2>

                                <p className="mt-1 text-base text-slate-600">
                                    Open the main parent portal sections.
                                </p>
                            </div>

                            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                                {QUICK_ACTIONS.map((action) => (
                                    <Link
                                        key={action.href}
                                        href={action.href}
                                        className="rounded-2xl border bg-white p-5 transition hover:border-blue-300 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                                    >
                                        <h3 className="text-lg font-bold text-slate-950">
                                            {action.title}
                                        </h3>

                                        <p className="mt-2 text-sm leading-6 text-slate-600">
                                            {action.description}
                                        </p>

                                        <p className="mt-4 font-semibold text-blue-600">
                                            Open section →
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
