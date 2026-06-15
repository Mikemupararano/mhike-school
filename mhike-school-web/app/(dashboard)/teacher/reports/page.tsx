"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
    createStudentReport,
    deleteStudentReport,
    listStudentReports,
    type StudentReport,
    type StudentReportCreateInput,
} from "@/lib/services/studentReports";

type SaveAction = "draft" | "next" | "close";

type ReportFormState = {
    teacher_id: string;
    class_id: string;
    student_id: string;
    report_session_id: string;
    title: string;
    work_covered: string;
    report_text: string;
    exam_mark: string;
    attainment_grade: string;
    effort_grade: string;
    target_grade: string;
    next_steps: string;
    academic_year: string;
    term: string;
};

type ReportSessionConfig = {
    include_work_covered: boolean;
    include_exam_mark: boolean;
    include_attainment_grade: boolean;
    include_effort_grade: boolean;
    include_target_grade: boolean;
    include_next_steps: boolean;
};

const reportSessionConfig: ReportSessionConfig = {
    include_work_covered: true,
    include_exam_mark: true,
    include_attainment_grade: true,
    include_effort_grade: true,
    include_target_grade: true,
    include_next_steps: true,
};

const initialFormState: ReportFormState = {
    teacher_id: "",
    class_id: "",
    student_id: "",
    report_session_id: "",
    title: "",
    work_covered: "",
    report_text: "",
    exam_mark: "",
    attainment_grade: "",
    effort_grade: "",
    target_grade: "",
    next_steps: "",
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

function buildReportText(form: ReportFormState): string {
    const sections: string[] = [];

    if (form.work_covered.trim()) {
        sections.push(`Work covered:\n${form.work_covered.trim()}`);
    }

    if (form.report_text.trim()) {
        sections.push(`Student comment:\n${form.report_text.trim()}`);
    }

    if (form.next_steps.trim()) {
        sections.push(`Next steps:\n${form.next_steps.trim()}`);
    }

    return sections.join("\n\n");
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

    const sortedReports = useMemo(
        () =>
            [...reports].sort(
                (first, second) =>
                    new Date(second.created_at).getTime() -
                    new Date(first.created_at).getTime(),
            ),
        [reports],
    );

    function updateFormField(field: keyof ReportFormState, value: string) {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));
    }

    async function saveReport(action: SaveAction) {
        const studentId = Number(form.student_id);

        if (!studentId || Number.isNaN(studentId)) {
            setError("Select a valid student.");
            return;
        }

        if (!form.title.trim()) {
            setError("Report title is required.");
            return;
        }

        const reportText = buildReportText(form);

        if (!reportText.trim()) {
            setError("Report text is required.");
            return;
        }

        const payload: StudentReportCreateInput = {
            student_id: studentId,
            title: form.title.trim(),
            report_text: reportText,
            grade:
                form.attainment_grade.trim() ||
                form.exam_mark.trim() ||
                null,
            academic_year: form.academic_year.trim(),
            term: form.term.trim() || null,
        };

        try {
            setSaving(true);
            setError(null);
            setSuccessMessage(null);

            const created = await createStudentReport(payload);

            setReports((current) => [created, ...current]);

            if (action === "next") {
                setForm((current) => ({
                    ...current,
                    student_id: "",
                    report_text: "",
                    exam_mark: "",
                    attainment_grade: "",
                    effort_grade: "",
                    target_grade: "",
                    next_steps: "",
                }));

                setSuccessMessage("Draft saved. Select the next student.");
                return;
            }

            if (action === "close") {
                setForm(initialFormState);
                setSuccessMessage("Draft saved and closed.");
                return;
            }

            setSuccessMessage("Draft saved.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to save draft.",
            );
        } finally {
            setSaving(false);
        }
    }

    async function handleCreateReport(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        await saveReport("draft");
    }

    async function handleDeleteReport(reportId: number) {
        const confirmed = window.confirm(
            "Delete this report? This cannot be undone.",
        );

        if (!confirmed) return;

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
                    Write student draft reports, save, move to the next student,
                    or close when finished.
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
                    Write Draft Report
                </h2>

                <form onSubmit={handleCreateReport} className="mt-6 grid gap-5">
                    <div className="grid gap-4 md:grid-cols-3">
                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Teacher
                            </span>

                            <select
                                value={form.teacher_id}
                                onChange={(event) =>
                                    updateFormField(
                                        "teacher_id",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                            >
                                <option value="">
                                    Current teacher / staff member
                                </option>
                            </select>
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Class
                            </span>

                            <select
                                value={form.class_id}
                                onChange={(event) =>
                                    updateFormField(
                                        "class_id",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                            >
                                <option value="">
                                    Select class
                                </option>
                            </select>
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Student
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
                                placeholder="Temporary student ID until selector endpoint is connected"
                                inputMode="numeric"
                            />
                        </label>
                    </div>

                    <div className="grid gap-4 md:grid-cols-3">
                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Report Session
                            </span>

                            <select
                                value={form.report_session_id}
                                onChange={(event) =>
                                    updateFormField(
                                        "report_session_id",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                            >
                                <option value="">
                                    Default report session
                                </option>
                            </select>
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
                                    updateFormField("term", event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="Autumn"
                            />
                        </label>
                    </div>

                    <label className="grid gap-2">
                        <span className="text-sm font-semibold text-slate-700">
                            Report Title
                        </span>

                        <input
                            value={form.title}
                            onChange={(event) =>
                                updateFormField("title", event.target.value)
                            }
                            className="rounded-xl border px-3 py-2 text-sm"
                            placeholder="Autumn Progress Report"
                        />
                    </label>

                    {reportSessionConfig.include_work_covered && (
                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Work Covered
                            </span>

                            <textarea
                                value={form.work_covered}
                                onChange={(event) =>
                                    updateFormField(
                                        "work_covered",
                                        event.target.value,
                                    )
                                }
                                className="min-h-24 rounded-xl border px-3 py-2 text-sm"
                                placeholder="Write one or two lines about the work covered by the whole class."
                            />
                        </label>
                    )}

                    <label className="grid gap-2">
                        <span className="text-sm font-semibold text-slate-700">
                            Student Comment
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
                            placeholder="Write the individual student comment..."
                        />
                    </label>

                    <div className="grid gap-4 md:grid-cols-3">
                        {reportSessionConfig.include_exam_mark && (
                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Exam Mark
                                </span>

                                <input
                                    value={form.exam_mark}
                                    onChange={(event) =>
                                        updateFormField(
                                            "exam_mark",
                                            event.target.value,
                                        )
                                    }
                                    className="rounded-xl border px-3 py-2 text-sm"
                                    placeholder="e.g. 72%"
                                />
                            </label>
                        )}

                        {reportSessionConfig.include_attainment_grade && (
                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Attainment Grade
                                </span>

                                <input
                                    value={form.attainment_grade}
                                    onChange={(event) =>
                                        updateFormField(
                                            "attainment_grade",
                                            event.target.value,
                                        )
                                    }
                                    className="rounded-xl border px-3 py-2 text-sm"
                                    placeholder="e.g. A"
                                />
                            </label>
                        )}

                        {reportSessionConfig.include_effort_grade && (
                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Effort Grade
                                </span>

                                <input
                                    value={form.effort_grade}
                                    onChange={(event) =>
                                        updateFormField(
                                            "effort_grade",
                                            event.target.value,
                                        )
                                    }
                                    className="rounded-xl border px-3 py-2 text-sm"
                                    placeholder="e.g. Excellent"
                                />
                            </label>
                        )}
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                        {reportSessionConfig.include_target_grade && (
                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Target Grade
                                </span>

                                <input
                                    value={form.target_grade}
                                    onChange={(event) =>
                                        updateFormField(
                                            "target_grade",
                                            event.target.value,
                                        )
                                    }
                                    className="rounded-xl border px-3 py-2 text-sm"
                                    placeholder="e.g. A*"
                                />
                            </label>
                        )}

                        {reportSessionConfig.include_next_steps && (
                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Next Steps
                                </span>

                                <input
                                    value={form.next_steps}
                                    onChange={(event) =>
                                        updateFormField(
                                            "next_steps",
                                            event.target.value,
                                        )
                                    }
                                    className="rounded-xl border px-3 py-2 text-sm"
                                    placeholder="What should the student focus on next?"
                                />
                            </label>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-3 border-t pt-5">
                        <button
                            type="submit"
                            disabled={saving}
                            className="rounded-xl bg-blue-600 px-5 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {saving ? "Saving..." : "Save Draft"}
                        </button>

                        <button
                            type="button"
                            disabled={saving}
                            onClick={() => void saveReport("next")}
                            className="rounded-xl bg-slate-900 px-5 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            Save & Next Student
                        </button>

                        <button
                            type="button"
                            disabled={saving}
                            onClick={() => void saveReport("close")}
                            className="rounded-xl border px-5 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            Save & Close
                        </button>
                    </div>
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

                                    <span
                                        className={`rounded-full px-3 py-1 text-sm font-bold ${report.published
                                                ? "bg-green-50 text-green-700"
                                                : "bg-amber-50 text-amber-700"
                                            }`}
                                    >
                                        {report.published
                                            ? "Published"
                                            : "Draft"}
                                    </span>
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