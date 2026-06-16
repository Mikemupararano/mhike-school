"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
    createReportSession,
    deleteReportSession,
    listReportSessions,
    updateReportSession,
    type ReportSession,
    type ReportSessionCreateInput,
} from "@/lib/report-sessions";

type ReportSessionFormState = {
    title: string;
    academic_year: string;
    term: string;
    active: boolean;
    include_work_covered: boolean;
    include_student_comment: boolean;
    include_exam_mark: boolean;
    include_attainment_grade: boolean;
    include_effort_grade: boolean;
    include_target_grade: boolean;
    include_next_steps: boolean;
    include_tutor_comment: boolean;
};

const initialFormState: ReportSessionFormState = {
    title: "",
    academic_year: "2026/27",
    term: "",
    active: true,
    include_work_covered: true,
    include_student_comment: true,
    include_exam_mark: false,
    include_attainment_grade: false,
    include_effort_grade: false,
    include_target_grade: false,
    include_next_steps: false,
    include_tutor_comment: false,
};

const fieldLabels: Array<{
    key: keyof Pick<
        ReportSessionFormState,
        | "include_work_covered"
        | "include_student_comment"
        | "include_exam_mark"
        | "include_attainment_grade"
        | "include_effort_grade"
        | "include_target_grade"
        | "include_next_steps"
        | "include_tutor_comment"
    >;
    label: string;
    description: string;
}> = [
        {
            key: "include_work_covered",
            label: "Work Covered",
            description: "Whole-class summary entered once by the teacher.",
        },
        {
            key: "include_student_comment",
            label: "Student Comment",
            description: "Individual written comment for each student.",
        },
        {
            key: "include_exam_mark",
            label: "Exam Mark",
            description: "Assessment mark, percentage or score.",
        },
        {
            key: "include_attainment_grade",
            label: "Attainment Grade",
            description: "Current attainment or working grade.",
        },
        {
            key: "include_effort_grade",
            label: "Effort Grade",
            description: "Effort, attitude or learning behaviour grade.",
        },
        {
            key: "include_target_grade",
            label: "Target Grade",
            description: "Target or predicted grade.",
        },
        {
            key: "include_next_steps",
            label: "Next Steps",
            description: "Focused improvement target for the student.",
        },
        {
            key: "include_tutor_comment",
            label: "Tutor Comment",
            description: "Optional tutor-level comment.",
        },
    ];

function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function buildPayload(
    form: ReportSessionFormState,
): ReportSessionCreateInput {
    return {
        title: form.title.trim(),
        academic_year: form.academic_year.trim(),
        term: form.term.trim() || null,
        active: form.active,
        include_work_covered: form.include_work_covered,
        include_student_comment: form.include_student_comment,
        include_exam_mark: form.include_exam_mark,
        include_attainment_grade: form.include_attainment_grade,
        include_effort_grade: form.include_effort_grade,
        include_target_grade: form.include_target_grade,
        include_next_steps: form.include_next_steps,
        include_tutor_comment: form.include_tutor_comment,
    };
}

export default function SchoolAdminReportSessionsPage() {
    const [sessions, setSessions] = useState<ReportSession[]>([]);
    const [form, setForm] =
        useState<ReportSessionFormState>(initialFormState);
    const [editingSessionId, setEditingSessionId] = useState<number | null>(
        null,
    );
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    async function loadSessions() {
        try {
            setLoading(true);
            setError(null);

            const data = await listReportSessions();

            setSessions(data);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load report sessions.",
            );
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        void loadSessions();
    }, []);

    const sortedSessions = useMemo(
        () =>
            [...sessions].sort(
                (first, second) =>
                    Number(second.active) - Number(first.active) ||
                    new Date(second.created_at).getTime() -
                    new Date(first.created_at).getTime(),
            ),
        [sessions],
    );

    function updateTextField(
        field: "title" | "academic_year" | "term",
        value: string,
    ) {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));
    }

    function updateBooleanField(
        field: keyof ReportSessionFormState,
        value: boolean,
    ) {
        setForm((current) => ({
            ...current,
            [field]: value,
        }));
    }

    function resetForm() {
        setForm(initialFormState);
        setEditingSessionId(null);
        setError(null);
        setSuccessMessage(null);
    }

    function startEdit(session: ReportSession) {
        setEditingSessionId(session.id);
        setForm({
            title: session.title,
            academic_year: session.academic_year,
            term: session.term ?? "",
            active: session.active,
            include_work_covered: session.include_work_covered,
            include_student_comment: session.include_student_comment,
            include_exam_mark: session.include_exam_mark,
            include_attainment_grade: session.include_attainment_grade,
            include_effort_grade: session.include_effort_grade,
            include_target_grade: session.include_target_grade,
            include_next_steps: session.include_next_steps,
            include_tutor_comment: session.include_tutor_comment,
        });
        setError(null);
        setSuccessMessage(null);
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!form.title.trim()) {
            setError("Report session title is required.");
            return;
        }

        if (!form.academic_year.trim()) {
            setError("Academic year is required.");
            return;
        }

        const payload = buildPayload(form);

        try {
            setSaving(true);
            setError(null);
            setSuccessMessage(null);

            if (editingSessionId) {
                const updated = await updateReportSession(
                    editingSessionId,
                    payload,
                );

                setSessions((current) =>
                    current.map((session) =>
                        session.id === updated.id ? updated : session,
                    ),
                );

                setSuccessMessage("Report session updated.");
            } else {
                const created = await createReportSession(payload);

                setSessions((current) => [created, ...current]);

                setSuccessMessage("Report session created.");
            }

            resetForm();
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to save report session.",
            );
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete(sessionId: number) {
        const confirmed = window.confirm(
            "Delete this report session? This cannot be undone.",
        );

        if (!confirmed) {
            return;
        }

        try {
            setError(null);
            setSuccessMessage(null);

            await deleteReportSession(sessionId);

            setSessions((current) =>
                current.filter((session) => session.id !== sessionId),
            );

            if (editingSessionId === sessionId) {
                resetForm();
            }

            setSuccessMessage("Report session deleted.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to delete report session.",
            );
        }
    }

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Report Sessions
                </h1>

                <p className="mt-2 max-w-3xl text-slate-500">
                    Configure what teachers see when writing reports. Each
                    session controls the fields shown, such as work covered,
                    exam mark, attainment grade, effort grade and next steps.
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
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-950">
                            {editingSessionId
                                ? "Edit Report Session"
                                : "Create Report Session"}
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            School Admins control the report structure for each
                            reporting cycle.
                        </p>
                    </div>

                    {editingSessionId && (
                        <button
                            type="button"
                            onClick={resetForm}
                            className="w-fit rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                        >
                            Cancel Edit
                        </button>
                    )}
                </div>

                <form onSubmit={handleSubmit} className="mt-6 grid gap-5">
                    <div className="grid gap-4 md:grid-cols-3">
                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Session Title
                            </span>

                            <input
                                value={form.title}
                                onChange={(event) =>
                                    updateTextField(
                                        "title",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="Year 10 Autumn Reports"
                            />
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Academic Year
                            </span>

                            <input
                                value={form.academic_year}
                                onChange={(event) =>
                                    updateTextField(
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
                                    updateTextField("term", event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                                placeholder="Autumn"
                            />
                        </label>
                    </div>

                    <label className="flex items-start gap-3 rounded-2xl border bg-slate-50 p-4">
                        <input
                            type="checkbox"
                            checked={form.active}
                            onChange={(event) =>
                                updateBooleanField(
                                    "active",
                                    event.target.checked,
                                )
                            }
                            className="mt-1"
                        />

                        <span>
                            <span className="block text-sm font-bold text-slate-900">
                                Active session
                            </span>

                            <span className="block text-sm text-slate-500">
                                Active sessions appear first for teachers when
                                writing reports.
                            </span>
                        </span>
                    </label>

                    <div>
                        <h3 className="text-base font-bold text-slate-950">
                            Enabled Report Fields
                        </h3>

                        <p className="mt-1 text-sm text-slate-500">
                            Switch on only the fields required for this report
                            cycle.
                        </p>

                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {fieldLabels.map((field) => (
                                <label
                                    key={field.key}
                                    className="flex items-start gap-3 rounded-2xl border p-4 hover:bg-slate-50"
                                >
                                    <input
                                        type="checkbox"
                                        checked={Boolean(form[field.key])}
                                        onChange={(event) =>
                                            updateBooleanField(
                                                field.key,
                                                event.target.checked,
                                            )
                                        }
                                        className="mt-1"
                                    />

                                    <span>
                                        <span className="block text-sm font-bold text-slate-900">
                                            {field.label}
                                        </span>

                                        <span className="block text-sm text-slate-500">
                                            {field.description}
                                        </span>
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-3 border-t pt-5">
                        <button
                            type="submit"
                            disabled={saving}
                            className="rounded-xl bg-blue-600 px-5 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {saving
                                ? "Saving..."
                                : editingSessionId
                                    ? "Update Session"
                                    : "Create Session"}
                        </button>

                        <button
                            type="button"
                            onClick={resetForm}
                            className="rounded-xl border px-5 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                        >
                            Reset
                        </button>
                    </div>
                </form>
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <h2 className="text-xl font-bold text-slate-950">
                    Existing Report Sessions
                </h2>

                {loading ? (
                    <p className="mt-4 text-sm text-slate-500">
                        Loading report sessions...
                    </p>
                ) : sortedSessions.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                        No report sessions have been created yet.
                    </div>
                ) : (
                    <div className="mt-6 grid gap-4">
                        {sortedSessions.map((session) => (
                            <article
                                key={session.id}
                                className="rounded-2xl border bg-slate-50 p-5"
                            >
                                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-950">
                                            {session.title}
                                        </h3>

                                        <p className="mt-1 text-sm text-slate-500">
                                            {session.academic_year}
                                            {session.term
                                                ? ` · ${session.term}`
                                                : ""}{" "}
                                            · Created{" "}
                                            {formatDate(session.created_at)}
                                        </p>
                                    </div>

                                    <span
                                        className={`w-fit rounded-full px-3 py-1 text-sm font-bold ${session.active
                                            ? "bg-green-50 text-green-700"
                                            : "bg-slate-100 text-slate-600"
                                            }`}
                                    >
                                        {session.active
                                            ? "Active"
                                            : "Inactive"}
                                    </span>
                                </div>

                                <div className="mt-4 flex flex-wrap gap-2">
                                    {fieldLabels
                                        .filter((field) =>
                                            Boolean(session[field.key]),
                                        )
                                        .map((field) => (
                                            <span
                                                key={field.key}
                                                className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700"
                                            >
                                                {field.label}
                                            </span>
                                        ))}
                                </div>

                                <div className="mt-4 flex flex-wrap gap-3 border-t pt-4">
                                    <button
                                        type="button"
                                        onClick={() => startEdit(session)}
                                        className="rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-white"
                                    >
                                        Edit
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() =>
                                            void handleDelete(session.id)
                                        }
                                        className="rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
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