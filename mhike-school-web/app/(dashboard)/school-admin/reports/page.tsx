"use client";

import { useEffect, useMemo, useState } from "react";

import { publishReportSession } from "@/lib/report-publishing";
import {
    deleteStudentReport,
    listStudentReports,
    updateStudentReport,
    type StudentReport,
} from "@/lib/services/studentReports";

type StatusFilter = "all" | "draft" | "published";

type ReportSessionGroup = {
    report_session_id: number | null;
    title: string;
    reports: StudentReport[];
    draftCount: number;
    publishedCount: number;
};

const REPORT_STATUS_DRAFT = "draft";
const REPORT_STATUS_SUBMITTED = "submitted";
const REPORT_STATUS_APPROVED = "approved";
const REPORT_STATUS_PUBLISHED = "published";

function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function getGroupTitle(report: StudentReport): string {
    if (report.report_session_id) {
        return `Report Session ${report.report_session_id}`;
    }

    return "Reports Without Session";
}

function getStatusClassName(status: string): string {
    if (status === REPORT_STATUS_PUBLISHED) {
        return "bg-green-50 text-green-700";
    }

    if (status === REPORT_STATUS_APPROVED) {
        return "bg-blue-50 text-blue-700";
    }

    if (status === REPORT_STATUS_SUBMITTED) {
        return "bg-purple-50 text-purple-700";
    }

    return "bg-amber-50 text-amber-700";
}

export default function SchoolAdminReportsPage() {
    const [reports, setReports] = useState<StudentReport[]>([]);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("draft");
    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState<number | null>(null);
    const [publishingSessionId, setPublishingSessionId] =
        useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    useEffect(() => {
        async function loadReports() {
            try {
                setLoading(true);
                setError(null);

                const data = await listStudentReports();

                setReports(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load reports.",
                );
            } finally {
                setLoading(false);
            }
        }

        void loadReports();
    }, []);

    const overallStats = useMemo(() => {
        const total = reports.length;
        const published = reports.filter((report) => report.published).length;
        const draft = total - published;
        const completion =
            total === 0 ? 0 : Math.round((published / total) * 100);

        return { total, draft, published, completion };
    }, [reports]);

    const filteredReports = useMemo(() => {
        const sorted = [...reports].sort(
            (first, second) =>
                new Date(second.created_at).getTime() -
                new Date(first.created_at).getTime(),
        );

        if (statusFilter === "draft") {
            return sorted.filter((report) => !report.published);
        }

        if (statusFilter === "published") {
            return sorted.filter((report) => report.published);
        }

        return sorted;
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
                    publishedCount: 0,
                });
            }

            const group = groups.get(key);

            if (!group) {
                continue;
            }

            group.reports.push(report);

            if (report.published) {
                group.publishedCount += 1;
            } else {
                group.draftCount += 1;
            }
        }

        return Array.from(groups.values()).sort((first, second) => {
            const firstId = first.report_session_id ?? 0;
            const secondId = second.report_session_id ?? 0;

            return secondId - firstId;
        });
    }, [filteredReports]);

    async function updateReportStatus(
        report: StudentReport,
        status: string,
    ) {
        try {
            setSavingId(report.id);
            setError(null);
            setSuccessMessage(null);

            const updated = await updateStudentReport(report.id, {
                status,
            });

            setReports((current) =>
                current.map((item) =>
                    item.id === updated.id ? updated : item,
                ),
            );

            setSuccessMessage(`Report status updated to ${status}.`);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to update report status.",
            );
        } finally {
            setSavingId(null);
        }
    }

    async function publishReport(report: StudentReport) {
        try {
            setSavingId(report.id);
            setError(null);
            setSuccessMessage(null);

            const updated = await updateStudentReport(report.id, {
                published: true,
            });

            setReports((current) =>
                current.map((item) =>
                    item.id === updated.id ? updated : item,
                ),
            );

            setSuccessMessage("Report published.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to publish report.",
            );
        } finally {
            setSavingId(null);
        }
    }

    async function unpublishReport(report: StudentReport) {
        try {
            setSavingId(report.id);
            setError(null);
            setSuccessMessage(null);

            const updated = await updateStudentReport(report.id, {
                published: false,
            });

            setReports((current) =>
                current.map((item) =>
                    item.id === updated.id ? updated : item,
                ),
            );

            setSuccessMessage("Report returned to draft.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to return report to draft.",
            );
        } finally {
            setSavingId(null);
        }
    }

    async function handlePublishSession(reportSessionId: number) {
        const confirmed = window.confirm(
            "Publish all approved draft reports in this session?",
        );

        if (!confirmed) {
            return;
        }

        try {
            setPublishingSessionId(reportSessionId);
            setError(null);
            setSuccessMessage(null);

            const result = await publishReportSession(reportSessionId);
            const refreshedReports = await listStudentReports();

            setReports(refreshedReports);

            setSuccessMessage(
                `${result.published_count} reports published.`,
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to publish report session.",
            );
        } finally {
            setPublishingSessionId(null);
        }
    }

    async function handleDeleteReport(reportId: number) {
        const confirmed = window.confirm(
            "Delete this report? This cannot be undone.",
        );

        if (!confirmed) {
            return;
        }

        try {
            setSavingId(reportId);
            setError(null);
            setSuccessMessage(null);

            await deleteStudentReport(reportId);

            setReports((current) =>
                current.filter((report) => report.id !== reportId),
            );

            setSuccessMessage("Report deleted.");
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
                    Report Review & Publishing
                </h1>

                <p className="mt-2 max-w-3xl text-slate-500">
                    Review teacher draft reports, approve them, and publish
                    approved reports for parent access.
                </p>
            </div>

            {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                    {error}
                </div>
            )}

            {successMessage && (
                <div className="rounded-2xl border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-700">
                    {successMessage}
                </div>
            )}

            <section className="grid gap-4 md:grid-cols-4">
                <div className="rounded-2xl border bg-white p-5">
                    <p className="text-sm text-slate-500">Total Reports</p>
                    <p className="mt-2 text-3xl font-bold text-slate-950">
                        {overallStats.total}
                    </p>
                </div>

                <div className="rounded-2xl border bg-white p-5">
                    <p className="text-sm text-slate-500">Draft Reports</p>
                    <p className="mt-2 text-3xl font-bold text-amber-600">
                        {overallStats.draft}
                    </p>
                </div>

                <div className="rounded-2xl border bg-white p-5">
                    <p className="text-sm text-slate-500">Published Reports</p>
                    <p className="mt-2 text-3xl font-bold text-green-600">
                        {overallStats.published}
                    </p>
                </div>

                <div className="rounded-2xl border bg-white p-5">
                    <p className="text-sm text-slate-500">Completion</p>
                    <p className="mt-2 text-3xl font-bold text-slate-950">
                        {overallStats.completion}%
                    </p>
                </div>
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-950">
                            Report Sessions
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            {filteredReports.length} report
                            {filteredReports.length === 1 ? "" : "s"} shown.
                        </p>
                    </div>

                    <select
                        value={statusFilter}
                        onChange={(event) =>
                            setStatusFilter(event.target.value as StatusFilter)
                        }
                        className="w-fit rounded-xl border px-3 py-2 text-sm"
                    >
                        <option value="draft">Draft reports</option>
                        <option value="published">Published reports</option>
                        <option value="all">All reports</option>
                    </select>
                </div>

                {loading ? (
                    <p className="mt-6 text-sm text-slate-500">
                        Loading reports...
                    </p>
                ) : groupedReports.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                        No reports found for this filter.
                    </div>
                ) : (
                    <div className="mt-6 grid gap-6">
                        {groupedReports.map((group) => (
                            <section
                                key={group.report_session_id ?? "none"}
                                className="rounded-2xl border bg-slate-50 p-5"
                            >
                                <div className="flex flex-col gap-4 border-b pb-4 md:flex-row md:items-center md:justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-950">
                                            {group.title}
                                        </h3>

                                        <p className="mt-1 text-sm text-slate-500">
                                            {group.reports.length} report
                                            {group.reports.length === 1
                                                ? ""
                                                : "s"}{" "}
                                            · {group.draftCount} draft ·{" "}
                                            {group.publishedCount} published
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        disabled={
                                            group.draftCount === 0 ||
                                            group.report_session_id === null ||
                                            publishingSessionId ===
                                            group.report_session_id
                                        }
                                        onClick={() =>
                                            group.report_session_id &&
                                            void handlePublishSession(
                                                group.report_session_id,
                                            )
                                        }
                                        className="w-fit rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {publishingSessionId ===
                                            group.report_session_id
                                            ? "Publishing..."
                                            : "Publish Approved Reports"}
                                    </button>
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

                                                    <p className="mt-1 text-sm text-slate-500">
                                                        Student{" "}
                                                        {report.student_id} ·
                                                        Teacher{" "}
                                                        {report.teacher_id ??
                                                            "Not assigned"}{" "}
                                                        ·{" "}
                                                        {report.academic_year}
                                                        {report.term
                                                            ? ` · ${report.term}`
                                                            : ""}
                                                    </p>

                                                    <p className="mt-1 text-xs text-slate-400">
                                                        Created{" "}
                                                        {formatDate(
                                                            report.created_at,
                                                        )}
                                                    </p>
                                                </div>

                                                <div className="flex flex-wrap gap-2">
                                                    <span
                                                        className={`w-fit rounded-full px-3 py-1 text-sm font-bold ${getStatusClassName(
                                                            report.status,
                                                        )}`}
                                                    >
                                                        {report.status}
                                                    </span>

                                                    <span
                                                        className={`w-fit rounded-full px-3 py-1 text-sm font-bold ${report.published
                                                            ? "bg-green-50 text-green-700"
                                                            : "bg-amber-50 text-amber-700"
                                                            }`}
                                                    >
                                                        {report.published
                                                            ? "Published"
                                                            : "Not Published"}
                                                    </span>
                                                </div>
                                            </div>

                                            <p className="mt-4 whitespace-pre-line rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                                                {report.report_text}
                                            </p>

                                            <div className="mt-4 flex flex-wrap gap-3 border-t pt-4">
                                                {report.status ===
                                                    REPORT_STATUS_SUBMITTED && (
                                                        <button
                                                            type="button"
                                                            disabled={
                                                                savingId ===
                                                                report.id
                                                            }
                                                            onClick={() =>
                                                                void updateReportStatus(
                                                                    report,
                                                                    REPORT_STATUS_APPROVED,
                                                                )
                                                            }
                                                            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                                                        >
                                                            Approve
                                                        </button>
                                                    )}

                                                {report.status !==
                                                    REPORT_STATUS_DRAFT &&
                                                    !report.published && (
                                                        <button
                                                            type="button"
                                                            disabled={
                                                                savingId ===
                                                                report.id
                                                            }
                                                            onClick={() =>
                                                                void updateReportStatus(
                                                                    report,
                                                                    REPORT_STATUS_DRAFT,
                                                                )
                                                            }
                                                            className="rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                                                        >
                                                            Return to Draft
                                                        </button>
                                                    )}

                                                {report.published ? (
                                                    <button
                                                        type="button"
                                                        disabled={
                                                            savingId ===
                                                            report.id
                                                        }
                                                        onClick={() =>
                                                            void unpublishReport(
                                                                report,
                                                            )
                                                        }
                                                        className="rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                                                    >
                                                        Unpublish
                                                    </button>
                                                ) : (
                                                    report.status ===
                                                    REPORT_STATUS_APPROVED && (
                                                        <button
                                                            type="button"
                                                            disabled={
                                                                savingId ===
                                                                report.id
                                                            }
                                                            onClick={() =>
                                                                void publishReport(
                                                                    report,
                                                                )
                                                            }
                                                            className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-60"
                                                        >
                                                            Publish
                                                        </button>
                                                    )
                                                )}

                                                <button
                                                    type="button"
                                                    disabled={
                                                        savingId === report.id
                                                    }
                                                    onClick={() =>
                                                        void handleDeleteReport(
                                                            report.id,
                                                        )
                                                    }
                                                    className="rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60"
                                                >
                                                    Delete
                                                </button>
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