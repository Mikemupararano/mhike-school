"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { publishReportSession } from "@/lib/report-publishing";
import {
    approveStudentReport,
    deleteStudentReport,
    getStudentReportReviewDashboard,
    listStudentReports,
    returnStudentReport,
    type StudentReport,
    type StudentReportReviewDashboard,
} from "@/lib/services/studentReports";

type StatusFilter =
    | "all"
    | "draft"
    | "submitted"
    | "approved"
    | "published";

type ReportSessionGroup = {
    report_session_id: number | null;
    title: string;
    reports: StudentReport[];
    draftCount: number;
    submittedCount: number;
    approvedCount: number;
    publishedCount: number;
};

const REPORT_STATUS_DRAFT = "draft";
const REPORT_STATUS_SUBMITTED = "submitted";
const REPORT_STATUS_APPROVED = "approved";
const REPORT_STATUS_PUBLISHED = "published";

const EMPTY_DASHBOARD: StudentReportReviewDashboard = {
    draft: 0,
    submitted: 0,
    approved: 0,
    published: 0,
};

function formatDate(value: string | null): string {
    if (!value) {
        return "Not recorded";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Invalid date";
    }

    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function formatStatus(status: string): string {
    return status
        .split("_")
        .map(
            (word) =>
                word.charAt(0).toUpperCase() +
                word.slice(1).toLowerCase(),
        )
        .join(" ");
}

function getGroupTitle(report: StudentReport): string {
    if (report.report_session_id !== null) {
        return `Report Session ${report.report_session_id}`;
    }

    return "Reports Without Session";
}

function getStatusClassName(status: string): string {
    switch (status) {
        case REPORT_STATUS_PUBLISHED:
            return "bg-green-50 text-green-700";

        case REPORT_STATUS_APPROVED:
            return "bg-blue-50 text-blue-700";

        case REPORT_STATUS_SUBMITTED:
            return "bg-purple-50 text-purple-700";

        default:
            return "bg-amber-50 text-amber-700";
    }
}

export default function SchoolAdminReportsPage() {
    const [reports, setReports] = useState<StudentReport[]>([]);
    const [dashboard, setDashboard] =
        useState<StudentReportReviewDashboard>(EMPTY_DASHBOARD);

    const [statusFilter, setStatusFilter] =
        useState<StatusFilter>("submitted");

    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState<number | null>(null);
    const [publishingSessionId, setPublishingSessionId] =
        useState<number | null>(null);

    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(
        null,
    );

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const [reportData, dashboardData] = await Promise.all([
                listStudentReports(),
                getStudentReportReviewDashboard(),
            ]);

            setReports(reportData);
            setDashboard(dashboardData);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load report review information.",
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadData();
    }, [loadData]);

    const filteredReports = useMemo(() => {
        const sorted = [...reports].sort((first, second) => {
            const firstDate =
                first.submitted_at ?? first.created_at;
            const secondDate =
                second.submitted_at ?? second.created_at;

            return (
                new Date(secondDate).getTime() -
                new Date(firstDate).getTime()
            );
        });

        if (statusFilter === "all") {
            return sorted;
        }

        if (statusFilter === REPORT_STATUS_PUBLISHED) {
            return sorted.filter(
                (report) =>
                    report.published ||
                    report.status === REPORT_STATUS_PUBLISHED,
            );
        }

        return sorted.filter(
            (report) =>
                report.status === statusFilter && !report.published,
        );
    }, [reports, statusFilter]);

    const groupedReports = useMemo<ReportSessionGroup[]>(() => {
        const groups = new Map<string, ReportSessionGroup>();

        for (const report of filteredReports) {
            const key = String(report.report_session_id ?? "none");

            if (!groups.has(key)) {
                groups.set(key, {
                    report_session_id: report.report_session_id,
                    title: getGroupTitle(report),
                    reports: [],
                    draftCount: 0,
                    submittedCount: 0,
                    approvedCount: 0,
                    publishedCount: 0,
                });
            }

            const group = groups.get(key);

            if (!group) {
                continue;
            }

            group.reports.push(report);

            if (
                report.published ||
                report.status === REPORT_STATUS_PUBLISHED
            ) {
                group.publishedCount += 1;
            } else if (report.status === REPORT_STATUS_APPROVED) {
                group.approvedCount += 1;
            } else if (report.status === REPORT_STATUS_SUBMITTED) {
                group.submittedCount += 1;
            } else {
                group.draftCount += 1;
            }
        }

        return Array.from(groups.values()).sort((first, second) => {
            if (
                first.report_session_id === null &&
                second.report_session_id !== null
            ) {
                return 1;
            }

            if (
                first.report_session_id !== null &&
                second.report_session_id === null
            ) {
                return -1;
            }

            return (
                (second.report_session_id ?? 0) -
                (first.report_session_id ?? 0)
            );
        });
    }, [filteredReports]);

    async function handleApproveReport(report: StudentReport) {
        try {
            setSavingId(report.id);
            setError(null);
            setSuccessMessage(null);

            await approveStudentReport(report.id);
            await loadData();

            setSuccessMessage("Report approved successfully.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to approve report.",
            );
        } finally {
            setSavingId(null);
        }
    }

    async function handleReturnReport(report: StudentReport) {
        const reviewComments = window.prompt(
            "Enter feedback explaining what the teacher should correct:",
            report.review_comments ?? "",
        );

        if (reviewComments === null) {
            return;
        }

        const trimmedComments = reviewComments.trim();

        if (!trimmedComments) {
            setError(
                "Please enter feedback before returning the report.",
            );
            return;
        }

        try {
            setSavingId(report.id);
            setError(null);
            setSuccessMessage(null);

            await returnStudentReport(report.id, {
                review_comments: trimmedComments,
            });

            await loadData();

            setSuccessMessage(
                "Report returned to the teacher for correction.",
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to return report for correction.",
            );
        } finally {
            setSavingId(null);
        }
    }

    async function handlePublishSession(reportSessionId: number) {
        const confirmed = window.confirm(
            "Publish all approved reports in this report session?",
        );

        if (!confirmed) {
            return;
        }

        try {
            setPublishingSessionId(reportSessionId);
            setError(null);
            setSuccessMessage(null);

            const result = await publishReportSession(reportSessionId);

            await loadData();

            setSuccessMessage(
                `${result.published_count} ${result.published_count === 1 ? "report" : "reports"
                } published.`,
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to publish the report session.",
            );
        } finally {
            setPublishingSessionId(null);
        }
    }

    async function handleDeleteReport(report: StudentReport) {
        if (report.status !== REPORT_STATUS_DRAFT || report.published) {
            setError("Only unpublished draft reports can be deleted.");
            return;
        }

        const confirmed = window.confirm(
            "Delete this draft report? This cannot be undone.",
        );

        if (!confirmed) {
            return;
        }

        try {
            setSavingId(report.id);
            setError(null);
            setSuccessMessage(null);

            await deleteStudentReport(report.id);
            await loadData();

            setSuccessMessage("Draft report deleted.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to delete report.",
            );
        } finally {
            setSavingId(null);
        }
    }

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Report Review &amp; Publishing
                </h1>

                <p className="mt-2 max-w-3xl text-slate-600">
                    Review submitted reports, return reports requiring
                    correction, approve completed reports and publish approved
                    report sessions for parent access.
                </p>
            </div>

            {error && (
                <div
                    role="alert"
                    className="rounded-2xl border border-red-200 bg-red-50 p-4 text-base font-medium text-red-700"
                >
                    {error}
                </div>
            )}

            {successMessage && (
                <div
                    role="status"
                    className="rounded-2xl border border-green-200 bg-green-50 p-4 text-base font-medium text-green-700"
                >
                    {successMessage}
                </div>
            )}

            <section
                aria-label="Report status summary"
                className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
            >
                <button
                    type="button"
                    onClick={() => setStatusFilter("draft")}
                    className="rounded-2xl border bg-white p-5 text-left transition hover:border-amber-300 hover:shadow-sm"
                >
                    <p className="text-base font-medium text-slate-600">
                        Draft
                    </p>
                    <p className="mt-2 text-3xl font-bold text-amber-600">
                        {dashboard.draft}
                    </p>
                </button>

                <button
                    type="button"
                    onClick={() => setStatusFilter("submitted")}
                    className="rounded-2xl border bg-white p-5 text-left transition hover:border-purple-300 hover:shadow-sm"
                >
                    <p className="text-base font-medium text-slate-600">
                        Awaiting Review
                    </p>
                    <p className="mt-2 text-3xl font-bold text-purple-600">
                        {dashboard.submitted}
                    </p>
                </button>

                <button
                    type="button"
                    onClick={() => setStatusFilter("approved")}
                    className="rounded-2xl border bg-white p-5 text-left transition hover:border-blue-300 hover:shadow-sm"
                >
                    <p className="text-base font-medium text-slate-600">
                        Approved
                    </p>
                    <p className="mt-2 text-3xl font-bold text-blue-600">
                        {dashboard.approved}
                    </p>
                </button>

                <button
                    type="button"
                    onClick={() => setStatusFilter("published")}
                    className="rounded-2xl border bg-white p-5 text-left transition hover:border-green-300 hover:shadow-sm"
                >
                    <p className="text-base font-medium text-slate-600">
                        Published
                    </p>
                    <p className="mt-2 text-3xl font-bold text-green-600">
                        {dashboard.published}
                    </p>
                </button>
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-950">
                            Reports
                        </h2>

                        <p className="mt-1 text-base text-slate-600">
                            {filteredReports.length}{" "}
                            {filteredReports.length === 1
                                ? "report"
                                : "reports"}{" "}
                            shown.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                        <label
                            htmlFor="report-status-filter"
                            className="text-base font-semibold text-slate-700"
                        >
                            Status
                        </label>

                        <select
                            id="report-status-filter"
                            value={statusFilter}
                            onChange={(event) =>
                                setStatusFilter(
                                    event.target.value as StatusFilter,
                                )
                            }
                            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base text-slate-900"
                        >
                            <option value="submitted">
                                Awaiting review
                            </option>
                            <option value="approved">Approved</option>
                            <option value="draft">Draft</option>
                            <option value="published">Published</option>
                            <option value="all">All reports</option>
                        </select>

                        <button
                            type="button"
                            disabled={loading}
                            onClick={() => void loadData()}
                            className="rounded-xl border border-slate-300 px-4 py-2 text-base font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            Refresh
                        </button>
                    </div>
                </div>

                {loading ? (
                    <p className="mt-6 text-base text-slate-600">
                        Loading reports...
                    </p>
                ) : groupedReports.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-base text-slate-600">
                        No reports were found for this status.
                    </div>
                ) : (
                    <div className="mt-6 grid gap-6">
                        {groupedReports.map((group) => (
                            <section
                                key={group.report_session_id ?? "none"}
                                className="rounded-2xl border bg-slate-50 p-5"
                            >
                                <div className="flex flex-col gap-4 border-b border-slate-200 pb-4 md:flex-row md:items-center md:justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-950">
                                            {group.title}
                                        </h3>

                                        <p className="mt-1 text-base text-slate-600">
                                            {group.reports.length}{" "}
                                            {group.reports.length === 1
                                                ? "report"
                                                : "reports"}
                                            {" · "}
                                            {group.draftCount} draft
                                            {" · "}
                                            {group.submittedCount} submitted
                                            {" · "}
                                            {group.approvedCount} approved
                                            {" · "}
                                            {group.publishedCount} published
                                        </p>
                                    </div>

                                    {group.report_session_id !== null && (
                                        <button
                                            type="button"
                                            disabled={
                                                group.approvedCount === 0 ||
                                                publishingSessionId ===
                                                group.report_session_id
                                            }
                                            onClick={() =>
                                                void handlePublishSession(
                                                    group.report_session_id as number,
                                                )
                                            }
                                            className="w-fit rounded-xl bg-green-600 px-4 py-2 text-base font-semibold text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {publishingSessionId ===
                                                group.report_session_id
                                                ? "Publishing..."
                                                : "Publish Approved Reports"}
                                        </button>
                                    )}
                                </div>

                                <div className="mt-4 grid gap-4">
                                    {group.reports.map((report) => (
                                        <article
                                            key={report.id}
                                            className="rounded-2xl border bg-white p-5"
                                        >
                                            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                                <div>
                                                    <h4 className="text-lg font-bold text-slate-950">
                                                        {report.title}
                                                    </h4>

                                                    <p className="mt-1 text-base text-slate-600">
                                                        Student{" "}
                                                        {report.student_id}
                                                        {" · "}
                                                        Teacher{" "}
                                                        {report.teacher_id ??
                                                            "Not assigned"}
                                                        {" · "}
                                                        {
                                                            report.academic_year
                                                        }
                                                        {report.term
                                                            ? ` · ${report.term}`
                                                            : ""}
                                                    </p>

                                                    <p className="mt-1 text-sm text-slate-500">
                                                        Created{" "}
                                                        {formatDate(
                                                            report.created_at,
                                                        )}
                                                        {report.submitted_at
                                                            ? ` · Submitted ${formatDate(
                                                                report.submitted_at,
                                                            )}`
                                                            : ""}
                                                    </p>
                                                </div>

                                                <div className="flex flex-wrap gap-2">
                                                    <span
                                                        className={`w-fit rounded-full px-3 py-1 text-sm font-bold ${getStatusClassName(
                                                            report.status,
                                                        )}`}
                                                    >
                                                        {formatStatus(
                                                            report.status,
                                                        )}
                                                    </span>

                                                    {report.published && (
                                                        <span className="w-fit rounded-full bg-green-50 px-3 py-1 text-sm font-bold text-green-700">
                                                            Parent Visible
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            <p className="mt-4 whitespace-pre-line rounded-xl bg-slate-50 p-4 text-base leading-7 text-slate-800">
                                                {report.report_text}
                                            </p>

                                            {report.review_comments && (
                                                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                                                    <p className="font-semibold text-amber-900">
                                                        Review feedback
                                                    </p>
                                                    <p className="mt-1 whitespace-pre-line text-base leading-7 text-amber-800">
                                                        {
                                                            report.review_comments
                                                        }
                                                    </p>
                                                </div>
                                            )}

                                            <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-200 pt-4">
                                                {report.status ===
                                                    REPORT_STATUS_SUBMITTED &&
                                                    !report.published && (
                                                        <>
                                                            <button
                                                                type="button"
                                                                disabled={
                                                                    savingId ===
                                                                    report.id
                                                                }
                                                                onClick={() =>
                                                                    void handleApproveReport(
                                                                        report,
                                                                    )
                                                                }
                                                                className="rounded-xl bg-blue-600 px-4 py-2 text-base font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                                                            >
                                                                {savingId ===
                                                                    report.id
                                                                    ? "Saving..."
                                                                    : "Approve"}
                                                            </button>

                                                            <button
                                                                type="button"
                                                                disabled={
                                                                    savingId ===
                                                                    report.id
                                                                }
                                                                onClick={() =>
                                                                    void handleReturnReport(
                                                                        report,
                                                                    )
                                                                }
                                                                className="rounded-xl border border-amber-300 px-4 py-2 text-base font-semibold text-amber-800 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                            >
                                                                Return for
                                                                Correction
                                                            </button>
                                                        </>
                                                    )}

                                                {report.status ===
                                                    REPORT_STATUS_DRAFT &&
                                                    !report.published && (
                                                        <button
                                                            type="button"
                                                            disabled={
                                                                savingId ===
                                                                report.id
                                                            }
                                                            onClick={() =>
                                                                void handleDeleteReport(
                                                                    report,
                                                                )
                                                            }
                                                            className="rounded-xl border border-red-200 px-4 py-2 text-base font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                        >
                                                            Delete Draft
                                                        </button>
                                                    )}

                                                {report.status ===
                                                    REPORT_STATUS_APPROVED &&
                                                    !report.published && (
                                                        <p className="self-center text-base font-medium text-blue-700">
                                                            Ready for session
                                                            publication.
                                                        </p>
                                                    )}

                                                {report.published && (
                                                    <p className="self-center text-base font-medium text-green-700">
                                                        Published and available
                                                        to authorised parents.
                                                    </p>
                                                )}
                                            </div>
                                        </article>
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>
                )}
            </section>
        </main>
    );
}