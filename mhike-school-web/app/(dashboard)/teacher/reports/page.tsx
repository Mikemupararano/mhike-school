"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
    listReportSessions,
    type ReportSession,
} from "@/lib/report-sessions";
import {
    listReportClasses,
    listReportClassStudents,
    listReportTeachers,
    type ReportClass,
    type ReportStudent,
    type ReportTeacher,
} from "@/lib/report-data";
import {
    checkReportComment,
    generateReportFromNotes,
    type ReportQualityResponse,
} from "@/lib/report-quality";
import {
    createStudentReport,
    deleteStudentReport,
    listStudentReports,
    updateStudentReport,
    type StudentReport,
    type StudentReportCreateInput,
} from "@/lib/services/studentReports";

type SaveAction = "draft" | "next" | "close" | "submit";

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
    tutor_comment: string;
    academic_year: string;
    term: string;
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
    tutor_comment: "",
    academic_year: "2026/27",
    term: "",
};

const REPORT_STATUS_SUBMITTED = "submitted";

function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function getStatusBadgeClass(status: string): string {
    switch (status) {
        case "published":
            return "bg-green-50 text-green-700";
        case "approved":
            return "bg-blue-50 text-blue-700";
        case "submitted":
            return "bg-purple-50 text-purple-700";
        default:
            return "bg-amber-50 text-amber-700";
    }
}

function buildReportText(
    form: ReportFormState,
    activeSession: ReportSession | null,
): string {
    const sections: string[] = [];

    if (activeSession?.include_work_covered && form.work_covered.trim()) {
        sections.push(`Work covered:\n${form.work_covered.trim()}`);
    }

    if (
        (!activeSession || activeSession.include_student_comment) &&
        form.report_text.trim()
    ) {
        sections.push(`Student comment:\n${form.report_text.trim()}`);
    }

    if (activeSession?.include_exam_mark && form.exam_mark.trim()) {
        sections.push(`Exam mark:\n${form.exam_mark.trim()}`);
    }

    if (
        activeSession?.include_attainment_grade &&
        form.attainment_grade.trim()
    ) {
        sections.push(`Attainment grade:\n${form.attainment_grade.trim()}`);
    }

    if (activeSession?.include_effort_grade && form.effort_grade.trim()) {
        sections.push(`Effort grade:\n${form.effort_grade.trim()}`);
    }

    if (activeSession?.include_target_grade && form.target_grade.trim()) {
        sections.push(`Target grade:\n${form.target_grade.trim()}`);
    }

    if (activeSession?.include_next_steps && form.next_steps.trim()) {
        sections.push(`Next steps:\n${form.next_steps.trim()}`);
    }

    if (activeSession?.include_tutor_comment && form.tutor_comment.trim()) {
        sections.push(`Tutor comment:\n${form.tutor_comment.trim()}`);
    }

    return sections.join("\n\n");
}

export default function TeacherReportsPage() {
    const router = useRouter();

    const [reports, setReports] = useState<StudentReport[]>([]);
    const [reportSessions, setReportSessions] = useState<ReportSession[]>([]);
    const [activeSession, setActiveSession] = useState<ReportSession | null>(
        null,
    );

    const [teachers, setTeachers] = useState<ReportTeacher[]>([]);
    const [classes, setClasses] = useState<ReportClass[]>([]);
    const [students, setStudents] = useState<ReportStudent[]>([]);

    const [form, setForm] = useState<ReportFormState>(initialFormState);
    const [loading, setLoading] = useState(true);
    const [loadingClasses, setLoadingClasses] = useState(false);
    const [loadingStudents, setLoadingStudents] = useState(false);
    const [saving, setSaving] = useState(false);
    const [checkingQuality, setCheckingQuality] = useState(false);
    const [generatingFromNotes, setGeneratingFromNotes] = useState(false);
    const [qualityResult, setQualityResult] =
        useState<ReportQualityResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    useEffect(() => {
        async function loadPageData() {
            try {
                setLoading(true);
                setError(null);

                const [reportsData, sessionsData, teachersData, classesData] =
                    await Promise.all([
                        listStudentReports(),
                        listReportSessions(),
                        listReportTeachers(),
                        listReportClasses(),
                    ]);

                setReports(reportsData);
                setReportSessions(sessionsData);
                setTeachers(teachersData);
                setClasses(classesData);

                const active =
                    sessionsData.find((session) => session.active) ??
                    sessionsData[0] ??
                    null;

                setActiveSession(active);

                if (active) {
                    setForm((current) => ({
                        ...current,
                        report_session_id: String(active.id),
                        academic_year: active.academic_year,
                        term: active.term ?? "",
                        title: current.title || active.title,
                    }));
                }
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

        void loadPageData();
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
        if (field === "report_text") {
            setQualityResult(null);
        }

        setForm((current) => ({
            ...current,
            [field]: value,
        }));
    }

    function handleSessionChange(sessionId: string) {
        const selectedSession =
            reportSessions.find(
                (session) => String(session.id) === sessionId,
            ) ?? null;

        setActiveSession(selectedSession);

        setForm((current) => ({
            ...current,
            report_session_id: sessionId,
            academic_year:
                selectedSession?.academic_year ?? current.academic_year,
            term: selectedSession?.term ?? current.term,
            title: selectedSession?.title ?? current.title,
        }));
    }

    async function handleTeacherChange(teacherId: string) {
        setForm((current) => ({
            ...current,
            teacher_id: teacherId,
            class_id: "",
            student_id: "",
        }));

        setStudents([]);

        try {
            setLoadingClasses(true);
            setError(null);

            const data = await listReportClasses(teacherId || null);

            setClasses(data);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load classes.",
            );
        } finally {
            setLoadingClasses(false);
        }
    }

    async function handleClassChange(classId: string) {
        setForm((current) => ({
            ...current,
            class_id: classId,
            student_id: "",
        }));

        if (!classId) {
            setStudents([]);
            return;
        }

        try {
            setLoadingStudents(true);
            setError(null);

            const data = await listReportClassStudents(classId);

            setStudents(data);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load students.",
            );
        } finally {
            setLoadingStudents(false);
        }
    }

    async function handleCheckQuality() {
        if (!form.report_text.trim()) {
            setError("Enter a student comment first.");
            return;
        }

        try {
            setCheckingQuality(true);
            setError(null);
            setSuccessMessage(null);

            const result = await checkReportComment(form.report_text);

            setQualityResult(result);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to check UK grammar and spelling.",
            );
        } finally {
            setCheckingQuality(false);
        }
    }

    async function handleGenerateFromNotes() {
        if (!form.work_covered.trim() && !form.report_text.trim()) {
            setError("Enter work covered and/or teacher notes first.");
            return;
        }

        try {
            setGeneratingFromNotes(true);
            setError(null);
            setSuccessMessage(null);
            setQualityResult(null);

            const selectedStudent = students.find(
                (student) => String(student.id) === form.student_id,
            );

            const selectedClass = classes.find(
                (classItem) => String(classItem.id) === form.class_id,
            );

            const notesForGeneration = [
                form.work_covered.trim()
                    ? `Work covered: ${form.work_covered.trim()}`
                    : "",
                form.report_text.trim()
                    ? `Teacher notes: ${form.report_text.trim()}`
                    : "",
            ]
                .filter(Boolean)
                .join("\n\n");

            const generated = await generateReportFromNotes(
                notesForGeneration,
                selectedStudent?.full_name,
                selectedClass?.subject_name ?? undefined,
                selectedClass?.name ?? undefined,
            );

            updateFormField("report_text", generated.generated_comment);
            setSuccessMessage("Report generated from notes.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to generate report from notes.",
            );
        } finally {
            setGeneratingFromNotes(false);
        }
    }

    function moveToNextStudent() {
        const currentIndex = students.findIndex(
            (student) => String(student.id) === form.student_id,
        );

        const nextStudent = students[currentIndex + 1];

        setQualityResult(null);

        setForm((current) => ({
            ...current,
            student_id: nextStudent ? String(nextStudent.id) : "",
            report_text: "",
            exam_mark: "",
            attainment_grade: "",
            effort_grade: "",
            target_grade: "",
            next_steps: "",
            tutor_comment: "",
        }));

        setSuccessMessage(
            nextStudent
                ? "Draft saved. Moved to the next student."
                : "Draft saved. No more students in this class.",
        );
    }

    async function saveReport(action: SaveAction) {
        const studentId = Number(form.student_id);

        if (!studentId || Number.isNaN(studentId)) {
            setError("Select a valid student.");
            return;
        }

        if (!activeSession) {
            setError("Select a report session.");
            return;
        }

        if (!form.title.trim()) {
            setError("Report title is required.");
            return;
        }

        const reportText = buildReportText(form, activeSession);

        if (!reportText.trim()) {
            setError("Report text is required.");
            return;
        }

        const reportSessionId = Number(form.report_session_id);

        if (!reportSessionId || Number.isNaN(reportSessionId)) {
            setError("Select a report session.");
            return;
        }

        const payload: StudentReportCreateInput = {
            student_id: studentId,
            report_session_id: reportSessionId,
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

            if (action === "submit") {
                const submitted = await updateStudentReport(created.id, {
                    status: REPORT_STATUS_SUBMITTED,
                });

                setReports((current) => [submitted, ...current]);
                setSuccessMessage("Report submitted for review.");
                return;
            }

            setReports((current) => [created, ...current]);

            if (action === "next") {
                moveToNextStudent();
                return;
            }

            if (action === "close") {
                setForm({
                    ...initialFormState,
                    report_session_id: String(activeSession.id),
                    academic_year: activeSession.academic_year,
                    term: activeSession.term ?? "",
                    title: activeSession.title,
                });

                setStudents([]);
                setQualityResult(null);
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

    const generationDisabled =
        generatingFromNotes ||
        (!form.work_covered.trim() && !form.report_text.trim());

    return (
        <main className="space-y-6 p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Student Reports
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Write student draft reports using the active report
                        session.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => router.back()}
                    className="w-fit rounded-xl border px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                >
                    ← Back
                </button>
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
                                    void handleTeacherChange(
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                            >
                                <option value="">
                                    Current teacher / all classes
                                </option>

                                {teachers.map((teacher) => (
                                    <option
                                        key={teacher.id}
                                        value={String(teacher.id)}
                                    >
                                        {teacher.full_name}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Class
                            </span>

                            <select
                                value={form.class_id}
                                onChange={(event) =>
                                    void handleClassChange(event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                            >
                                <option value="">
                                    {loadingClasses
                                        ? "Loading classes..."
                                        : "Select class"}
                                </option>

                                {classes.map((classGroup) => (
                                    <option
                                        key={classGroup.id}
                                        value={String(classGroup.id)}
                                    >
                                        {classGroup.name}
                                        {classGroup.subject_name
                                            ? ` · ${classGroup.subject_name}`
                                            : ""}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Student
                            </span>

                            <select
                                value={form.student_id}
                                onChange={(event) =>
                                    updateFormField(
                                        "student_id",
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                            >
                                <option value="">
                                    {loadingStudents
                                        ? "Loading students..."
                                        : form.class_id
                                            ? "Select student"
                                            : "Select a class first"}
                                </option>

                                {students.map((student) => (
                                    <option
                                        key={student.id}
                                        value={String(student.id)}
                                    >
                                        {student.full_name}
                                    </option>
                                ))}
                            </select>
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
                                    handleSessionChange(event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-sm"
                            >
                                <option value="">
                                    {reportSessions.length === 0
                                        ? "No report sessions available"
                                        : "Select report session"}
                                </option>

                                {reportSessions.map((session) => (
                                    <option
                                        key={session.id}
                                        value={String(session.id)}
                                    >
                                        {session.title}
                                        {session.active ? " (Active)" : ""}
                                    </option>
                                ))}
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

                    {activeSession?.include_work_covered && (
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

                    {(!activeSession ||
                        activeSession.include_student_comment) && (
                            <div className="grid gap-3">
                                <label className="grid gap-2">
                                    <span className="text-sm font-semibold text-slate-700">
                                        Teacher Notes / Generated Student Comment
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
                                        placeholder="Write teacher notes first, then click Generate From Notes. The generated report will appear here."
                                    />
                                </label>

                                <div className="flex flex-wrap gap-3">
                                    <button
                                        type="button"
                                        onClick={() =>
                                            void handleGenerateFromNotes()
                                        }
                                        disabled={generationDisabled}
                                        className="rounded-xl bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {generatingFromNotes
                                            ? "Generating..."
                                            : "Generate From Notes"}
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => void handleCheckQuality()}
                                        disabled={
                                            checkingQuality ||
                                            !form.report_text.trim()
                                        }
                                        className="rounded-xl border px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {checkingQuality
                                            ? "Checking..."
                                            : "Check UK Grammar & Spelling"}
                                    </button>
                                </div>

                                {qualityResult && (
                                    <div className="rounded-xl border bg-slate-50 p-4">
                                        <h3 className="font-bold text-slate-900">
                                            Report Quality Review
                                        </h3>

                                        <p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-700">
                                            {qualityResult.corrected_comment}
                                        </p>

                                        {qualityResult.issues.length > 0 && (
                                            <ul className="mt-3 list-disc pl-5 text-sm text-slate-600">
                                                {qualityResult.issues.map(
                                                    (issue, index) => (
                                                        <li key={index}>
                                                            {issue.message}
                                                        </li>
                                                    ),
                                                )}
                                            </ul>
                                        )}

                                        <button
                                            type="button"
                                            onClick={() =>
                                                updateFormField(
                                                    "report_text",
                                                    qualityResult.corrected_comment,
                                                )
                                            }
                                            className="mt-4 rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
                                        >
                                            Apply Suggestions
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}

                    <div className="grid gap-4 md:grid-cols-3">
                        {activeSession?.include_exam_mark && (
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

                        {activeSession?.include_attainment_grade && (
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

                        {activeSession?.include_effort_grade && (
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
                        {activeSession?.include_target_grade && (
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

                        {activeSession?.include_next_steps && (
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

                    {activeSession?.include_tutor_comment && (
                        <label className="grid gap-2">
                            <span className="text-sm font-semibold text-slate-700">
                                Tutor Comment
                            </span>

                            <textarea
                                value={form.tutor_comment}
                                onChange={(event) =>
                                    updateFormField(
                                        "tutor_comment",
                                        event.target.value,
                                    )
                                }
                                className="min-h-28 rounded-xl border px-3 py-2 text-sm"
                                placeholder="Write tutor comment..."
                            />
                        </label>
                    )}

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
                            onClick={() => void saveReport("submit")}
                            className="rounded-xl bg-purple-600 px-5 py-2 text-sm font-bold text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            Submit For Review
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
                                        className={`rounded-full px-3 py-1 text-sm font-bold ${getStatusBadgeClass(
                                            report.status,
                                        )}`}
                                    >
                                        {report.status}
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