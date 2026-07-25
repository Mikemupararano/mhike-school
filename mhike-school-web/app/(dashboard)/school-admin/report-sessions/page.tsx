"use client";

import {
    FormEvent,
    useEffect,
    useMemo,
    useState,
} from "react";
import { useRouter } from "next/navigation";

import {
    createReportSession,
    deleteReportSession,
    exportReportSessionZip,
    listReportSessions,
    updateReportSession,
    type ReportSession,
    type ReportSessionCreateInput,
} from "@/lib/report-sessions";

type ReportingMode = "grade_card" | "full_report" | "both";

type YearGroup =
    | "Year 7"
    | "Year 8"
    | "Year 9"
    | "Year 10"
    | "Year 11"
    | "Year 12"
    | "Year 13"
    | "Custom";

type ReportFieldKey =
    | "include_work_covered"
    | "include_student_comment"
    | "include_exam_mark"
    | "include_attainment_grade"
    | "include_effort_grade"
    | "include_target_grade"
    | "include_next_steps"
    | "include_tutor_comment";

type ReportSessionFormState = {
    session_name: string;
    academic_year: string;
    year_group: YearGroup;
    custom_year_group: string;
    reporting_period: string;
    active: boolean;

    include_work_covered: boolean;
    include_student_comment: boolean;
    include_exam_mark: boolean;
    include_attainment_grade: boolean;
    include_effort_grade: boolean;
    include_target_grade: boolean;
    include_next_steps: boolean;
    include_tutor_comment: boolean;

    reporting_mode: ReportingMode;
    display_order: number;
    enable_report_generation: boolean;
    allow_teacher_edit_after_submission: boolean;
    allow_smt_edit_after_approval: boolean;
    show_previous_grades: boolean;
    show_previous_tutor_comments: boolean;
    show_progress_journey: boolean;
};

type SessionWithOptionalConfiguration = ReportSession & {
    checkpoint_name?: string | null;
    display_order?: number;
    reporting_mode?: ReportingMode;
    enable_report_generation?: boolean;
    allow_teacher_edit_after_submission?: boolean;
    allow_smt_edit_after_approval?: boolean;
    show_previous_grades?: boolean;
    show_previous_tutor_comments?: boolean;
    show_progress_journey?: boolean;
    copied_from_session_id?: number | null;
};

type SessionCreatePayload = ReportSessionCreateInput & {
    checkpoint_name?: string | null;
    display_order?: number;
    reporting_mode?: ReportingMode;
    enable_report_generation?: boolean;
    require_student_comment?: boolean;
    require_exam_mark?: boolean;
    require_attainment_grade?: boolean;
    require_effort_grade?: boolean;
    require_target_grade?: boolean;
    require_next_steps?: boolean;
    require_tutor_comment?: boolean;
    allow_teacher_edit_after_submission?: boolean;
    allow_smt_edit_after_approval?: boolean;
    show_previous_grades?: boolean;
    show_previous_tutor_comments?: boolean;
    show_progress_journey?: boolean;
    copied_from_session_id?: number | null;
};

const YEAR_GROUP_OPTIONS: YearGroup[] = [
    "Year 7",
    "Year 8",
    "Year 9",
    "Year 10",
    "Year 11",
    "Year 12",
    "Year 13",
    "Custom",
];

const REPORTING_PERIOD_OPTIONS = [
    "Autumn",
    "Spring",
    "Summer",
    "Autumn 1",
    "Autumn 2",
    "Spring 1",
    "Spring 2",
    "Summer 1",
    "Summer 2",
    "Progress Check",
    "End-of-Year Report",
    "Custom",
] as const;

const initialFormState: ReportSessionFormState = {
    session_name: "Reports",
    academic_year: "2026/27",
    year_group: "Year 10",
    custom_year_group: "",
    reporting_period: "Autumn",
    active: true,

    include_work_covered: true,
    include_student_comment: true,
    include_exam_mark: false,
    include_attainment_grade: true,
    include_effort_grade: true,
    include_target_grade: true,
    include_next_steps: false,
    include_tutor_comment: false,

    reporting_mode: "full_report",
    display_order: 1,
    enable_report_generation: true,
    allow_teacher_edit_after_submission: false,
    allow_smt_edit_after_approval: true,
    show_previous_grades: false,
    show_previous_tutor_comments: false,
    show_progress_journey: false,
};

const fieldLabels: Array<{
    key: ReportFieldKey;
    label: string;
    description: string;
}> = [
        {
            key: "include_work_covered",
            label: "Work Covered",
            description:
                "A shared whole-class summary that teachers can save once for the class.",
        },
        {
            key: "include_student_comment",
            label: "Student Comment",
            description:
                "An individual written or generated comment for each student.",
        },
        {
            key: "include_effort_grade",
            label: "Effort Grade",
            description:
                "The student's effort, attitude or learning-behaviour grade.",
        },
        {
            key: "include_attainment_grade",
            label: "Attainment Grade",
            description:
                "The student's current attainment or working grade.",
        },
        {
            key: "include_target_grade",
            label: "Target Grade",
            description:
                "The student's target, predicted or aspirational grade.",
        },
        {
            key: "include_exam_mark",
            label: "Exam Mark",
            description:
                "An assessment mark, percentage or numerical score.",
        },
        {
            key: "include_next_steps",
            label: "Next Steps",
            description:
                "A focused improvement target for the next reporting period.",
        },
        {
            key: "include_tutor_comment",
            label: "Tutor Comment",
            description:
                "An optional pastoral or tutor-level comment.",
        },
    ];

function formatDate(value: string): string {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Unknown date";
    }

    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function resolveYearGroupLabel(
    form: Pick<
        ReportSessionFormState,
        "year_group" | "custom_year_group"
    >,
): string {
    if (form.year_group === "Custom") {
        return form.custom_year_group.trim();
    }

    return form.year_group;
}

function buildGeneratedTitle(
    form: Pick<
        ReportSessionFormState,
        | "session_name"
        | "year_group"
        | "custom_year_group"
        | "reporting_period"
    >,
): string {
    const yearGroup = resolveYearGroupLabel(form);
    const period = form.reporting_period.trim();
    const sessionName = form.session_name.trim();

    return [yearGroup, period, sessionName]
        .filter((value) => value.length > 0)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();
}

function inferYearGroupFromTitle(
    title: string,
): {
    yearGroup: YearGroup;
    customYearGroup: string;
} {
    const standardYearGroup = YEAR_GROUP_OPTIONS.find(
        (option) =>
            option !== "Custom" &&
            title.toLowerCase().startsWith(option.toLowerCase()),
    );

    if (standardYearGroup && standardYearGroup !== "Custom") {
        return {
            yearGroup: standardYearGroup,
            customYearGroup: "",
        };
    }

    return {
        yearGroup: "Custom",
        customYearGroup: "",
    };
}

function inferSessionName(
    title: string,
    yearGroupLabel: string,
    reportingPeriod: string,
): string {
    let remaining = title.trim();

    if (
        yearGroupLabel &&
        remaining.toLowerCase().startsWith(yearGroupLabel.toLowerCase())
    ) {
        remaining = remaining.slice(yearGroupLabel.length).trim();
    }

    if (
        reportingPeriod &&
        remaining.toLowerCase().startsWith(reportingPeriod.toLowerCase())
    ) {
        remaining = remaining.slice(reportingPeriod.length).trim();
    }

    return remaining || "Reports";
}

function normaliseReportingPeriod(
    session: SessionWithOptionalConfiguration,
): string {
    return (
        session.checkpoint_name?.trim() ||
        session.term?.trim() ||
        "Reporting Period"
    );
}

function buildPayload(
    form: ReportSessionFormState,
    copiedFromSessionId?: number | null,
): SessionCreatePayload {
    const title = buildGeneratedTitle(form);
    const checkpointName = form.reporting_period.trim();

    return {
        title,
        academic_year: form.academic_year.trim(),
        term: checkpointName || null,
        checkpoint_name: checkpointName || null,
        active: form.active,

        include_work_covered: form.include_work_covered,
        include_student_comment: form.include_student_comment,
        include_exam_mark: form.include_exam_mark,
        include_attainment_grade: form.include_attainment_grade,
        include_effort_grade: form.include_effort_grade,
        include_target_grade: form.include_target_grade,
        include_next_steps: form.include_next_steps,
        include_tutor_comment: form.include_tutor_comment,

        require_student_comment: form.include_student_comment,
        require_exam_mark: false,
        require_attainment_grade: form.include_attainment_grade,
        require_effort_grade: form.include_effort_grade,
        require_target_grade: form.include_target_grade,
        require_next_steps: false,
        require_tutor_comment: false,

        reporting_mode: form.reporting_mode,
        display_order: Math.max(1, form.display_order),
        enable_report_generation: form.enable_report_generation,
        allow_teacher_edit_after_submission:
            form.allow_teacher_edit_after_submission,
        allow_smt_edit_after_approval:
            form.allow_smt_edit_after_approval,
        show_previous_grades: form.show_previous_grades,
        show_previous_tutor_comments:
            form.show_previous_tutor_comments,
        show_progress_journey: form.show_progress_journey,
        copied_from_session_id: copiedFromSessionId ?? null,
    };
}

function buildFormFromSession(
    session: SessionWithOptionalConfiguration,
): ReportSessionFormState {
    const reportingPeriod = normaliseReportingPeriod(session);
    const inferred = inferYearGroupFromTitle(session.title);

    const yearGroupLabel =
        inferred.yearGroup === "Custom"
            ? inferred.customYearGroup
            : inferred.yearGroup;

    return {
        session_name: inferSessionName(
            session.title,
            yearGroupLabel,
            reportingPeriod,
        ),
        academic_year: session.academic_year,
        year_group: inferred.yearGroup,
        custom_year_group: inferred.customYearGroup,
        reporting_period: reportingPeriod,
        active: session.active,

        include_work_covered: session.include_work_covered,
        include_student_comment: session.include_student_comment,
        include_exam_mark: session.include_exam_mark,
        include_attainment_grade: session.include_attainment_grade,
        include_effort_grade: session.include_effort_grade,
        include_target_grade: session.include_target_grade,
        include_next_steps: session.include_next_steps,
        include_tutor_comment: session.include_tutor_comment,

        reporting_mode: session.reporting_mode ?? "full_report",
        display_order: session.display_order ?? 1,
        enable_report_generation:
            session.enable_report_generation ?? true,
        allow_teacher_edit_after_submission:
            session.allow_teacher_edit_after_submission ?? false,
        allow_smt_edit_after_approval:
            session.allow_smt_edit_after_approval ?? true,
        show_previous_grades:
            session.show_previous_grades ?? false,
        show_previous_tutor_comments:
            session.show_previous_tutor_comments ?? false,
        show_progress_journey:
            session.show_progress_journey ?? false,
    };
}

function getAcademicYearSortValue(academicYear: string): number {
    const match = academicYear.match(/\d{4}/);

    if (!match) {
        return 0;
    }

    return Number(match[0]);
}

function createSafeFileName(title: string): string {
    return (
        title
            .trim()
            .replace(/[^a-zA-Z0-9-_]+/g, "-")
            .replace(/^-+|-+$/g, "")
            .toLowerCase() || "report-session"
    );
}
type ReportSessionWithStatistics = SessionWithOptionalConfiguration & {
    draft_count?: number;
    submitted_count?: number;
    tutor_review_count?: number;
    ready_for_smt_count?: number;
    approved_count?: number;
    published_count?: number;
    total_reports?: number;
};

export default function SchoolAdminReportSessionsPage() {
    const router = useRouter();

    const [sessions, setSessions] = useState<
        ReportSessionWithStatistics[]
    >([]);
    const [form, setForm] =
        useState<ReportSessionFormState>(initialFormState);

    const [editingSessionId, setEditingSessionId] = useState<
        number | null
    >(null);
    const [duplicatingSessionId, setDuplicatingSessionId] = useState<
        number | null
    >(null);
    const [exportingSessionId, setExportingSessionId] = useState<
        number | null
    >(null);
    const [deletingSessionId, setDeletingSessionId] = useState<
        number | null
    >(null);
    const [activatingSessionId, setActivatingSessionId] = useState<
        number | null
    >(null);

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [showAdvancedSettings, setShowAdvancedSettings] =
        useState(false);

    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<
        string | null
    >(null);

    const generatedTitle = useMemo(
        () => buildGeneratedTitle(form),
        [form],
    );

    const groupedSessions = useMemo(() => {
        const groups = new Map<
            string,
            ReportSessionWithStatistics[]
        >();

        for (const session of sessions) {
            const academicYear =
                session.academic_year.trim() || "Unspecified";

            const existing = groups.get(academicYear) ?? [];

            existing.push(session);
            groups.set(academicYear, existing);
        }

        return Array.from(groups.entries())
            .sort(
                ([firstYear], [secondYear]) =>
                    getAcademicYearSortValue(secondYear) -
                    getAcademicYearSortValue(firstYear),
            )
            .map(([academicYear, academicYearSessions]) => ({
                academicYear,
                sessions: [...academicYearSessions].sort(
                    (first, second) =>
                        Number(second.active) -
                        Number(first.active) ||
                        (first.display_order ?? 1) -
                        (second.display_order ?? 1) ||
                        new Date(second.created_at).getTime() -
                        new Date(first.created_at).getTime(),
                ),
            }));
    }, [sessions]);

    async function loadSessions() {
        try {
            setLoading(true);
            setError(null);

            const data = await listReportSessions();

            setSessions(
                data as ReportSessionWithStatistics[],
            );
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

    function updateTextField(
        field:
            | "session_name"
            | "academic_year"
            | "custom_year_group"
            | "reporting_period",
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

    function updateYearGroup(value: YearGroup) {
        setForm((current) => ({
            ...current,
            year_group: value,
            custom_year_group:
                value === "Custom"
                    ? current.custom_year_group
                    : "",
        }));
    }

    function updateReportingMode(value: ReportingMode) {
        setForm((current) => ({
            ...current,
            reporting_mode: value,
        }));
    }

    function updateDisplayOrder(value: string) {
        const parsed = Number.parseInt(value, 10);

        setForm((current) => ({
            ...current,
            display_order:
                Number.isFinite(parsed) && parsed >= 1
                    ? parsed
                    : 1,
        }));
    }

    function clearMessages() {
        setError(null);
        setSuccessMessage(null);
    }

    function resetForm(options?: {
        preserveSuccessMessage?: boolean;
    }) {
        setForm(initialFormState);
        setEditingSessionId(null);
        setDuplicatingSessionId(null);
        setShowAdvancedSettings(false);
        setError(null);

        if (!options?.preserveSuccessMessage) {
            setSuccessMessage(null);
        }
    }

    function startEdit(
        session: ReportSessionWithStatistics,
    ) {
        setEditingSessionId(session.id);
        setDuplicatingSessionId(null);
        setForm(buildFormFromSession(session));
        setShowAdvancedSettings(false);
        clearMessages();

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    }

    function prepareDuplicate(
        session: ReportSessionWithStatistics,
    ) {
        const duplicateForm = buildFormFromSession(session);

        setEditingSessionId(null);
        setDuplicatingSessionId(session.id);
        setForm({
            ...duplicateForm,
            session_name: duplicateForm.session_name
                .replace(/\s+\(Copy\)$/i, "")
                .trim(),
            active: false,
        });
        setShowAdvancedSettings(false);
        setError(null);
        setSuccessMessage(
            "Configuration copied. Check the year group and reporting period, then create the new session.",
        );

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    }

    function validateForm(): string | null {
        if (!form.session_name.trim()) {
            return "Session name is required.";
        }

        if (!form.academic_year.trim()) {
            return "Academic year is required.";
        }

        if (
            form.year_group === "Custom" &&
            !form.custom_year_group.trim()
        ) {
            return "Enter a custom year group.";
        }

        if (!form.reporting_period.trim()) {
            return "Reporting period is required.";
        }

        if (!generatedTitle) {
            return "The report session title could not be generated.";
        }

        const hasAtLeastOneReportField = fieldLabels.some(
            (field) => Boolean(form[field.key]),
        );

        if (!hasAtLeastOneReportField) {
            return "Select at least one report content field.";
        }

        return null;
    }

    function findOtherActiveSessions(
        excludedSessionId?: number | null,
    ): ReportSessionWithStatistics[] {
        return sessions.filter(
            (session) =>
                session.active &&
                session.id !== excludedSessionId,
        );
    }

    function confirmActiveSessionChange(
        excludedSessionId?: number | null,
    ): boolean {
        if (!form.active) {
            return true;
        }

        const activeSessions =
            findOtherActiveSessions(excludedSessionId);

        if (activeSessions.length === 0) {
            return true;
        }

        const activeTitles = activeSessions
            .map((session) => `• ${session.title}`)
            .join("\n");

        return window.confirm(
            [
                "Another report session is currently active:",
                "",
                activeTitles,
                "",
                "Continuing will deactivate the currently active session or sessions.",
                "",
                "Continue?",
            ].join("\n"),
        );
    }

    async function deactivateOtherSessions(
        excludedSessionId?: number | null,
    ) {
        const activeSessions =
            findOtherActiveSessions(excludedSessionId);

        if (activeSessions.length === 0) {
            return;
        }

        const deactivatedSessions = await Promise.all(
            activeSessions.map(async (session) => {
                const existingForm =
                    buildFormFromSession(session);

                const updated = await updateReportSession(
                    session.id,
                    buildPayload({
                        ...existingForm,
                        active: false,
                    }),
                );

                return updated as ReportSessionWithStatistics;
            }),
        );

        setSessions((current) =>
            current.map((session) => {
                const replacement = deactivatedSessions.find(
                    (updated) => updated.id === session.id,
                );

                return replacement ?? session;
            }),
        );
    }

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        const validationError = validateForm();

        if (validationError) {
            setError(validationError);
            setSuccessMessage(null);
            return;
        }

        const activeChangeConfirmed =
            confirmActiveSessionChange(
                editingSessionId,
            );

        if (!activeChangeConfirmed) {
            return;
        }

        try {
            setSaving(true);
            clearMessages();

            if (form.active) {
                await deactivateOtherSessions(
                    editingSessionId,
                );
            }

            const payload = buildPayload(
                form,
                duplicatingSessionId,
            );

            if (editingSessionId !== null) {
                const updated =
                    await updateReportSession(
                        editingSessionId,
                        payload,
                    );

                setSessions((current) =>
                    current.map((session) =>
                        session.id === updated.id
                            ? {
                                ...session,
                                ...updated,
                            }
                            : session,
                    ),
                );

                resetForm({
                    preserveSuccessMessage: true,
                });
                setSuccessMessage(
                    "Report session updated successfully.",
                );
            } else {
                const created =
                    await createReportSession(payload);

                setSessions((current) => [
                    created as ReportSessionWithStatistics,
                    ...current,
                ]);

                resetForm({
                    preserveSuccessMessage: true,
                });
                setSuccessMessage(
                    duplicatingSessionId
                        ? "Report session duplicated successfully."
                        : "Report session created successfully.",
                );
            }
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

    async function handleActivate(
        session: ReportSessionWithStatistics,
    ) {
        if (session.active) {
            setSuccessMessage(
                `${session.title} is already active.`,
            );
            setError(null);
            return;
        }

        const activeSessions =
            findOtherActiveSessions(session.id);

        const confirmationMessage =
            activeSessions.length > 0
                ? [
                    `Activate "${session.title}"?`,
                    "",
                    "This will deactivate:",
                    ...activeSessions.map(
                        (activeSession) =>
                            `• ${activeSession.title}`,
                    ),
                    "",
                    "Continue?",
                ].join("\n")
                : `Activate "${session.title}"?`;

        if (!window.confirm(confirmationMessage)) {
            return;
        }

        try {
            setActivatingSessionId(session.id);
            clearMessages();

            await deactivateOtherSessions(session.id);

            const sessionForm =
                buildFormFromSession(session);

            const updated = await updateReportSession(
                session.id,
                buildPayload({
                    ...sessionForm,
                    active: true,
                }),
            );

            setSessions((current) =>
                current.map((currentSession) =>
                    currentSession.id === session.id
                        ? {
                            ...currentSession,
                            ...updated,
                        }
                        : {
                            ...currentSession,
                            active: false,
                        },
                ),
            );

            setSuccessMessage(
                `${updated.title} is now the active report session.`,
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to activate report session.",
            );

            await loadSessions();
        } finally {
            setActivatingSessionId(null);
        }
    }

    async function handleDelete(
        session: ReportSessionWithStatistics,
    ) {
        const confirmed = window.confirm(
            [
                `Delete "${session.title}"?`,
                "",
                "This cannot be undone.",
            ].join("\n"),
        );

        if (!confirmed) {
            return;
        }

        try {
            setDeletingSessionId(session.id);
            clearMessages();

            await deleteReportSession(session.id);

            setSessions((current) =>
                current.filter(
                    (currentSession) =>
                        currentSession.id !== session.id,
                ),
            );

            if (editingSessionId === session.id) {
                resetForm({
                    preserveSuccessMessage: true,
                });
            }

            setSuccessMessage(
                "Report session deleted successfully.",
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to delete report session.",
            );
        } finally {
            setDeletingSessionId(null);
        }
    }

    async function handleExport(
        session: ReportSessionWithStatistics,
    ) {
        try {
            setExportingSessionId(session.id);
            clearMessages();

            const archive =
                await exportReportSessionZip(session.id);
            const objectUrl =
                URL.createObjectURL(archive);

            const link =
                document.createElement("a");

            link.href = objectUrl;
            link.download = `${createSafeFileName(
                session.title,
            )}-reports.zip`;

            document.body.appendChild(link);
            link.click();
            link.remove();

            window.setTimeout(() => {
                URL.revokeObjectURL(objectUrl);
            }, 0);

            setSuccessMessage(
                "Report ZIP downloaded successfully.",
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to export report session.",
            );
        } finally {
            setExportingSessionId(null);
        }
    }

    function openReportReview(
        session: ReportSessionWithStatistics,
    ) {
        const query = new URLSearchParams({
            report_session_id: String(session.id),
        });

        router.push(
            `/school-admin/reports?${query.toString()}`,
        );
    }
    return (
        <main className="space-y-6 p-8">
            <header>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Report Sessions
                </h1>

                <p className="mt-2 max-w-3xl text-slate-500">
                    Create and manage reporting cycles for each year group.
                    Teachers will use the selected report contents when writing
                    reports, including shared Work Covered content saved for
                    their classes.
                </p>
            </header>

            {error && (
                <div
                    role="alert"
                    className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700"
                >
                    {error}
                </div>
            )}

            {successMessage && (
                <div
                    role="status"
                    className="rounded-2xl border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-700"
                >
                    {successMessage}
                </div>
            )}

            <section className="rounded-2xl border bg-white p-6 shadow-sm">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-950">
                            {editingSessionId !== null
                                ? "Edit Report Session"
                                : duplicatingSessionId !== null
                                    ? "Duplicate Report Session"
                                    : "Create Report Session"}
                        </h2>

                        <p className="mt-1 max-w-2xl text-sm text-slate-500">
                            Enter the basic reporting-cycle information, then
                            choose what teachers should complete.
                        </p>
                    </div>

                    {(editingSessionId !== null ||
                        duplicatingSessionId !== null) && (
                            <button
                                type="button"
                                onClick={() => resetForm()}
                                className="w-fit rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                            >
                                Cancel
                            </button>
                        )}
                </div>

                <form
                    onSubmit={handleSubmit}
                    className="mt-6 space-y-7"
                >
                    <fieldset className="space-y-5">
                        <legend className="text-base font-bold text-slate-950">
                            Basic Information
                        </legend>

                        <div className="grid gap-4 md:grid-cols-2">
                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Session Name
                                </span>

                                <input
                                    value={form.session_name}
                                    onChange={(event) =>
                                        updateTextField(
                                            "session_name",
                                            event.target.value,
                                        )
                                    }
                                    className="rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                    placeholder="Reports"
                                    required
                                />

                                <span className="text-xs text-slate-500">
                                    Usually “Reports”, “Progress Reports” or
                                    “Grade Cards”.
                                </span>
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
                                    className="rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                    placeholder="2026/27"
                                    required
                                />

                                <span className="text-xs text-slate-500">
                                    Use the format 2026/27.
                                </span>
                            </label>

                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Year Group
                                </span>

                                <select
                                    value={form.year_group}
                                    onChange={(event) =>
                                        updateYearGroup(
                                            event.target.value as YearGroup,
                                        )
                                    }
                                    className="rounded-xl border bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                >
                                    {YEAR_GROUP_OPTIONS.map((option) => (
                                        <option
                                            key={option}
                                            value={option}
                                        >
                                            {option}
                                        </option>
                                    ))}
                                </select>

                                <span className="text-xs text-slate-500">
                                    Select the cohort that will use this
                                    reporting session.
                                </span>
                            </label>

                            <label className="grid gap-2">
                                <span className="text-sm font-semibold text-slate-700">
                                    Reporting Period
                                </span>

                                <select
                                    value={
                                        REPORTING_PERIOD_OPTIONS.includes(
                                            form.reporting_period as (typeof REPORTING_PERIOD_OPTIONS)[number],
                                        )
                                            ? form.reporting_period
                                            : "Custom"
                                    }
                                    onChange={(event) => {
                                        const value = event.target.value;

                                        updateTextField(
                                            "reporting_period",
                                            value === "Custom" ? "" : value,
                                        );
                                    }}
                                    className="rounded-xl border bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                >
                                    {REPORTING_PERIOD_OPTIONS.map(
                                        (option) => (
                                            <option
                                                key={option}
                                                value={option}
                                            >
                                                {option}
                                            </option>
                                        ),
                                    )}
                                </select>

                                <span className="text-xs text-slate-500">
                                    Select a school term, half term or reporting
                                    checkpoint.
                                </span>
                            </label>
                        </div>

                        {form.year_group === "Custom" && (
                            <label className="grid gap-2 md:max-w-lg">
                                <span className="text-sm font-semibold text-slate-700">
                                    Custom Year Group
                                </span>

                                <input
                                    value={form.custom_year_group}
                                    onChange={(event) =>
                                        updateTextField(
                                            "custom_year_group",
                                            event.target.value,
                                        )
                                    }
                                    className="rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                    placeholder="Sixth Form, Reception or Staff"
                                    required
                                />
                            </label>
                        )}

                        {!REPORTING_PERIOD_OPTIONS.includes(
                            form.reporting_period as (typeof REPORTING_PERIOD_OPTIONS)[number],
                        ) && (
                                <label className="grid gap-2 md:max-w-lg">
                                    <span className="text-sm font-semibold text-slate-700">
                                        Custom Reporting Period
                                    </span>

                                    <input
                                        value={form.reporting_period}
                                        onChange={(event) =>
                                            updateTextField(
                                                "reporting_period",
                                                event.target.value,
                                            )
                                        }
                                        className="rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                        placeholder="October Progress Review"
                                        required
                                    />
                                </label>
                            )}

                        <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4">
                            <span className="text-xs font-bold uppercase tracking-wide text-blue-700">
                                Display title
                            </span>

                            <p className="mt-1 text-lg font-bold text-slate-950">
                                {generatedTitle ||
                                    "Complete the fields above"}
                            </p>

                            <p className="mt-1 text-sm text-slate-600">
                                This title will be shown to teachers, reviewers
                                and parents.
                            </p>
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
                                className="mt-1 h-4 w-4"
                            />

                            <span>
                                <span className="block text-sm font-bold text-slate-900">
                                    Active session
                                </span>

                                <span className="mt-1 block text-sm text-slate-500">
                                    Teachers will see the active session first.
                                    Activating this session will deactivate any
                                    currently active report session after
                                    confirmation.
                                </span>
                            </span>
                        </label>
                    </fieldset>

                    <fieldset className="space-y-4 border-t pt-7">
                        <div>
                            <legend className="text-base font-bold text-slate-950">
                                Report Contents
                            </legend>

                            <p className="mt-1 text-sm text-slate-500">
                                Select the fields teachers and pastoral staff
                                should complete for this reporting cycle.
                            </p>
                        </div>

                        <div className="grid gap-3 md:grid-cols-2">
                            {fieldLabels.map((field) => (
                                <label
                                    key={field.key}
                                    className="flex cursor-pointer items-start gap-3 rounded-2xl border p-4 transition hover:border-blue-200 hover:bg-blue-50/40"
                                >
                                    <input
                                        type="checkbox"
                                        checked={Boolean(
                                            form[field.key],
                                        )}
                                        onChange={(event) =>
                                            updateBooleanField(
                                                field.key,
                                                event.target.checked,
                                            )
                                        }
                                        className="mt-1 h-4 w-4"
                                    />

                                    <span>
                                        <span className="block text-sm font-bold text-slate-900">
                                            {field.label}
                                        </span>

                                        <span className="mt-1 block text-sm text-slate-500">
                                            {field.description}
                                        </span>
                                    </span>
                                </label>
                            ))}
                        </div>

                        {form.include_work_covered && (
                            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                                <p className="text-sm font-bold text-amber-900">
                                    Shared Work Covered enabled
                                </p>

                                <p className="mt-1 text-sm text-amber-800">
                                    Teachers can use Save for Class to store one
                                    Work Covered summary for the selected report
                                    session, class and subject. The saved text
                                    can then be reused while moving between
                                    students.
                                </p>
                            </div>
                        )}
                    </fieldset>

                    <section className="border-t pt-7">
                        <button
                            type="button"
                            onClick={() =>
                                setShowAdvancedSettings(
                                    (current) => !current,
                                )
                            }
                            aria-expanded={showAdvancedSettings}
                            className="flex w-full items-center justify-between rounded-2xl border bg-slate-50 px-4 py-3 text-left transition hover:bg-slate-100"
                        >
                            <span>
                                <span className="block text-sm font-bold text-slate-900">
                                    Advanced Settings
                                </span>

                                <span className="mt-1 block text-sm text-slate-500">
                                    Configure reporting mode, edit permissions,
                                    previous-report information and ordering.
                                </span>
                            </span>

                            <span
                                aria-hidden="true"
                                className="ml-4 text-xl font-bold text-slate-500"
                            >
                                {showAdvancedSettings ? "−" : "+"}
                            </span>
                        </button>

                        {showAdvancedSettings && (
                            <div className="mt-4 space-y-5 rounded-2xl border p-5">
                                <div className="grid gap-4 md:grid-cols-2">
                                    <label className="grid gap-2">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Reporting Mode
                                        </span>

                                        <select
                                            value={form.reporting_mode}
                                            onChange={(event) =>
                                                updateReportingMode(
                                                    event.target
                                                        .value as ReportingMode,
                                                )
                                            }
                                            className="rounded-xl border bg-white px-3 py-2.5 text-sm"
                                        >
                                            <option value="full_report">
                                                Full report
                                            </option>
                                            <option value="grade_card">
                                                Grade card
                                            </option>
                                            <option value="both">
                                                Full report and grade card
                                            </option>
                                        </select>
                                    </label>

                                    <label className="grid gap-2">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Display Order
                                        </span>

                                        <input
                                            type="number"
                                            min={1}
                                            value={form.display_order}
                                            onChange={(event) =>
                                                updateDisplayOrder(
                                                    event.target.value,
                                                )
                                            }
                                            className="rounded-xl border px-3 py-2.5 text-sm"
                                        />

                                        <span className="text-xs text-slate-500">
                                            Lower numbers appear first.
                                        </span>
                                    </label>
                                </div>

                                <div className="grid gap-3 md:grid-cols-2">
                                    <label className="flex items-start gap-3 rounded-2xl border p-4">
                                        <input
                                            type="checkbox"
                                            checked={
                                                form.enable_report_generation
                                            }
                                            onChange={(event) =>
                                                updateBooleanField(
                                                    "enable_report_generation",
                                                    event.target.checked,
                                                )
                                            }
                                            className="mt-1"
                                        />

                                        <span>
                                            <span className="block text-sm font-bold text-slate-900">
                                                Enable report generation
                                            </span>

                                            <span className="mt-1 block text-sm text-slate-500">
                                                Allow teachers to generate
                                                report comments from their
                                                notes.
                                            </span>
                                        </span>
                                    </label>

                                    <label className="flex items-start gap-3 rounded-2xl border p-4">
                                        <input
                                            type="checkbox"
                                            checked={
                                                form.allow_teacher_edit_after_submission
                                            }
                                            onChange={(event) =>
                                                updateBooleanField(
                                                    "allow_teacher_edit_after_submission",
                                                    event.target.checked,
                                                )
                                            }
                                            className="mt-1"
                                        />

                                        <span>
                                            <span className="block text-sm font-bold text-slate-900">
                                                Teacher edits after submission
                                            </span>

                                            <span className="mt-1 block text-sm text-slate-500">
                                                Permit teachers to edit reports
                                                after they have submitted them.
                                            </span>
                                        </span>
                                    </label>

                                    <label className="flex items-start gap-3 rounded-2xl border p-4">
                                        <input
                                            type="checkbox"
                                            checked={
                                                form.allow_smt_edit_after_approval
                                            }
                                            onChange={(event) =>
                                                updateBooleanField(
                                                    "allow_smt_edit_after_approval",
                                                    event.target.checked,
                                                )
                                            }
                                            className="mt-1"
                                        />

                                        <span>
                                            <span className="block text-sm font-bold text-slate-900">
                                                SMT edits after approval
                                            </span>

                                            <span className="mt-1 block text-sm text-slate-500">
                                                Allow authorised reviewers to
                                                correct approved reports before
                                                publication.
                                            </span>
                                        </span>
                                    </label>

                                    <label className="flex items-start gap-3 rounded-2xl border p-4">
                                        <input
                                            type="checkbox"
                                            checked={
                                                form.show_previous_grades
                                            }
                                            onChange={(event) =>
                                                updateBooleanField(
                                                    "show_previous_grades",
                                                    event.target.checked,
                                                )
                                            }
                                            className="mt-1"
                                        />

                                        <span>
                                            <span className="block text-sm font-bold text-slate-900">
                                                Show previous grades
                                            </span>

                                            <span className="mt-1 block text-sm text-slate-500">
                                                Display earlier grades for
                                                comparison while writing the
                                                report.
                                            </span>
                                        </span>
                                    </label>

                                    <label className="flex items-start gap-3 rounded-2xl border p-4">
                                        <input
                                            type="checkbox"
                                            checked={
                                                form.show_previous_tutor_comments
                                            }
                                            onChange={(event) =>
                                                updateBooleanField(
                                                    "show_previous_tutor_comments",
                                                    event.target.checked,
                                                )
                                            }
                                            className="mt-1"
                                        />

                                        <span>
                                            <span className="block text-sm font-bold text-slate-900">
                                                Show previous tutor comments
                                            </span>

                                            <span className="mt-1 block text-sm text-slate-500">
                                                Display previous pastoral
                                                comments to authorised staff.
                                            </span>
                                        </span>
                                    </label>

                                    <label className="flex items-start gap-3 rounded-2xl border p-4">
                                        <input
                                            type="checkbox"
                                            checked={
                                                form.show_progress_journey
                                            }
                                            onChange={(event) =>
                                                updateBooleanField(
                                                    "show_progress_journey",
                                                    event.target.checked,
                                                )
                                            }
                                            className="mt-1"
                                        />

                                        <span>
                                            <span className="block text-sm font-bold text-slate-900">
                                                Show progress journey
                                            </span>

                                            <span className="mt-1 block text-sm text-slate-500">
                                                Include progress information
                                                across reporting checkpoints.
                                            </span>
                                        </span>
                                    </label>
                                </div>
                            </div>
                        )}
                    </section>

                    <div className="flex flex-wrap gap-3 border-t pt-5">
                        <button
                            type="submit"
                            disabled={saving}
                            data-custom-button="true"
                            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {saving
                                ? "Saving..."
                                : editingSessionId !== null
                                    ? "Update Session"
                                    : duplicatingSessionId !== null
                                        ? "Create Duplicate"
                                        : "Create Session"}
                        </button>

                        <button
                            type="button"
                            onClick={() => resetForm()}
                            disabled={saving}
                            data-custom-button="true"
                            className="rounded-xl border px-5 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                        >
                            Reset
                        </button>
                    </div>
                </form>
            </section>
            <section className="rounded-2xl border bg-white p-6 shadow-sm">
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-950">
                            Existing Report Sessions
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            Sessions are grouped by academic year. Open a
                            session to review progress, duplicate its
                            configuration, activate it or export its reports.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => void loadSessions()}
                        disabled={loading}
                        data-custom-button="true"
                        className="w-fit rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {loading ? "Refreshing..." : "Refresh"}
                    </button>
                </div>

                {loading ? (
                    <p className="mt-6 text-sm text-slate-500">
                        Loading report sessions...
                    </p>
                ) : groupedSessions.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                        No report sessions have been created yet.
                    </div>
                ) : (
                    <div className="mt-6 space-y-8">
                        {groupedSessions.map((group) => (
                            <section
                                key={group.academicYear}
                                className="space-y-4"
                            >
                                <div className="flex items-center gap-3">
                                    <h3 className="text-lg font-extrabold text-slate-950">
                                        {group.academicYear}
                                    </h3>

                                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                                        {group.sessions.length}{" "}
                                        {group.sessions.length === 1
                                            ? "session"
                                            : "sessions"}
                                    </span>
                                </div>

                                <div className="grid gap-4">
                                    {group.sessions.map((session) => {
                                        const draftCount =
                                            session.draft_count ?? 0;
                                        const submittedCount =
                                            session.submitted_count ?? 0;
                                        const tutorReviewCount =
                                            session.tutor_review_count ?? 0;
                                        const readyForSmtCount =
                                            session.ready_for_smt_count ?? 0;
                                        const approvedCount =
                                            session.approved_count ?? 0;
                                        const publishedCount =
                                            session.published_count ?? 0;

                                        const totalReports =
                                            session.total_reports ??
                                            draftCount +
                                            submittedCount +
                                            tutorReviewCount +
                                            readyForSmtCount +
                                            approvedCount +
                                            publishedCount;

                                        return (
                                            <article
                                                key={session.id}
                                                className="rounded-2xl border bg-slate-50 p-5"
                                            >
                                                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                                                    <div className="min-w-0">
                                                        <div className="flex flex-wrap items-center gap-2">
                                                            <h4 className="text-lg font-bold text-slate-950">
                                                                {
                                                                    session.title
                                                                }
                                                            </h4>

                                                            <span
                                                                className={`rounded-full px-3 py-1 text-xs font-bold ${session.active
                                                                    ? "bg-green-100 text-green-700"
                                                                    : "bg-slate-200 text-slate-600"
                                                                    }`}
                                                            >
                                                                {session.active
                                                                    ? "Active"
                                                                    : "Inactive"}
                                                            </span>
                                                        </div>

                                                        <p className="mt-1 text-sm text-slate-500">
                                                            {normaliseReportingPeriod(
                                                                session,
                                                            )}
                                                            {" · "}
                                                            Created{" "}
                                                            {formatDate(
                                                                session.created_at,
                                                            )}
                                                        </p>

                                                        {session.copied_from_session_id && (
                                                            <p className="mt-1 text-xs font-medium text-slate-500">
                                                                Created from a
                                                                duplicated
                                                                session
                                                                configuration.
                                                            </p>
                                                        )}
                                                    </div>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            openReportReview(
                                                                session,
                                                            )
                                                        }
                                                        data-custom-button="true"
                                                        className="w-fit rounded-xl bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800"
                                                    >
                                                        Open Reports →
                                                    </button>
                                                </div>

                                                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
                                                    <div className="rounded-xl border bg-white p-3">
                                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                            Total
                                                        </p>
                                                        <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                                            {totalReports}
                                                        </p>
                                                    </div>

                                                    <div className="rounded-xl border bg-white p-3">
                                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                            Drafts
                                                        </p>
                                                        <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                                            {draftCount}
                                                        </p>
                                                    </div>

                                                    <div className="rounded-xl border bg-white p-3">
                                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                            Submitted
                                                        </p>
                                                        <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                                            {submittedCount}
                                                        </p>
                                                    </div>

                                                    <div className="rounded-xl border bg-white p-3">
                                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                            Tutor Review
                                                        </p>
                                                        <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                                            {
                                                                tutorReviewCount
                                                            }
                                                        </p>
                                                    </div>

                                                    <div className="rounded-xl border bg-white p-3">
                                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                            Approved
                                                        </p>
                                                        <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                                            {approvedCount}
                                                        </p>
                                                    </div>

                                                    <div className="rounded-xl border bg-white p-3">
                                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                            Published
                                                        </p>
                                                        <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                                            {publishedCount}
                                                        </p>
                                                    </div>
                                                </div>

                                                {readyForSmtCount > 0 && (
                                                    <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                                                        <strong>
                                                            {
                                                                readyForSmtCount
                                                            }
                                                        </strong>{" "}
                                                        {readyForSmtCount === 1
                                                            ? "report is"
                                                            : "reports are"}{" "}
                                                        ready for SMT review.
                                                    </div>
                                                )}

                                                <div className="mt-5">
                                                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                        Enabled report contents
                                                    </p>

                                                    <div className="mt-2 flex flex-wrap gap-2">
                                                        {fieldLabels
                                                            .filter((field) =>
                                                                Boolean(
                                                                    session[
                                                                    field
                                                                        .key
                                                                    ],
                                                                ),
                                                            )
                                                            .map((field) => (
                                                                <span
                                                                    key={
                                                                        field.key
                                                                    }
                                                                    className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700"
                                                                >
                                                                    {
                                                                        field.label
                                                                    }
                                                                </span>
                                                            ))}

                                                        {!fieldLabels.some(
                                                            (field) =>
                                                                Boolean(
                                                                    session[
                                                                    field
                                                                        .key
                                                                    ],
                                                                ),
                                                        ) && (
                                                                <span className="text-sm text-slate-500">
                                                                    No report fields
                                                                    enabled.
                                                                </span>
                                                            )}
                                                    </div>
                                                </div>

                                                <div className="mt-5 flex flex-wrap gap-3 border-t pt-4">
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            startEdit(session)
                                                        }
                                                        data-custom-button="true"
                                                        className="rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-white"
                                                    >
                                                        ✏️ Edit
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            prepareDuplicate(
                                                                session,
                                                            )
                                                        }
                                                        data-custom-button="true"
                                                        className="rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-white"
                                                    >
                                                        📄 Duplicate
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleActivate(
                                                                session,
                                                            )
                                                        }
                                                        disabled={
                                                            session.active ||
                                                            activatingSessionId ===
                                                            session.id
                                                        }
                                                        data-custom-button="true"
                                                        className="rounded-xl border border-green-200 px-4 py-2 text-sm font-semibold text-green-700 transition hover:bg-green-50 disabled:cursor-not-allowed disabled:opacity-50"
                                                    >
                                                        {activatingSessionId ===
                                                            session.id
                                                            ? "Activating..."
                                                            : session.active
                                                                ? "✅ Active"
                                                                : "✅ Activate"}
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleExport(
                                                                session,
                                                            )
                                                        }
                                                        disabled={
                                                            exportingSessionId ===
                                                            session.id
                                                        }
                                                        data-custom-button="true"
                                                        className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                                                    >
                                                        {exportingSessionId ===
                                                            session.id
                                                            ? "Exporting..."
                                                            : "📦 Export ZIP"}
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleDelete(
                                                                session,
                                                            )
                                                        }
                                                        disabled={
                                                            deletingSessionId ===
                                                            session.id
                                                        }
                                                        data-custom-button="true"
                                                        className="rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                                                    >
                                                        {deletingSessionId ===
                                                            session.id
                                                            ? "Deleting..."
                                                            : "🗑 Delete"}
                                                    </button>
                                                </div>
                                            </article>
                                        );
                                    })}
                                </div>
                            </section>
                        ))}
                    </div>
                )}
            </section>
        </main>
    );
}
