"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
    listReportSessions,
    type ReportSession,
} from "@/lib/report-sessions";
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
    | "tutor_review"
    | "returned_by_tutor"
    | "ready_for_smt"
    | "returned_by_smt"
    | "approved"
    | "published";

type ReportSessionGroup = {
    reportSessionId: number | null;
    title: string;
    reports: StudentReport[];
    statusCounts: Record<string, number>;
};

type ReturnEditorState = {
    reportId: number;
    comments: string;
} | null;

const STATUS_DRAFT = "draft";
const STATUS_SUBMITTED = "submitted";
const STATUS_TUTOR_REVIEW = "tutor_review";
const STATUS_RETURNED_BY_TUTOR = "returned_by_tutor";
const STATUS_READY_FOR_SMT = "ready_for_smt";
const STATUS_RETURNED_BY_SMT = "returned_by_smt";
const STATUS_APPROVED = "approved";
const STATUS_PUBLISHED = "published";

const EMPTY_DASHBOARD: StudentReportReviewDashboard = {
    draft: 0,
    submitted: 0,
    approved: 0,
    published: 0,
};

const REVIEWABLE_STATUSES = new Set([
    STATUS_SUBMITTED,
    STATUS_TUTOR_REVIEW,
    STATUS_READY_FOR_SMT,
]);

const STATUS_OPTIONS: Array<{
    value: StatusFilter;
    label: string;
}> = [
        { value: "submitted", label: "Awaiting review" },
        { value: "tutor_review", label: "Tutor review" },
        { value: "ready_for_smt", label: "Ready for SMT" },
        { value: "returned_by_tutor", label: "Returned by tutor" },
        { value: "returned_by_smt", label: "Returned by SMT" },
        { value: "approved", label: "Approved" },
        { value: "published", label: "Published" },
        { value: "draft", label: "Draft" },
        { value: "all", label: "All reports" },
    ];

function formatDate(value: string | null | undefined): string {
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
    switch (status) {
        case STATUS_DRAFT:
            return "Draft";
        case STATUS_SUBMITTED:
            return "Submitted";
        case STATUS_TUTOR_REVIEW:
            return "Tutor review";
        case STATUS_RETURNED_BY_TUTOR:
            return "Returned by tutor";
        case STATUS_READY_FOR_SMT:
            return "Ready for SMT";
        case STATUS_RETURNED_BY_SMT:
            return "Returned by SMT";
        case STATUS_APPROVED:
            return "Approved";
        case STATUS_PUBLISHED:
            return "Published";
        default:
            return status.replaceAll("_", " ");
    }
}

function getStatusClassName(status: string): string {
    switch (status) {
        case STATUS_PUBLISHED:
            return "bg-green-50 text-green-700";
        case STATUS_APPROVED:
            return "bg-blue-50 text-blue-700";
        case STATUS_SUBMITTED:
        case STATUS_TUTOR_REVIEW:
        case STATUS_READY_FOR_SMT:
            return "bg-purple-50 text-purple-700";
        case STATUS_RETURNED_BY_TUTOR:
        case STATUS_RETURNED_BY_SMT:
            return "bg-red-50 text-red-700";
        default:
            return "bg-amber-50 text-amber-700";
    }
}

function getReportTimestamp(report: StudentReport): number {
    const value =
        report.submitted_at ??
        report.updated_at ??
        report.created_at;

    const timestamp = new Date(value).getTime();

    return Number.isNaN(timestamp) ? 0 : timestamp;
}

function isPublished(report: StudentReport): boolean {
    return report.published || report.status === STATUS_PUBLISHED;
}

function matchesStatus(
    report: StudentReport,
    statusFilter: StatusFilter,
): boolean {
    if (statusFilter === "all") {
        return true;
    }

    if (statusFilter === STATUS_PUBLISHED) {
        return isPublished(report);
    }

    if (isPublished(report)) {
        return false;
    }

    return report.status === statusFilter;
}

export default function SchoolAdminReportsPage() {
    const router = useRouter();

    const [reports, setReports] = useState<StudentReport[]>([]);
    const [reportSessions, setReportSessions] = useState<ReportSession[]>([]);
    const [dashboard, setDashboard] =
        useState<StudentReportReviewDashboard>(EMPTY_DASHBOARD);

    const [statusFilter, setStatusFilter] =
        useState<StatusFilter>("submitted");
    const [sessionFilter, setSessionFilter] = useState("all");
    const [searchQuery, setSearchQuery] = useState("");

    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState<number | null>(null);
    const [publishingSessionId, setPublishingSessionId] =
        useState<number | null>(null);
    const [returnEditor, setReturnEditor] =
        useState<ReturnEditorState>(null);

    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(
        null,
    );

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const [reportData, dashboardData, sessionData] =
                await Promise.all([
                    listStudentReports(),
                    getStudentReportReviewDashboard(),
                    listReportSessions(),
                ]);

            setReports(reportData);
            setDashboard(dashboardData);
            setReportSessions(sessionData);
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

    const sessionTitleById = useMemo(
        () =>
            new Map(
                reportSessions.map((session) => [
                    session.id,
                    session.title,
                ]),
            ),
        [reportSessions],
    );

    const statusCounts = useMemo(() => {
        const counts: Record<string, number> = {
            draft: 0,
            submitted: 0,
            tutor_review: 0,
            returned_by_tutor: 0,
            ready_for_smt: 0,
            returned_by_smt: 0,
            approved: 0,
            published: 0,
        };

        for (const report of reports) {
            if (isPublished(report)) {
                counts.published += 1;
                continue;
            }

            counts[report.status] = (counts[report.status] ?? 0) + 1;
        }

        return counts;
    }, [reports]);

    const filteredReports = useMemo(() => {
        const normalisedSearch = searchQuery.trim().toLowerCase();

        return [...reports]
            .filter((report) => matchesStatus(report, statusFilter))
            .filter((report) =>
                sessionFilter === "all"
                    ? true
                    : String(report.report_session_id ?? "none") ===
                    sessionFilter,
            )
            .filter((report) => {
                if (!normalisedSearch) {
                    return true;
                }

                const searchableText = [
                    report.title,
                    report.report_text,
                    report.review_comments ?? "",
                    String(report.student_id),
                    String(report.teacher_id ?? ""),
                    report.academic_year,
                    report.term ?? "",
                    report.status,
                ]
                    .join(" ")
                    .toLowerCase();

                return searchableText.includes(normalisedSearch);
            })
            .sort(
                (first, second) =>
                    getReportTimestamp(second) -
                    getReportTimestamp(first),
            );
    }, [reports, searchQuery, sessionFilter, statusFilter]);

    const groupedReports = useMemo<ReportSessionGroup[]>(() => {
        const groups = new Map<string, ReportSessionGroup>();

        for (const report of filteredReports) {
            const key = String(report.report_session_id ?? "none");

            if (!groups.has(key)) {
                const sessionTitle =
                    report.report_session_id === null
                        ? "Reports Without Session"
                        : sessionTitleById.get(report.report_session_id) ??
                        `Report Session ${report.report_session_id}`;

                groups.set(key, {
                    reportSessionId: report.report_session_id,
                    title: sessionTitle,
                    reports: [],
                    statusCounts: {},
                });
            }

            const group = groups.get(key);

            if (!group) {
                continue;
            }

            group.reports.push(report);

            const status = isPublished(report)
                ? STATUS_PUBLISHED
                : report.status;

            group.statusCounts[status] =
                (group.statusCounts[status] ?? 0) + 1;
        }

        return Array.from(groups.values()).sort((first, second) => {
            if (
                first.reportSessionId === null &&
                second.reportSessionId !== null
            ) {
                return 1;
            }

            if (
                first.reportSessionId !== null &&
                second.reportSessionId === null
            ) {
                return -1;
            }

            return (
                (second.reportSessionId ?? 0) -
                (first.reportSessionId ?? 0)
            );
        });
    }, [filteredReports, sessionTitleById]);

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

    function openReturnEditor(report: StudentReport) {
        setError(null);
        setSuccessMessage(null);
        setReturnEditor({
            reportId: report.id,
            comments: report.review_comments ?? "",
        });
    }

    async function handleReturnReport(report: StudentReport) {
        if (!returnEditor || returnEditor.reportId !== report.id) {
            return;
        }

        const reviewComments = returnEditor.comments.trim();

        if (!reviewComments) {
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
                review_comments: reviewComments,
            });

            setReturnEditor(null);
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
            "Publish all approved reports in this report session? Published reports will become visible to authorised parents.",
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
        if (report.status !== STATUS_DRAFT || isPublished(report)) {
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

    const summaryCards = [
        {
            label: "Draft",
            value: dashboard.draft,
            filter: "draft" as StatusFilter,
            valueClass: "text-amber-600",
            hoverClass: "hover:border-amber-300",
        },
        {
            label: "Awaiting Review",
            value:
                statusCounts.submitted +
                statusCounts.tutor_review +
                statusCounts.ready_for_smt,
            filter: "submitted" as StatusFilter,
            valueClass: "text-purple-600",
            hoverClass: "hover:border-purple-300",
        },
        {
            label: "Approved",
            value: dashboard.approved,
            filter: "approved" as StatusFilter,
            valueClass: "text-blue-600",
            hoverClass: "hover:border-blue-300",
        },
        {
            label: "Published",
            value: dashboard.published,
            filter: "published" as StatusFilter,
            valueClass: "text-green-600",
            hoverClass: "hover:border-green-300",
        },
    ];

    return (
        <main className="space-y-6 p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Report Review &amp; Publishing
                    </h1>

                    <p className="mt-2 max-w-3xl text-base text-slate-600">
                        Review submitted reports, return reports requiring
                        correction, approve completed reports and publish
                        approved sessions for parent access.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => router.back()}
                    className="w-fit rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-bold text-slate-700 hover:bg-slate-50"
                >
                    ← Back
                </button>
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
                {summaryCards.map((card) => (
                    <button
                        key={card.label}
                        type="button"
                        onClick={() => setStatusFilter(card.filter)}
                        className={`rounded-2xl border bg-white p-5 text-left transition hover:shadow-sm ${card.hoverClass}`}
                    >
                        <p className="text-base font-medium text-slate-600">
                            {card.label}
                        </p>
                        <p
                            className={`mt-2 text-3xl font-bold ${card.valueClass}`}
                        >
                            {card.value}
                        </p>
                    </button>
                ))}
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <div className="flex flex-col gap-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
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

                        <button
                            type="button"
                            disabled={loading}
                            onClick={() => void loadData()}
                            className="w-fit rounded-xl border border-slate-300 px-4 py-2 text-base font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {loading ? "Refreshing..." : "Refresh"}
                        </button>
                    </div>

                    <div className="grid gap-4 md:grid-cols-3">
                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
                                Status
                            </span>

                            <select
                                value={statusFilter}
                                onChange={(event) =>
                                    setStatusFilter(
                                        event.target.value as StatusFilter,
                                    )
                                }
                                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base text-slate-900"
                            >
                                {STATUS_OPTIONS.map((option) => (
                                    <option
                                        key={option.value}
                                        value={option.value}
                                    >
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
                                Report Session
                            </span>

                            <select
                                value={sessionFilter}
                                onChange={(event) =>
                                    setSessionFilter(event.target.value)
                                }
                                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base text-slate-900"
                            >
                                <option value="all">All sessions</option>
                                {reportSessions.map((session) => (
                                    <option
                                        key={session.id}
                                        value={String(session.id)}
                                    >
                                        {session.title}
                                        {session.active ? " (Active)" : ""}
                                    </option>
                                ))}
                                <option value="none">
                                    Reports without session
                                </option>
                            </select>
                        </label>

                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
                                Search
                            </span>

                            <input
                                value={searchQuery}
                                onChange={(event) =>
                                    setSearchQuery(event.target.value)
                                }
                                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base text-slate-900"
                                placeholder="Title, pupil ID, teacher ID or text"
                            />
                        </label>
                    </div>
                </div>

                {loading ? (
                    <p className="mt-6 text-base text-slate-600">
                        Loading reports...
                    </p>
                ) : groupedReports.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-base text-slate-600">
                        No reports were found for the selected filters.
                    </div>
                ) : (
                    <div className="mt-6 grid gap-6">
                        {groupedReports.map((group) => {
                            const approvedCount =
                                group.statusCounts[STATUS_APPROVED] ?? 0;

                            return (
                                <section
                                    key={group.reportSessionId ?? "none"}
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
                                                {group.statusCounts[
                                                    STATUS_DRAFT
                                                ] ?? 0}{" "}
                                                draft
                                                {" · "}
                                                {group.statusCounts[
                                                    STATUS_SUBMITTED
                                                ] ?? 0}{" "}
                                                submitted
                                                {" · "}
                                                {group.statusCounts[
                                                    STATUS_READY_FOR_SMT
                                                ] ?? 0}{" "}
                                                ready for SMT
                                                {" · "}
                                                {approvedCount} approved
                                                {" · "}
                                                {group.statusCounts[
                                                    STATUS_PUBLISHED
                                                ] ?? 0}{" "}
                                                published
                                            </p>
                                        </div>

                                        {group.reportSessionId !== null && (
                                            <button
                                                type="button"
                                                disabled={
                                                    approvedCount === 0 ||
                                                    publishingSessionId ===
                                                    group.reportSessionId
                                                }
                                                onClick={() =>
                                                    void handlePublishSession(
                                                        group.reportSessionId as number,
                                                    )
                                                }
                                                className="w-fit rounded-xl bg-green-600 px-4 py-2 text-base font-semibold text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
                                            >
                                                {publishingSessionId ===
                                                    group.reportSessionId
                                                    ? "Publishing..."
                                                    : "Publish Approved Reports"}
                                            </button>
                                        )}
                                    </div>

                                    <div className="mt-4 grid gap-4">
                                        {group.reports.map((report) => {
                                            const published =
                                                isPublished(report);
                                            const returnEditorOpen =
                                                returnEditor?.reportId ===
                                                report.id;

                                            return (
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
                                                                Pupil ID{" "}
                                                                {
                                                                    report.student_id
                                                                }
                                                                {" · "}
                                                                Teacher ID{" "}
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
                                                                    published
                                                                        ? STATUS_PUBLISHED
                                                                        : report.status,
                                                                )}`}
                                                            >
                                                                {formatStatus(
                                                                    published
                                                                        ? STATUS_PUBLISHED
                                                                        : report.status,
                                                                )}
                                                            </span>

                                                            {published && (
                                                                <span className="w-fit rounded-full bg-green-50 px-3 py-1 text-sm font-bold text-green-700">
                                                                    Parent
                                                                    Visible
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {report.work_covered && (
                                                        <div className="mt-4">
                                                            <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                                                Work Covered
                                                            </p>
                                                            <p className="mt-1 whitespace-pre-line rounded-xl bg-slate-50 p-4 text-base leading-7 text-slate-800">
                                                                {
                                                                    report.work_covered
                                                                }
                                                            </p>
                                                        </div>
                                                    )}

                                                    {report.teacher_notes && (
                                                        <div className="mt-4">
                                                            <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                                                Teacher Notes
                                                            </p>
                                                            <p className="mt-1 whitespace-pre-line rounded-xl bg-slate-50 p-4 text-base leading-7 text-slate-800">
                                                                {
                                                                    report.teacher_notes
                                                                }
                                                            </p>
                                                        </div>
                                                    )}

                                                    {report.generated_report_text && (
                                                        <div className="mt-4">
                                                            <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                                                Generated Draft
                                                            </p>
                                                            <p className="mt-1 whitespace-pre-line rounded-xl border border-blue-100 bg-blue-50 p-4 text-base leading-7 text-slate-800">
                                                                {
                                                                    report.generated_report_text
                                                                }
                                                            </p>
                                                        </div>
                                                    )}

                                                    <div className="mt-4">
                                                        <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                                            Final Report
                                                        </p>
                                                        <p className="mt-1 whitespace-pre-line rounded-xl border border-slate-200 bg-white p-4 text-base leading-7 text-slate-800">
                                                            {
                                                                report.report_text
                                                            }
                                                        </p>
                                                    </div>

                                                    {report.review_comments && (
                                                        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                                                            <p className="font-semibold text-amber-900">
                                                                Review Feedback
                                                            </p>
                                                            <p className="mt-1 whitespace-pre-line text-base leading-7 text-amber-800">
                                                                {
                                                                    report.review_comments
                                                                }
                                                            </p>
                                                        </div>
                                                    )}

                                                    {returnEditorOpen && (
                                                        <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4">
                                                            <label className="grid gap-2">
                                                                <span className="text-base font-bold text-amber-900">
                                                                    Feedback
                                                                    for the
                                                                    teacher
                                                                </span>

                                                                <textarea
                                                                    value={
                                                                        returnEditor.comments
                                                                    }
                                                                    onChange={(
                                                                        event,
                                                                    ) =>
                                                                        setReturnEditor(
                                                                            {
                                                                                reportId:
                                                                                    report.id,
                                                                                comments:
                                                                                    event
                                                                                        .target
                                                                                        .value,
                                                                            },
                                                                        )
                                                                    }
                                                                    className="min-h-32 rounded-xl border border-amber-300 bg-white px-4 py-3 text-base leading-7 text-slate-900"
                                                                    placeholder="Explain clearly what should be corrected."
                                                                />
                                                            </label>

                                                            <div className="mt-3 flex flex-wrap gap-3">
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
                                                                    className="rounded-xl bg-amber-600 px-4 py-2 text-base font-semibold text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
                                                                >
                                                                    {savingId ===
                                                                        report.id
                                                                        ? "Returning..."
                                                                        : "Confirm Return"}
                                                                </button>

                                                                <button
                                                                    type="button"
                                                                    disabled={
                                                                        savingId ===
                                                                        report.id
                                                                    }
                                                                    onClick={() =>
                                                                        setReturnEditor(
                                                                            null,
                                                                        )
                                                                    }
                                                                    className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-700 hover:bg-slate-50"
                                                                >
                                                                    Cancel
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )}

                                                    <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-200 pt-4">
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                router.push(
                                                                    `/teacher/reports/${report.id}`,
                                                                )
                                                            }
                                                            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-700 hover:bg-slate-50"
                                                        >
                                                            Open Full Report
                                                        </button>

                                                        {REVIEWABLE_STATUSES.has(
                                                            report.status,
                                                        ) &&
                                                            !published && (
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
                                                                            openReturnEditor(
                                                                                report,
                                                                            )
                                                                        }
                                                                        className="rounded-xl border border-amber-300 px-4 py-2 text-base font-semibold text-amber-800 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                                    >
                                                                        Return
                                                                        for
                                                                        Correction
                                                                    </button>
                                                                </>
                                                            )}

                                                        {report.status ===
                                                            STATUS_DRAFT &&
                                                            !published && (
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
                                                                    Delete
                                                                    Draft
                                                                </button>
                                                            )}

                                                        {report.status ===
                                                            STATUS_APPROVED &&
                                                            !published && (
                                                                <p className="self-center text-base font-medium text-blue-700">
                                                                    Ready for
                                                                    session
                                                                    publication.
                                                                </p>
                                                            )}

                                                        {published && (
                                                            <p className="self-center text-base font-medium text-green-700">
                                                                Published and
                                                                available to
                                                                authorised
                                                                parents.
                                                            </p>
                                                        )}
                                                    </div>
                                                </article>
                                            );
                                        })}
                                    </div>
                                </section>
                            );
                        })}
                    </div>
                )}
            </section>
        </main>
    );
}
