"use client";

import { useRouter, useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import {
    getStudentReport,
    updateStudentReport,
    type StudentReport,
} from "@/lib/services/studentReports";

type FormState = {
    title: string;
    report_text: string;
    grade: string;
    academic_year: string;
    term: string;
};

export default function TeacherReportEditPage() {
    const router = useRouter();
    const params = useParams();

    const reportId = Number(params.reportId);

    const [report, setReport] =
        useState<StudentReport | null>(null);

    const [form, setForm] = useState<FormState>({
        title: "",
        report_text: "",
        grade: "",
        academic_year: "",
        term: "",
    });

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadReport() {
            try {
                setLoading(true);
                setError(null);

                const data =
                    await getStudentReport(reportId);

                setReport(data);

                setForm({
                    title: data.title,
                    report_text: data.report_text,
                    grade: data.grade ?? "",
                    academic_year: data.academic_year,
                    term: data.term ?? "",
                });
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load report.",
                );
            } finally {
                setLoading(false);
            }
        }

        if (!Number.isNaN(reportId)) {
            void loadReport();
        }
    }, [reportId]);

    function updateField(
        field: keyof FormState,
        value: string,
    ) {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));
    }

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        try {
            setSaving(true);
            setError(null);

            await updateStudentReport(reportId, {
                title: form.title,
                report_text: form.report_text,
                grade: form.grade || null,
                academic_year: form.academic_year,
                term: form.term || null,
            });

            router.push("/teacher/reports");
            router.refresh();
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to update report.",
            );
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return (
            <main className="p-8">
                <p className="text-slate-500">
                    Loading report...
                </p>
            </main>
        );
    }

    if (!report) {
        return (
            <main className="p-8">
                <p className="text-red-600">
                    Report not found.
                </p>
            </main>
        );
    }

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Edit Report
                </h1>

                <p className="mt-2 text-slate-500">
                    Update the report details below.
                </p>
            </div>

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                    {error}
                </div>
            )}

            <form
                onSubmit={handleSubmit}
                className="space-y-6 rounded-2xl border bg-white p-6"
            >
                <div className="grid gap-4 md:grid-cols-2">
                    <label className="grid gap-2">
                        <span className="text-sm font-semibold">
                            Title
                        </span>

                        <input
                            value={form.title}
                            onChange={(event) =>
                                updateField(
                                    "title",
                                    event.target.value,
                                )
                            }
                            className="rounded-xl border px-3 py-2"
                        />
                    </label>

                    <label className="grid gap-2">
                        <span className="text-sm font-semibold">
                            Grade
                        </span>

                        <input
                            value={form.grade}
                            onChange={(event) =>
                                updateField(
                                    "grade",
                                    event.target.value,
                                )
                            }
                            className="rounded-xl border px-3 py-2"
                        />
                    </label>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                    <label className="grid gap-2">
                        <span className="text-sm font-semibold">
                            Academic Year
                        </span>

                        <input
                            value={form.academic_year}
                            onChange={(event) =>
                                updateField(
                                    "academic_year",
                                    event.target.value,
                                )
                            }
                            className="rounded-xl border px-3 py-2"
                        />
                    </label>

                    <label className="grid gap-2">
                        <span className="text-sm font-semibold">
                            Term
                        </span>

                        <input
                            value={form.term}
                            onChange={(event) =>
                                updateField(
                                    "term",
                                    event.target.value,
                                )
                            }
                            className="rounded-xl border px-3 py-2"
                        />
                    </label>
                </div>

                <label className="grid gap-2">
                    <span className="text-sm font-semibold">
                        Report Text
                    </span>

                    <textarea
                        value={form.report_text}
                        onChange={(event) =>
                            updateField(
                                "report_text",
                                event.target.value,
                            )
                        }
                        className="min-h-48 rounded-xl border px-3 py-2"
                    />
                </label>

                <div className="flex gap-3">
                    <button
                        type="submit"
                        disabled={saving}
                        className="rounded-xl bg-blue-600 px-5 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                    >
                        {saving
                            ? "Saving..."
                            : "Save Changes"}
                    </button>

                    <button
                        type="button"
                        onClick={() =>
                            router.push(
                                "/teacher/reports",
                            )
                        }
                        className="rounded-xl border px-5 py-2 font-semibold"
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </main>
    );
}