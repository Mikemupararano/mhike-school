"use client";

import {
    ArrowLeft,
    FileText,
    Loader2,
    RotateCcw,
    Save,
    TriangleAlert,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import {
    type FormEvent,
    useCallback,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";

import RoleGate from "@/components/auth/RoleGate";
import {
    getStudentReport,
    updateStudentReport,
    type StudentReport,
} from "@/lib/services/studentReports";
import { UserRole } from "@/types/user";

type FormState = {
    title: string;
    report_text: string;
    grade: string;
    academic_year: string;
    term: string;
};

const EMPTY_FORM: FormState = {
    title: "",
    report_text: "",
    grade: "",
    academic_year: "",
    term: "",
};

function normaliseForm(report: StudentReport): FormState {
    return {
        title: report.title ?? "",
        report_text: report.report_text ?? "",
        grade: report.grade ?? "",
        academic_year: report.academic_year ?? "",
        term: report.term ?? "",
    };
}

function hasFormChanged(
    current: FormState,
    original: FormState,
): boolean {
    return (
        current.title !== original.title ||
        current.report_text !== original.report_text ||
        current.grade !== original.grade ||
        current.academic_year !== original.academic_year ||
        current.term !== original.term
    );
}

export default function TeacherReportEditPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherReportEditContent />
        </RoleGate>
    );
}

function TeacherReportEditContent() {
    const router = useRouter();
    const params = useParams<{ reportId?: string | string[] }>();

    const rawReportId = Array.isArray(params.reportId)
        ? params.reportId[0]
        : params.reportId;

    const reportId = Number(rawReportId);
    const hasValidReportId =
        Number.isInteger(reportId) && reportId > 0;

    const [report, setReport] = useState<StudentReport | null>(null);
    const [form, setForm] = useState<FormState>(EMPTY_FORM);
    const [originalForm, setOriginalForm] =
        useState<FormState>(EMPTY_FORM);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] =
        useState<string | null>(null);

    const isDirty = useMemo(
        () => hasFormChanged(form, originalForm),
        [form, originalForm],
    );

    const reportCharacterCount = form.report_text.length;

    const loadReport = useCallback(async () => {
        if (!hasValidReportId) {
            setLoading(false);
            setError("The report ID is invalid.");
            return;
        }

        try {
            setLoading(true);
            setError(null);
            setSuccessMessage(null);

            const data = await getStudentReport(reportId);
            const nextForm = normaliseForm(data);

            setReport(data);
            setForm(nextForm);
            setOriginalForm(nextForm);
        } catch (err) {
            setReport(null);
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load report.",
            );
        } finally {
            setLoading(false);
        }
    }, [hasValidReportId, reportId]);

    useEffect(() => {
        void loadReport();
    }, [loadReport]);

    useEffect(() => {
        function warnBeforeUnload(event: BeforeUnloadEvent) {
            if (!isDirty || saving) {
                return;
            }

            event.preventDefault();
        }

        window.addEventListener("beforeunload", warnBeforeUnload);

        return () => {
            window.removeEventListener(
                "beforeunload",
                warnBeforeUnload,
            );
        };
    }, [isDirty, saving]);

    function updateField(field: keyof FormState, value: string) {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));
        setSuccessMessage(null);
    }

    function handleReset() {
        setForm(originalForm);
        setError(null);
        setSuccessMessage(null);
    }

    function handleCancel() {
        if (
            isDirty &&
            !window.confirm(
                "You have unsaved changes. Leave this page without saving?",
            )
        ) {
            return;
        }

        router.push("/teacher/reports");
    }

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        if (!hasValidReportId || saving) {
            return;
        }

        const title = form.title.trim();
        const reportText = form.report_text.trim();
        const academicYear = form.academic_year.trim();
        const grade = form.grade.trim();
        const term = form.term.trim();

        if (!title) {
            setError("Enter a report title.");
            return;
        }

        if (!reportText) {
            setError("Enter the report text.");
            return;
        }

        if (!academicYear) {
            setError("Enter the academic year.");
            return;
        }

        try {
            setSaving(true);
            setError(null);
            setSuccessMessage(null);

            const updated = await updateStudentReport(reportId, {
                title,
                report_text: reportText,
                grade: grade || null,
                academic_year: academicYear,
                term: term || null,
            });

            const nextForm = normaliseForm(updated);

            setReport(updated);
            setForm(nextForm);
            setOriginalForm(nextForm);
            setSuccessMessage("Report changes saved successfully.");
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
        return <ReportEditLoadingState />;
    }

    if (!report) {
        return (
            <main className="min-h-full bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
                <div className="mx-auto max-w-3xl">
                    <section
                        role="alert"
                        className="rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm"
                    >
                        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-700">
                            <TriangleAlert
                                aria-hidden="true"
                                className="h-6 w-6"
                            />
                        </div>

                        <h1 className="mt-4 text-2xl font-extrabold text-slate-950">
                            Report unavailable
                        </h1>

                        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">
                            {error ??
                                "The requested report could not be found."}
                        </p>

                        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
                            {hasValidReportId && (
                                <button
                                    type="button"
                                    onClick={() => void loadReport()}
                                    data-custom-button="true"
                                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-blue-800"
                                >
                                    <RotateCcw
                                        aria-hidden="true"
                                        className="h-4 w-4"
                                    />
                                    Retry
                                </button>
                            )}

                            <button
                                type="button"
                                onClick={() =>
                                    router.push("/teacher/reports")
                                }
                                data-custom-button="true"
                                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                            >
                                <ArrowLeft
                                    aria-hidden="true"
                                    className="h-4 w-4"
                                />
                                Back to reports
                            </button>
                        </div>
                    </section>
                </div>
            </main>
        );
    }

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-5xl">
                <header className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <button
                            type="button"
                            onClick={handleCancel}
                            data-custom-button="true"
                            className="inline-flex items-center gap-2 rounded-lg px-2 py-1 text-sm font-bold text-slate-600 transition hover:bg-slate-100 hover:text-slate-950"
                        >
                            <ArrowLeft
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            Back to reports
                        </button>

                        <div className="mt-4 flex items-start gap-4">
                            <div className="hidden rounded-2xl bg-blue-100 p-3 text-blue-700 sm:block">
                                <FileText
                                    aria-hidden="true"
                                    className="h-7 w-7"
                                />
                            </div>

                            <div>
                                <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">
                                    Teacher reports
                                </p>
                                <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                                    Edit Report
                                </h1>
                                <p className="mt-2 max-w-2xl text-base text-slate-600">
                                    Review and update the report details
                                    before submitting it for the next
                                    workflow stage.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                        <span
                            className={`h-2.5 w-2.5 rounded-full ${isDirty ? "bg-amber-500" : "bg-green-500"
                                }`}
                            aria-hidden="true"
                        />
                        <span className="text-sm font-bold text-slate-700">
                            {isDirty
                                ? "Unsaved changes"
                                : "All changes saved"}
                        </span>
                    </div>
                </header>

                <div className="sr-only" aria-live="polite" role="status">
                    {saving ? "Saving report." : successMessage ?? ""}
                </div>

                {error && (
                    <div
                        role="alert"
                        className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800"
                    >
                        {error}
                    </div>
                )}

                {successMessage && (
                    <div
                        role="status"
                        className="mt-6 rounded-2xl border border-green-200 bg-green-50 p-4 text-sm font-semibold text-green-800"
                    >
                        {successMessage}
                    </div>
                )}

                <form
                    onSubmit={handleSubmit}
                    className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
                >
                    <section className="border-b border-slate-200 p-5 sm:p-6">
                        <div>
                            <h2 className="text-xl font-bold text-slate-950">
                                Report details
                            </h2>
                            <p className="mt-1 text-sm text-slate-500">
                                Fields marked with an asterisk are required.
                            </p>
                        </div>

                        <div className="mt-6 grid gap-5 md:grid-cols-2">
                            <FormField
                                label="Title"
                                htmlFor="report-title"
                                required
                            >
                                <input
                                    id="report-title"
                                    value={form.title}
                                    onChange={(event) =>
                                        updateField("title", event.target.value)
                                    }
                                    required
                                    maxLength={200}
                                    autoComplete="off"
                                    className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                />
                            </FormField>

                            <FormField
                                label="Grade"
                                htmlFor="report-grade"
                                hint="Optional"
                            >
                                <input
                                    id="report-grade"
                                    value={form.grade}
                                    onChange={(event) =>
                                        updateField("grade", event.target.value)
                                    }
                                    maxLength={50}
                                    autoComplete="off"
                                    placeholder="For example: A, 7, Secure"
                                    className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                />
                            </FormField>

                            <FormField
                                label="Academic year"
                                htmlFor="academic-year"
                                required
                            >
                                <input
                                    id="academic-year"
                                    value={form.academic_year}
                                    onChange={(event) =>
                                        updateField(
                                            "academic_year",
                                            event.target.value,
                                        )
                                    }
                                    required
                                    maxLength={20}
                                    autoComplete="off"
                                    placeholder="For example: 2026/27"
                                    className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                />
                            </FormField>

                            <FormField
                                label="Term"
                                htmlFor="report-term"
                                hint="Optional"
                            >
                                <input
                                    id="report-term"
                                    value={form.term}
                                    onChange={(event) =>
                                        updateField("term", event.target.value)
                                    }
                                    maxLength={50}
                                    autoComplete="off"
                                    placeholder="For example: Autumn"
                                    className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                />
                            </FormField>
                        </div>
                    </section>

                    <section className="p-5 sm:p-6">
                        <FormField
                            label="Report text"
                            htmlFor="report-text"
                            required
                            hint={`${reportCharacterCount.toLocaleString(
                                "en-GB",
                            )} characters`}
                        >
                            <textarea
                                id="report-text"
                                value={form.report_text}
                                onChange={(event) =>
                                    updateField(
                                        "report_text",
                                        event.target.value,
                                    )
                                }
                                required
                                rows={14}
                                className="min-h-72 w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 text-base leading-7 text-slate-950 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                            />
                        </FormField>
                    </section>

                    <footer className="sticky bottom-0 flex flex-col-reverse gap-3 border-t border-slate-200 bg-white/95 p-5 backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:p-6">
                        <div className="flex flex-col-reverse gap-3 sm:flex-row">
                            <button
                                type="button"
                                onClick={handleCancel}
                                disabled={saving}
                                data-custom-button="true"
                                className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                Cancel
                            </button>

                            <button
                                type="button"
                                onClick={handleReset}
                                disabled={saving || !isDirty}
                                data-custom-button="true"
                                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <RotateCcw
                                    aria-hidden="true"
                                    className="h-4 w-4"
                                />
                                Reset changes
                            </button>
                        </div>

                        <button
                            type="submit"
                            disabled={saving || !isDirty}
                            data-custom-button="true"
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {saving ? (
                                <Loader2
                                    aria-hidden="true"
                                    className="h-4 w-4 animate-spin"
                                />
                            ) : (
                                <Save
                                    aria-hidden="true"
                                    className="h-4 w-4"
                                />
                            )}
                            {saving ? "Saving..." : "Save changes"}
                        </button>
                    </footer>
                </form>
            </div>
        </main>
    );
}

function FormField({
    label,
    htmlFor,
    required = false,
    hint,
    children,
}: {
    label: string;
    htmlFor: string;
    required?: boolean;
    hint?: string;
    children: ReactNode;
}) {
    return (
        <label htmlFor={htmlFor} className="grid gap-2">
            <span className="flex items-center justify-between gap-3">
                <span className="text-sm font-bold text-slate-800">
                    {label}
                    {required && (
                        <span
                            className="ml-1 text-red-600"
                            aria-hidden="true"
                        >
                            *
                        </span>
                    )}
                </span>

                {hint && (
                    <span className="text-xs font-medium text-slate-500">
                        {hint}
                    </span>
                )}
            </span>

            {children}
        </label>
    );
}

function ReportEditLoadingState() {
    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-5xl" aria-hidden="true">
                <div className="h-8 w-36 animate-pulse rounded-lg bg-slate-200" />
                <div className="mt-5 h-28 animate-pulse rounded-2xl bg-slate-200" />

                <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
                    <div className="space-y-5 border-b border-slate-200 p-6">
                        <div className="h-7 w-48 animate-pulse rounded bg-slate-200" />

                        <div className="grid gap-5 md:grid-cols-2">
                            {Array.from({ length: 4 }).map((_, index) => (
                                <div key={index} className="space-y-2">
                                    <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
                                    <div className="h-11 animate-pulse rounded-xl bg-slate-200" />
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-2 p-6">
                        <div className="h-4 w-28 animate-pulse rounded bg-slate-200" />
                        <div className="h-80 animate-pulse rounded-xl bg-slate-200" />
                    </div>
                </div>
            </div>
        </main>
    );
}
