"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import AttendanceHistoryTable from "@/components/parent/AttendanceHistoryTable";
import AttendanceSummaryCards from "@/components/parent/AttendanceSummaryCards";
import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

import {
    getParentStudentProgress,
    type StudentProgressSummary,
} from "@/lib/services/parentProgress";

function formatPercentage(value: number | null): string {
    if (value === null) {
        return "N/A";
    }

    return `${value}%`;
}

export default function ParentDashboardPage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading,
        error,
    } = useParentChildren();

    const [progress, setProgress] =
        useState<StudentProgressSummary | null>(null);

    const [progressLoading, setProgressLoading] = useState(false);

    const [progressError, setProgressError] =
        useState<string | null>(null);

    useEffect(() => {
        async function loadProgress() {
            if (!selectedStudentId) {
                setProgress(null);
                return;
            }

            try {
                setProgressLoading(true);
                setProgressError(null);

                const data = await getParentStudentProgress(
                    selectedStudentId,
                );

                setProgress(data);
            } catch (err) {
                setProgressError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load progress summary.",
                );
            } finally {
                setProgressLoading(false);
            }
        }

        void loadProgress();
    }, [selectedStudentId]);

    const recentHistory = useMemo(() => {
        return selectedProfile?.history.slice(0, 10) ?? [];
    }, [selectedProfile]);

    const pageLoading = loading || progressLoading;
    const pageError = error || progressError;

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Parent Dashboard
                </h1>

                <p className="mt-2 text-slate-500">
                    View your child&apos;s attendance, grades,
                    reports, and progress summary.
                </p>
            </div>

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
                            onSelectStudent={
                                setSelectedStudentId
                            }
                            title="Linked Students"
                            description="Select a child to view their dashboard."
                        />

                        <AttendanceSummaryCards
                            profile={selectedProfile}
                        />

                        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Attendance
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {formatPercentage(
                                        progress?.attendance_percentage ??
                                        null,
                                    )}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Overall attendance percentage.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Assignment Average
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {formatPercentage(
                                        progress?.average_assignment_score ??
                                        null,
                                    )}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Across graded assignments.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Reports
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {progress?.report_count ?? 0}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Published academic reports.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Feedback
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {progress?.recent_feedback_count ??
                                        0}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Graded submissions with feedback.
                                </p>
                            </div>
                        </section>

                        <section className="grid gap-4 lg:grid-cols-2">
                            <div className="rounded-2xl border bg-white p-6">
                                <h2 className="text-xl font-bold text-slate-950">
                                    Latest Report
                                </h2>

                                <p className="mt-2 text-slate-500">
                                    {progress?.latest_report_title ??
                                        "No reports have been published yet."}
                                </p>

                                <Link
                                    href="/parent/reports"
                                    className="mt-4 inline-block font-semibold text-blue-600 hover:text-blue-700"
                                >
                                    View reports
                                </Link>
                            </div>

                            <div className="rounded-2xl border bg-white p-6">
                                <h2 className="text-xl font-bold text-slate-950">
                                    Assignments Completed
                                </h2>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {progress?.assignments_completed ??
                                        0}
                                </p>

                                <Link
                                    href="/parent/grades"
                                    className="mt-4 inline-block font-semibold text-blue-600 hover:text-blue-700"
                                >
                                    View grades
                                </Link>
                            </div>
                        </section>

                        <section className="rounded-2xl border bg-white p-6">
                            <div className="flex items-center justify-between gap-4">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        Recent Attendance
                                    </h2>

                                    <p className="mt-1 text-sm text-slate-500">
                                        Latest attendance records
                                        for the selected student.
                                    </p>
                                </div>

                                <Link
                                    href="/parent/attendance"
                                    className="shrink-0 font-semibold text-blue-600 hover:text-blue-700"
                                >
                                    View full history
                                </Link>
                            </div>

                            <AttendanceHistoryTable
                                records={recentHistory}
                            />
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}