"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
    createStudentReport,
    deleteStudentReport,
    listStudentReports,
    type StudentReport,
    type StudentReportCreateInput,
} from "@/lib/services/studentReports";

type ReportFormState = {
    student_id: string;
    title: string;
    report_text: string;
    grade: string;
    academic_year: string;
    term: string;
};

const initialFormState: ReportFormState = {
    student_id: "",
    title: "",
    report_text: "",
    grade: "",
    academic_year: "2026/27",
    term: "",
};

function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

export default function TeacherReportsPage() {
    const [reports, setReports] = useState<StudentReport[]>([]);
    const [form, setForm] = useState<ReportFormState>(initialFormState);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
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

    const sortedReports = useMemo(() => {
        return [...reports].sort(
            (first, second) =>
                new Date(second.created_at).getTime() -
                new Date(first.created_at).getTime(),
        );
    }, [reports]);

    function updateFormField(
        field: keyof ReportFormState,
        value: string,
    ) {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));
    }

    async function handleCreateReport(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        const studentId = Number(form.student_id);

        if (!studentId || Number.isNaN(studentId)) {
            setError("Enter a valid student ID.");
            return;
        }

        if (!form.title.trim()) {
            setError("Report title is required.");
            return;
        }

        if (!form.report_text.trim()) {
            setError("Report text is required.");
            return;
        }

        if (!form.academic_year.trim()) {
            setError("Academic year is required.");
            return;
        }

        const payload: StudentReportCreateInput = {
            student_id: studentId,
            title: form.title.trim(),
            report_text: form.report_text.trim(),
            grade: form.grade.trim() || null,
            academic_year: form.academic_year.trim(),
            term: form.term.trim() || null,
        };

        try {
            setSaving(true);
            setError(null);
            setSuccessMessage(null);

            const created = await createStudentReport(payload);

            setReports((current) => [created, ...current]);
            setForm(initialFormState);
            setSuccessMessage("Report created successfully.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to create report.",
            );
        } finally {
            setSaving(false);
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
        }
    }

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Student Reports
                </h1>

                <p className="mt-2 text-slate-500">
                    Create and manage academic reports for students.
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
                <h2 className="text-xl font-bold text-slate-950">
                    Create Report
                </h2>

                <form onSubmit={handleCreateReport} className="mt-6 grid gap-4">
                    <div className="grid gap-4 md:grid-cols-3">
                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Student ID
                            </span>

                            <input
                                value={form.student_id}
                                onChange={(event) =>
                                    updateFormField(
                                        "student_id",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="e.g. 12"
                                inputMode="numeric"
                            />
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Academic Year
                            </span>

                            <input
                                value={form.academic_year}
                                onChange={(event) =>
                                    updateFormField(
                                        "academic_year",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="2026/27"
                            />
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Term
                            </span>

                            <input
                                value={form.term}
                                onChange={(event) =>
                                    updateFormField(
                                        "term",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="Autumn"
                            />
                        </label>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Title
                            </span>

                            <input
                                value={form.title}
                                onChange={(event) =>
                                    updateFormField(
                                        "title",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="Autumn Progress Report"
                            />
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Grade
                            </span>

                            <input
                                value={form.grade}
                                onChange={(event) =>
                                    updateFormField(
                                        "grade",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="A"
                            />
                        </label>
                    </div>

                    <label className="grid gap-2">
                        <span className="text-sm font-semibold text-slate-700">
                            Report Text
                        </span>

                        <textarea
                            value={form.report_text}
                            onChange={(event) =>
                                updateFormField(
                                    "report_text",
                                    event.target.value,
                                )
                            }
                            className="min-h-40 rounded-xl border px-3 py-2 text-sm"
                            placeholder="Write the report feedback..."
                        />
                    </label>

                    <button
                        type="submit"
                        disabled={saving}
                        className="w-fit rounded-xl bg-blue-600 px-5 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {saving ? "Creating..." : "Create Report"}
                    </button>
                </form>
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <h2 className="text-xl font-bold text-slate-950">
                    Existing Reports
                </h2>

                {loading ? (
                    <p className="mt-4 text-sm text-slate-500">
                        Loading reports...
                    </p>
                ) : sortedReports.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                        No reports have been created yet.
                    </div>
                ) : (
                    <div className="mt-6 grid gap-4">
                        {sortedReports.map((report) => (
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
                                            Student {report.student_id} ·{" "}
                                            {report.academic_year}
                                            {report.term
                                                ? ` · ${report.term}`
                                                : ""}
                                        </p>
                                    </div>

                                    {report.grade && (
                                        <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">
                                            {report.grade}
                                        </span>
                                    )}
                                </div>

                                <p className="mt-4 whitespace-pre-line text-sm leading-6 text-slate-700">
                                    {report.report_text}
                                </p>

                                <div className="mt-4 flex flex-col gap-3 border-t pt-4 text-sm text-slate-500 md:flex-row md:items-center md:justify-between">
                                    <span>
                                        Created {formatDate(report.created_at)}
                                    </span>

                                    <button
                                        type="button"
                                        onClick={() =>
                                            void handleDeleteReport(report.id)
                                        }
                                        className="w-fit font-semibold text-red-600 hover:text-red-700"
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