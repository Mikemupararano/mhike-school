"use client";

import { useEffect, useMemo, useState } from "react";

import {
    deleteStudentReport,
    listStudentReports,
    updateStudentReport,
    type StudentReport,
} from "@/lib/services/studentReports";

type StatusFilter = "all" | "draft" | "published";

function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

export default function SchoolAdminReportsPage() {
    const [reports, setReports] = useState<StudentReport[]>([]);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("draft");
    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState<number | null>(null);
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

    async function handleDeleteReport(reportId: number) {
        const confirmed = window.confirm(
            "Delete this report? This cannot be undone.",
        );

        if (!confirmed) return;

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
                    Review teacher draft reports and publish them for parent
                    access. Teachers can save drafts, but only School Admins
                    should publish reports.
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

            <section className="rounded-2xl border bg-white p-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-950">
                            Reports
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
                ) : filteredReports.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                        No reports found for this filter.
                    </div>
                ) : (
                    <div className="mt-6 grid gap-4">
                        {filteredReports.map((report) => (
                            <article
                                key={report.id}
                                className="rounded-2xl border bg-slate-50 p-5"
                            >
                                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-950">
                                            {report.title}
                                        </h3>

                                        <p className="mt-1 text-sm text-slate-500">
                                            Student {report.student_id} · Teacher{" "}
                                            {report.teacher_id ?? "Not assigned"} ·{" "}
                                            {report.academic_year}
                                            {report.term ? ` · ${report.term}` : ""}
                                        </p>

                                        <p className="mt-1 text-xs text-slate-400">
                                            Created {formatDate(report.created_at)}
                                        </p>
                                    </div>

                                    <span
                                        className={`w-fit rounded-full px-3 py-1 text-sm font-bold ${report.published
                                            ? "bg-green-50 text-green-700"
                                            : "bg-amber-50 text-amber-700"
                                            }`}
                                    >
                                        {report.published ? "Published" : "Draft"}
                                    </span>
                                </div>

                                <p className="mt-4 whitespace-pre-line rounded-xl bg-white p-4 text-sm leading-6 text-slate-700">
                                    {report.report_text}
                                </p>

                                <div className="mt-4 flex flex-wrap gap-3 border-t pt-4">
                                    {report.published ? (
                                        <button
                                            type="button"
                                            disabled={savingId === report.id}
                                            onClick={() =>
                                                void unpublishReport(report)
                                            }
                                            className="rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-white disabled:opacity-60"
                                        >
                                            Return to Draft
                                        </button>
                                    ) : (
                                        <button
                                            type="button"
                                            disabled={savingId === report.id}
                                            onClick={() =>
                                                void publishReport(report)
                                            }
                                            className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-60"
                                        >
                                            Publish
                                        </button>
                                    )}

                                    <button
                                        type="button"
                                        disabled={savingId === report.id}
                                        onClick={() =>
                                            void handleDeleteReport(report.id)
                                        }
                                        className="rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </section>
        </main>
    );
}