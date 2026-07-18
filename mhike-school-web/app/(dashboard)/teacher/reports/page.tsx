/*
 * Reconciled teacher reports page.
 *
 * Key safeguards:
 * - AI generation never overwrites a manually written or edited final report.
 * - Work covered remains curriculum context; teacher notes remain pupil evidence.
 * - Only the pupil's first name is sent for report generation.
 * - Non-editable workflow stages remain read-only for teachers.
 * - Selected teacher/session filters are applied consistently.
 */

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
    submitStudentReport,
    updateStudentReport,
    type StudentReport,
    type StudentReportCreateInput,
} from "@/lib/services/studentReports";

type SaveAction = "draft" | "next" | "close" | "submit";

type TeacherFacingStatus =
    | "not_started"
    | "draft"
    | "returned_by_tutor"
    | "returned_by_smt"
    | "submitted"
    | "tutor_review"
    | "ready_for_smt"
    | "approved"
    | "published";

type StudentCompletionRow = {
    student: ReportStudent;
    report: StudentReport | null;
    status: TeacherFacingStatus;
    isComplete: boolean;
};

const COMPLETE_REPORT_STATUSES = new Set<TeacherFacingStatus>([
    "submitted",
    "tutor_review",
    "ready_for_smt",
    "approved",
    "published",
]);

const EDITABLE_REPORT_STATUSES = new Set<TeacherFacingStatus>([
    "draft",
    "returned_by_tutor",
    "returned_by_smt",
]);

type ReportFormState = {
    teacher_id: string;
    class_id: string;
    student_id: string;
    report_session_id: string;
    title: string;
    work_covered: string;
    teacher_notes: string;
    generated_report_text: string;
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
    teacher_notes: "",
    generated_report_text: "",
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


function getFirstName(fullName?: string | null): string | undefined {
    const cleaned = fullName?.trim();

    if (!cleaned) {
        return undefined;
    }

    return cleaned.split(/\s+/)[0];
}

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
        case "tutor_review":
        case "ready_for_smt":
            return "bg-purple-50 text-purple-700";
        case "returned_by_tutor":
        case "returned_by_smt":
            return "bg-red-50 text-red-700";
        case "not_started":
            return "bg-slate-100 text-slate-700";
        default:
            return "bg-amber-50 text-amber-700";
    }
}

function getStatusLabel(status: string): string {
    switch (status) {
        case "not_started":
            return "Not started";
        case "draft":
            return "Draft";
        case "returned_by_tutor":
            return "Returned by tutor";
        case "returned_by_smt":
            return "Returned by SMT";
        case "submitted":
            return "Submitted";
        case "tutor_review":
            return "Tutor review";
        case "ready_for_smt":
            return "Ready for SMT";
        case "approved":
            return "Approved";
        case "published":
            return "Published";
        default:
            return status.replaceAll("_", " ");
    }
}

function upsertReport(
    reports: StudentReport[],
    nextReport: StudentReport,
): StudentReport[] {
    const exists = reports.some((report) => report.id === nextReport.id);

    if (!exists) {
        return [nextReport, ...reports];
    }

    return reports.map((report) =>
        report.id === nextReport.id ? nextReport : report,
    );
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
    const [editingReportId, setEditingReportId] = useState<number | null>(null);

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
    const [outstandingOnly, setOutstandingOnly] = useState(false);

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

    const completionRows = useMemo<StudentCompletionRow[]>(() => {
        const selectedTeacherId = Number(form.teacher_id);

        return students.map((student) => {
            const matchingReports = reports
                .filter(
                    (report) =>
                        report.student_id === student.id &&
                        (!form.report_session_id ||
                            String(report.report_session_id ?? "") ===
                            form.report_session_id),
                )
                .filter((report) => {
                    if (!selectedTeacherId || Number.isNaN(selectedTeacherId)) {
                        return true;
                    }

                    const teacherId = (
                        report as StudentReport & {
                            teacher_id?: number | null;
                        }
                    ).teacher_id;

                    return teacherId == null || teacherId === selectedTeacherId;
                })
                .sort(
                    (first, second) =>
                        new Date(second.updated_at ?? second.created_at).getTime() -
                        new Date(first.updated_at ?? first.created_at).getTime(),
                );

            const report = matchingReports[0] ?? null;
            const status = (report?.status ??
                "not_started") as TeacherFacingStatus;

            return {
                student,
                report,
                status,
                isComplete: COMPLETE_REPORT_STATUSES.has(status),
            };
        });
    }, [form.report_session_id, form.teacher_id, reports, students]);

    const completionSummary = useMemo(() => {
        const total = completionRows.length;
        const completed = completionRows.filter((row) => row.isComplete).length;
        const outstanding = total - completed;
        const notStarted = completionRows.filter(
            (row) => row.status === "not_started",
        ).length;
        const drafts = completionRows.filter(
            (row) => row.status === "draft",
        ).length;
        const returned = completionRows.filter(
            (row) =>
                row.status === "returned_by_tutor" ||
                row.status === "returned_by_smt",
        ).length;
        const percentage =
            total === 0 ? 0 : Math.round((completed / total) * 100);

        return {
            total,
            completed,
            outstanding,
            notStarted,
            drafts,
            returned,
            percentage,
        };
    }, [completionRows]);

    const visibleCompletionRows = useMemo(
        () =>
            outstandingOnly
                ? completionRows.filter((row) => !row.isComplete)
                : completionRows,
        [completionRows, outstandingOnly],
    );

    const selectedStudentReports = useMemo(() => {
        if (!form.student_id) {
            return [];
        }

        const selectedTeacherId = Number(form.teacher_id);

        return reports
            .filter((report) => String(report.student_id) === form.student_id)
            .filter((report) =>
                form.report_session_id
                    ? String(report.report_session_id ?? "") ===
                    form.report_session_id
                    : true,
            )
            .filter((report) => {
                if (!selectedTeacherId || Number.isNaN(selectedTeacherId)) {
                    return true;
                }

                const teacherId = (
                    report as StudentReport & {
                        teacher_id?: number | null;
                    }
                ).teacher_id;

                return teacherId == null || teacherId === selectedTeacherId;
            })
            .sort(
                (first, second) =>
                    new Date(second.updated_at ?? second.created_at).getTime() -
                    new Date(first.updated_at ?? first.created_at).getTime(),
            );
    }, [
        reports,
        form.student_id,
        form.report_session_id,
        form.teacher_id,
    ]);

    function updateFormField(field: keyof ReportFormState, value: string) {
        if (field === "report_text") {
            setQualityResult(null);
        }

        setForm((current) => {
            const next = {
                ...current,
                [field]: value,
            };

            if (field === "teacher_notes" || field === "work_covered") {
                next.generated_report_text = "";
            }

            return next;
        });
    }

    function resetFormForActiveSession() {
        setForm({
            ...initialFormState,
            report_session_id: activeSession ? String(activeSession.id) : "",
            academic_year: activeSession?.academic_year ?? "2026/27",
            term: activeSession?.term ?? "",
            title: activeSession?.title ?? "",
        });

        setEditingReportId(null);
        setQualityResult(null);
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
        setOutstandingOnly(false);

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

        setOutstandingOnly(false);

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


    function handleStudentChange(studentId: string) {
        const selectedTeacherId = Number(form.teacher_id);

        const existingReport = reports
            .filter(
                (report) =>
                    String(report.student_id) === studentId &&
                    (form.report_session_id
                        ? String(report.report_session_id ?? "") ===
                        form.report_session_id
                        : true),
            )
            .filter((report) => {
                if (!selectedTeacherId || Number.isNaN(selectedTeacherId)) {
                    return true;
                }

                const teacherId = (
                    report as StudentReport & {
                        teacher_id?: number | null;
                    }
                ).teacher_id;

                return teacherId == null || teacherId === selectedTeacherId;
            })
            .sort(
                (first, second) =>
                    new Date(second.updated_at ?? second.created_at).getTime() -
                    new Date(first.updated_at ?? first.created_at).getTime(),
            )[0];

        if (
            existingReport &&
            EDITABLE_REPORT_STATUSES.has(
                existingReport.status as TeacherFacingStatus,
            )
        ) {
            handleEditReport(existingReport);
            return;
        }

        setEditingReportId(null);
        setQualityResult(null);
        setError(null);
        setSuccessMessage(
            existingReport
                ? "This report is read-only at its current review stage."
                : null,
        );

        setForm((current) => ({
            ...current,
            student_id: studentId,
            teacher_notes: "",
            generated_report_text: "",
            report_text: "",
            exam_mark: "",
            attainment_grade: "",
            effort_grade: "",
            target_grade: "",
            next_steps: "",
            tutor_comment: "",
        }));
    }

    async function handleCheckQuality() {
        if (!form.report_text.trim()) {
            setError("Enter a final student comment first.");
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
        if (!form.work_covered.trim() && !form.teacher_notes.trim()) {
            setError("Enter work covered and/or teacher notes first.");
            return;
        }
        if (!form.teacher_id) {
            setError("Select a teacher first.");
            return;
        }

        if (!form.class_id) {
            setError("Select a class first.");
            return;
        }

        if (!form.student_id) {
            setError("Select a pupil first.");
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
                    ? `Work covered:\n${form.work_covered.trim()}`
                    : "",
                form.teacher_notes.trim()
                    ? `Teacher notes:\n${form.teacher_notes.trim()}`
                    : "",
            ]
                .filter(Boolean)
                .join("\n\n");

            const generated = await generateReportFromNotes(
                notesForGeneration,
                getFirstName(selectedStudent?.full_name),
                selectedClass?.subject_name ?? undefined,
                selectedClass?.name ?? undefined,
            );

            setForm((current) => {
                const currentFinal = current.report_text.trim();
                const previousGenerated =
                    current.generated_report_text.trim();
                const finalContainsManualWork =
                    currentFinal.length > 0 &&
                    currentFinal !== previousGenerated;

                return {
                    ...current,
                    generated_report_text: generated.generated_comment,
                    report_text: finalContainsManualWork
                        ? current.report_text
                        : generated.generated_comment,
                };
            });

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

    function resetStudentSpecificFields(nextStudentId = "") {
        setQualityResult(null);

        setForm((current) => ({
            ...current,
            student_id: nextStudentId,
            teacher_notes: "",
            generated_report_text: "",
            report_text: "",
            exam_mark: "",
            attainment_grade: "",
            effort_grade: "",
            target_grade: "",
            next_steps: "",
            tutor_comment: "",
        }));
    }

    function moveToNextStudent() {
        const currentIndex = students.findIndex(
            (student) => String(student.id) === form.student_id,
        );

        const nextStudent = students[currentIndex + 1];

        resetStudentSpecificFields(nextStudent ? String(nextStudent.id) : "");

        setSuccessMessage(
            nextStudent
                ? "Draft saved. Moved to the next student."
                : "Draft saved. No more students in this class.",
        );
    }

    function handleEditReport(report: StudentReport) {
        setForm((current) => ({
            ...current,
            student_id: String(report.student_id),
            report_session_id: report.report_session_id
                ? String(report.report_session_id)
                : current.report_session_id,
            title: report.title,
            work_covered: report.work_covered ?? "",
            teacher_notes: report.teacher_notes ?? "",
            generated_report_text: report.generated_report_text ?? "",
            report_text: report.report_text,
            exam_mark:
                (
                    report as StudentReport & {
                        exam_mark?: number | null;
                    }
                ).exam_mark?.toString() ?? "",
            attainment_grade:
                (
                    report as StudentReport & {
                        attainment_grade?: string | null;
                    }
                ).attainment_grade ??
                report.grade ??
                "",
            effort_grade:
                (
                    report as StudentReport & {
                        effort_grade?: string | null;
                    }
                ).effort_grade ?? "",
            target_grade:
                (
                    report as StudentReport & {
                        target_grade?: string | null;
                    }
                ).target_grade ?? "",
            next_steps:
                (
                    report as StudentReport & {
                        next_steps?: string | null;
                    }
                ).next_steps ?? "",
            tutor_comment:
                (
                    report as StudentReport & {
                        tutor_comment?: string | null;
                    }
                ).tutor_comment ?? "",
            academic_year: report.academic_year,
            term: report.term ?? "",
        }));

        setEditingReportId(report.id);
        setQualityResult(null);
        setError(null);
        setSuccessMessage(`Editing report #${report.id}`);

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
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

        if (!form.report_text.trim()) {
            setError("Final student comment is required.");
            return;
        }

        const reportSessionId = Number(form.report_session_id);

        if (!reportSessionId || Number.isNaN(reportSessionId)) {
            setError("Select a report session.");
            return;
        }

        const parsedExamMark = form.exam_mark.trim()
            ? Number(form.exam_mark)
            : null;

        if (
            parsedExamMark !== null &&
            (Number.isNaN(parsedExamMark) || parsedExamMark < 0)
        ) {
            setError("Exam mark must be a valid non-negative number.");
            return;
        }

        const selectedClass = classes.find(
            (classItem) => String(classItem.id) === form.class_id,
        );

        const payload: StudentReportCreateInput &
            Partial<{
                exam_mark: number | null;
                attainment_grade: string | null;
                effort_grade: string | null;
                target_grade: string | null;
                next_steps: string | null;
                tutor_comment: string | null;
                subject_name: string | null;
                checkpoint_name: string | null;
                teacher_id: number | null;
            }> = {
            student_id: studentId,
            teacher_id: form.teacher_id ? Number(form.teacher_id) : null,
            report_session_id: reportSessionId,
            title: form.title.trim(),
            work_covered: form.work_covered.trim() || null,
            teacher_notes: form.teacher_notes.trim() || null,
            generated_report_text:
                form.generated_report_text.trim() || null,
            report_text: form.report_text.trim(),
            grade: form.attainment_grade.trim() || null,
            attainment_grade: form.attainment_grade.trim() || null,
            effort_grade: form.effort_grade.trim() || null,
            target_grade: form.target_grade.trim() || null,
            exam_mark: parsedExamMark,
            next_steps: form.next_steps.trim() || null,
            tutor_comment: form.tutor_comment.trim() || null,
            subject_name: selectedClass?.subject_name ?? null,
            checkpoint_name: form.term.trim() || null,
            academic_year: form.academic_year.trim(),
            term: form.term.trim() || null,
        };

        try {
            setSaving(true);
            setError(null);
            setSuccessMessage(null);

            const saved =
                editingReportId !== null
                    ? await updateStudentReport(editingReportId, payload)
                    : await createStudentReport(payload);

            if (action === "submit") {
                const submitted = await submitStudentReport(saved.id);

                setReports((current) => upsertReport(current, submitted));
                setEditingReportId(null);
                setSuccessMessage("Report submitted for review.");
                return;
            }

            setReports((current) => upsertReport(current, saved));

            if (action === "next") {
                setEditingReportId(null);
                moveToNextStudent();
                return;
            }

            if (action === "close") {
                resetFormForActiveSession();
                setStudents([]);
                setSuccessMessage("Draft saved and closed.");
                return;
            }

            setSuccessMessage(
                editingReportId !== null
                    ? "Report changes saved."
                    : "Draft saved.",
            );
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

            if (editingReportId === reportId) {
                resetFormForActiveSession();
            }

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
        (!form.work_covered.trim() && !form.teacher_notes.trim());

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
                    className="w-fit rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-bold text-slate-700 hover:bg-slate-50"
                >
                    ← Back
                </button>
            </div>

            {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-base font-medium text-red-700">
                    {error}
                </div>
            )}

            {successMessage && (
                <div className="rounded-2xl border border-green-200 bg-green-50 p-4 text-base font-medium text-green-700">
                    {successMessage}
                </div>
            )}

            <section className="rounded-2xl border bg-white p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <h2 className="text-2xl font-bold text-slate-950">
                            Report Completion Overview
                        </h2>
                        <p className="mt-1 text-base text-slate-600">
                            Every pupil in the selected class appears here,
                            including pupils whose report has not been started.
                        </p>
                    </div>

                    <button
                        type="button"
                        disabled={!form.class_id}
                        onClick={() =>
                            setOutstandingOnly((current) => !current)
                        }
                        className="w-fit rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {outstandingOnly
                            ? "Show all pupils"
                            : "Show outstanding only"}
                    </button>
                </div>

                {!form.class_id ? (
                    <div className="mt-5 rounded-2xl border border-dashed bg-slate-50 p-6 text-base text-slate-500">
                        Select a teacher, class and report session to check
                        completion.
                    </div>
                ) : (
                    <>
                        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
                            {[
                                ["Pupils", completionSummary.total],
                                ["Written", completionSummary.completed],
                                ["Outstanding", completionSummary.outstanding],
                                ["Not started", completionSummary.notStarted],
                                ["Drafts", completionSummary.drafts],
                                ["Returned", completionSummary.returned],
                                ["Complete", `${completionSummary.percentage}%`],
                            ].map(([label, value]) => (
                                <div
                                    key={String(label)}
                                    className="rounded-2xl border bg-slate-50 p-4"
                                >
                                    <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                        {label}
                                    </p>
                                    <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                        {value}
                                    </p>
                                </div>
                            ))}
                        </div>

                        <div className="mt-5">
                            <div className="h-3 overflow-hidden rounded-full bg-slate-200">
                                <div
                                    className="h-full rounded-full bg-green-600 transition-all"
                                    style={{
                                        width: `${completionSummary.percentage}%`,
                                    }}
                                />
                            </div>
                            <p className="mt-2 text-sm font-semibold text-slate-600">
                                {completionSummary.outstanding === 0 &&
                                    completionSummary.total > 0
                                    ? "All reports have been written and submitted."
                                    : `${completionSummary.outstanding} report${completionSummary.outstanding === 1 ? "" : "s"} still require attention.`}
                            </p>
                        </div>

                        <div className="mt-5 overflow-x-auto rounded-2xl border">
                            <table className="min-w-full divide-y divide-slate-200 text-left">
                                <thead className="bg-slate-50">
                                    <tr>
                                        <th className="px-4 py-3 text-sm font-bold uppercase text-slate-500">
                                            Pupil
                                        </th>
                                        <th className="px-4 py-3 text-sm font-bold uppercase text-slate-500">
                                            Status
                                        </th>
                                        <th className="px-4 py-3 text-sm font-bold uppercase text-slate-500">
                                            Last updated
                                        </th>
                                        <th className="px-4 py-3 text-sm font-bold uppercase text-slate-500">
                                            Action
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 bg-white">
                                    {visibleCompletionRows.map((row) => (
                                        <tr key={row.student.id}>
                                            <td className="px-4 py-3 text-base font-semibold text-slate-900">
                                                {row.student.full_name}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span
                                                    className={`inline-flex rounded-full px-3 py-1 text-sm font-bold ${getStatusBadgeClass(
                                                        row.status,
                                                    )}`}
                                                >
                                                    {getStatusLabel(row.status)}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-base text-slate-600">
                                                {row.report
                                                    ? formatDate(
                                                        row.report.updated_at ??
                                                        row.report.created_at,
                                                    )
                                                    : "—"}
                                            </td>
                                            <td className="px-4 py-3">
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        if (
                                                            row.report &&
                                                            EDITABLE_REPORT_STATUSES.has(
                                                                row.status,
                                                            )
                                                        ) {
                                                            handleEditReport(
                                                                row.report,
                                                            );
                                                        } else {
                                                            handleStudentChange(
                                                                String(
                                                                    row.student
                                                                        .id,
                                                                ),
                                                            );
                                                        }
                                                    }}
                                                    className="font-bold text-blue-600 hover:text-blue-700"
                                                >
                                                    {row.status === "not_started"
                                                        ? "Write"
                                                        : EDITABLE_REPORT_STATUSES.has(
                                                            row.status,
                                                        )
                                                            ? row.status ===
                                                                "draft"
                                                                ? "Continue"
                                                                : "Correct"
                                                            : "View"}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <h2 className="text-xl font-bold text-slate-950">
                    {editingReportId === null
                        ? "Write Draft Report"
                        : `Edit Draft Report #${editingReportId}`}
                </h2>

                <form onSubmit={handleCreateReport} className="mt-6 grid gap-5">
                    <div className="grid gap-4 md:grid-cols-3">
                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
                                Teacher
                            </span>

                            <select
                                value={form.teacher_id}
                                onChange={(event) =>
                                    void handleTeacherChange(
                                        event.target.value,
                                    )
                                }
                                className="rounded-xl border px-3 py-2 text-base"
                            >
                                <option value="">
                                    Select teacher
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
                            <span className="text-base font-semibold text-slate-700">
                                Class
                            </span>

                            <select
                                value={form.class_id}
                                onChange={(event) =>
                                    void handleClassChange(event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-base"
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
                            <span className="text-base font-semibold text-slate-700">
                                Student
                            </span>

                            <select
                                value={form.student_id}
                                onChange={(event) =>
                                    handleStudentChange(event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-base"
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
                                        {(() => {
                                            const row = completionRows.find(
                                                (item) =>
                                                    item.student.id ===
                                                    student.id,
                                            );

                                            return row
                                                ? ` · ${getStatusLabel(
                                                    row.status,
                                                )}`
                                                : "";
                                        })()}
                                    </option>
                                ))}
                            </select>
                        </label>
                    </div>

                    <div className="grid gap-4 md:grid-cols-3">
                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
                                Report Session
                            </span>

                            <select
                                value={form.report_session_id}
                                onChange={(event) =>
                                    handleSessionChange(event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-base"
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
                            <span className="text-base font-semibold text-slate-700">
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
                                className="rounded-xl border px-3 py-2 text-base"
                                placeholder="2026/27"
                            />
                        </label>

                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
                                Term
                            </span>

                            <input
                                value={form.term}
                                onChange={(event) =>
                                    updateFormField("term", event.target.value)
                                }
                                className="rounded-xl border px-3 py-2 text-base"
                                placeholder="Autumn"
                            />
                        </label>
                    </div>

                    <label className="grid gap-2">
                        <span className="text-base font-semibold text-slate-700">
                            Report Title
                        </span>

                        <input
                            value={form.title}
                            onChange={(event) =>
                                updateFormField("title", event.target.value)
                            }
                            className="rounded-xl border px-3 py-2 text-base"
                            placeholder="Autumn Progress Report"
                        />
                    </label>

                    {activeSession?.include_work_covered && (
                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
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
                                className="min-h-24 rounded-xl border px-3 py-2 text-base"
                                placeholder="Write one or two lines about the work covered by the whole class."
                            />
                        </label>
                    )}

                    {(!activeSession ||
                        activeSession.include_student_comment) && (
                            <div className="grid gap-5">
                                <section className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                                    <div className="flex items-start gap-3">
                                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-base font-bold text-white">
                                            1
                                        </span>

                                        <div>
                                            <h3 className="text-xl font-bold text-slate-950">
                                                Add Teacher Notes
                                            </h3>

                                            <p className="mt-1 text-base text-slate-600">
                                                Enter concise, student-specific evidence such as strengths,
                                                progress, participation and areas for improvement.
                                            </p>
                                        </div>
                                    </div>

                                    <label className="mt-4 grid gap-2">
                                        <span className="text-base font-semibold text-slate-700">
                                            Teacher Notes
                                        </span>

                                        <textarea
                                            value={form.teacher_notes}
                                            onChange={(event) =>
                                                updateFormField(
                                                    "teacher_notes",
                                                    event.target.value,
                                                )
                                            }
                                            className="min-h-36 rounded-xl border border-slate-300 bg-white px-4 py-3 text-base leading-7"
                                            placeholder="Example: Amy contributes confidently in practical work, completes tasks carefully and should now include more precise scientific detail in written explanations."
                                        />
                                    </label>
                                </section>

                                <section className="rounded-2xl border-2 border-purple-200 bg-purple-50 p-5">
                                    <div className="flex items-start gap-3">
                                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-purple-600 text-base font-bold text-white">
                                            2
                                        </span>

                                        <div>
                                            <h3 className="text-xl font-bold text-slate-950">
                                                Generate or Write the Report
                                            </h3>

                                            <p className="mt-1 text-base text-slate-600">
                                                Generate a draft from the teacher notes, or skip generation
                                                and write the report directly in the editor below.
                                            </p>
                                        </div>
                                    </div>

                                    <div className="mt-5 flex flex-wrap gap-3">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                void handleGenerateFromNotes()
                                            }
                                            disabled={generationDisabled}
                                            className="rounded-xl bg-purple-600 px-5 py-3 text-base font-bold text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {generatingFromNotes
                                                ? "Generating Report..."
                                                : "Generate Report From Notes"}
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() =>
                                                void handleCheckQuality()

                                            }
                                            disabled={
                                                checkingQuality ||
                                                !form.report_text.trim()
                                            }
                                            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-base font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            {checkingQuality
                                                ? "Checking Report..."
                                                : "Check UK Grammar & Spelling"}
                                        </button>
                                    </div>
                                </section>

                                {form.generated_report_text && (
                                    <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
                                        <div className="flex items-start gap-3">
                                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-base font-bold text-white">
                                                3
                                            </span>

                                            <div className="min-w-0">
                                                <h3 className="text-xl font-bold text-slate-950">
                                                    Generated Draft
                                                </h3>

                                                <p className="mt-1 text-base text-slate-600">
                                                    Review the generated wording, then edit the final report
                                                    below before saving.
                                                </p>
                                            </div>
                                        </div>

                                        <p className="mt-4 whitespace-pre-line rounded-xl border border-blue-200 bg-white p-4 text-base leading-7 text-slate-700">
                                            {form.generated_report_text}
                                        </p>
                                    </section>
                                )}

                                <section className="rounded-2xl border-2 border-blue-300 bg-white p-5">
                                    <div className="flex items-start gap-3">
                                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-base font-bold text-white">
                                            {form.generated_report_text ? "4" : "3"}
                                        </span>

                                        <div>
                                            <h3 className="text-xl font-bold text-slate-950">
                                                Write or Edit Final Student Report
                                            </h3>

                                            <p className="mt-1 text-base text-slate-600">
                                                This is the report that will be saved and submitted for review.
                                            </p>
                                        </div>
                                    </div>

                                    <label className="mt-4 grid gap-2">
                                        <span className="text-base font-semibold text-slate-700">
                                            Final Student Report
                                        </span>

                                        <textarea
                                            value={form.report_text}
                                            onChange={(event) =>
                                                updateFormField(
                                                    "report_text",
                                                    event.target.value,
                                                )
                                            }
                                            className="min-h-72 rounded-xl border-2 border-blue-300 bg-white px-4 py-3 text-base leading-7 focus:border-blue-600 focus:outline-none"
                                            placeholder="Generate a draft using the button above, or write the final student report directly here."
                                        />
                                    </label>
                                </section>

                                {qualityResult && (
                                    <section className="rounded-2xl border border-green-200 bg-green-50 p-5">
                                        <h3 className="text-xl font-bold text-slate-950">
                                            Report Quality Review
                                        </h3>

                                        <p className="mt-3 whitespace-pre-line text-base leading-7 text-slate-700">
                                            {qualityResult.corrected_comment}
                                        </p>

                                        {qualityResult.issues.length > 0 && (
                                            <ul className="mt-3 list-disc pl-5 text-base text-slate-600">
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
                                            className="mt-4 rounded-xl bg-green-600 px-5 py-3 text-base font-bold text-white hover:bg-green-700"
                                        >
                                            Apply Suggestions
                                        </button>
                                    </section>
                                )}
                            </div>
                        )}

                    <div className="grid gap-4 md:grid-cols-3">
                        {activeSession?.include_exam_mark && (
                            <label className="grid gap-2">
                                <span className="text-base font-semibold text-slate-700">
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
                                    className="rounded-xl border px-3 py-2 text-base"
                                    placeholder="e.g. 72%"
                                />
                            </label>
                        )}

                        {activeSession?.include_attainment_grade && (
                            <label className="grid gap-2">
                                <span className="text-base font-semibold text-slate-700">
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
                                    className="rounded-xl border px-3 py-2 text-base"
                                    placeholder="e.g. A"
                                />
                            </label>
                        )}

                        {activeSession?.include_effort_grade && (
                            <label className="grid gap-2">
                                <span className="text-base font-semibold text-slate-700">
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
                                    className="rounded-xl border px-3 py-2 text-base"
                                    placeholder="e.g. Excellent"
                                />
                            </label>
                        )}
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                        {activeSession?.include_target_grade && (
                            <label className="grid gap-2">
                                <span className="text-base font-semibold text-slate-700">
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
                                    className="rounded-xl border px-3 py-2 text-base"
                                    placeholder="e.g. A*"
                                />
                            </label>
                        )}

                        {activeSession?.include_next_steps && (
                            <label className="grid gap-2">
                                <span className="text-base font-semibold text-slate-700">
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
                                    className="rounded-xl border px-3 py-2 text-base"
                                    placeholder="What should the student focus on next?"
                                />
                            </label>
                        )}
                    </div>

                    {activeSession?.include_tutor_comment && (
                        <label className="grid gap-2">
                            <span className="text-base font-semibold text-slate-700">
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
                                className="min-h-28 rounded-xl border px-3 py-2 text-base"
                                placeholder="Write tutor comment..."
                            />
                        </label>
                    )}

                    <section className="sticky bottom-0 z-20 -mx-6 rounded-t-2xl border-t border-slate-200 bg-white/95 px-6 py-4 shadow-[0_-10px_30px_rgba(15,23,42,0.12)] backdrop-blur">
                        <div className="mb-3 flex items-center gap-3">
                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-base font-bold text-white">
                                {form.generated_report_text ? "5" : "4"}
                            </span>

                            <div>
                                <h3 className="text-lg font-bold text-slate-950">
                                    Save or Submit
                                </h3>

                                <p className="text-sm text-slate-600">
                                    Save your progress, move to the next student, or submit the finished report for review.
                                </p>
                            </div>
                        </div>

                        <div className="flex flex-wrap gap-3">
                            <button
                                type="submit"
                                disabled={saving}
                                className="rounded-xl bg-blue-600 px-5 py-2 text-base font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                {saving
                                    ? "Saving..."
                                    : editingReportId === null
                                        ? "Save Draft"
                                        : "Save Changes"}
                            </button>

                            <button
                                type="button"
                                disabled={saving}
                                onClick={() => void saveReport("submit")}
                                className="rounded-xl bg-purple-600 px-5 py-2 text-base font-bold text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                Submit For Review
                            </button>

                            <button
                                type="button"
                                disabled={saving}
                                onClick={() => void saveReport("next")}
                                className="rounded-xl bg-slate-900 px-5 py-2 text-base font-bold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                Save & Next Student
                            </button>

                            <button
                                type="button"
                                disabled={saving}
                                onClick={() => void saveReport("close")}
                                className="rounded-xl border border-slate-300 bg-white px-5 py-2 text-base font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                Save & Close
                            </button>

                            {editingReportId !== null && (
                                <button
                                    type="button"
                                    disabled={saving}
                                    onClick={() => {
                                        resetFormForActiveSession();
                                        setSuccessMessage("Editing cancelled.");
                                    }}
                                    className="rounded-xl border border-red-300 px-5 py-2 text-base font-bold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    Cancel Editing
                                </button>
                            )}
                        </div>
                    </section>
                </form>
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <h2 className="text-xl font-bold text-slate-950">
                    Existing Reports
                </h2>

                {loading ? (
                    <p className="mt-4 text-base text-slate-500">
                        Loading reports...
                    </p>
                ) : !form.student_id ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                        Select a class and pupil to view or edit reports.
                    </div>
                ) : selectedStudentReports.length === 0 ? (
                    <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                        No reports have been created for this pupil in the selected session.
                    </div>
                ) : (
                    <div className="mt-6 grid gap-4">
                        {selectedStudentReports.map((report) => (
                            <article
                                key={report.id}
                                className="rounded-2xl border bg-slate-50 p-5"
                            >
                                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-950">
                                            {report.title}
                                        </h3>

                                        <p className="mt-1 text-base text-slate-500">
                                            {students.find(
                                                (student) =>
                                                    student.id === report.student_id,
                                            )?.full_name ?? "Selected pupil"}{" "}
                                            · {report.academic_year}
                                            {report.term
                                                ? ` · ${report.term}`
                                                : ""}
                                        </p>
                                    </div>

                                    <span
                                        className={`rounded-full px-3 py-1 text-base font-bold ${getStatusBadgeClass(
                                            report.status,
                                        )}`}
                                    >
                                        {getStatusLabel(report.status)}
                                    </span>
                                </div>

                                {report.work_covered && (
                                    <div className="mt-4">
                                        <p className="text-sm font-bold uppercase text-slate-500">
                                            Work Covered
                                        </p>
                                        <p className="mt-1 whitespace-pre-line text-base leading-7 text-slate-700">
                                            {report.work_covered}
                                        </p>
                                    </div>
                                )}

                                {report.teacher_notes && (
                                    <div className="mt-4">
                                        <p className="text-sm font-bold uppercase text-slate-500">
                                            Teacher Notes
                                        </p>
                                        <p className="mt-1 whitespace-pre-line text-base leading-7 text-slate-700">
                                            {report.teacher_notes}
                                        </p>
                                    </div>
                                )}

                                {report.generated_report_text && (
                                    <div className="mt-4 rounded-xl border bg-white p-4">
                                        <p className="text-sm font-bold uppercase text-slate-500">
                                            Generated Draft
                                        </p>
                                        <p className="mt-1 whitespace-pre-line text-base leading-7 text-slate-600">
                                            {report.generated_report_text}
                                        </p>
                                    </div>
                                )}

                                <div className="mt-4">
                                    <p className="text-sm font-bold uppercase text-slate-500">
                                        Final Student Comment
                                    </p>
                                    <p className="mt-1 whitespace-pre-line text-base leading-7 text-slate-700">
                                        {report.report_text}
                                    </p>
                                </div>

                                {report.review_comments && (
                                    <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                                        <p className="text-sm font-bold uppercase text-amber-800">
                                            Review Feedback
                                        </p>
                                        <p className="mt-1 whitespace-pre-line text-base leading-7 text-amber-900">
                                            {report.review_comments}
                                        </p>
                                    </div>
                                )}

                                <div className="mt-4 flex flex-col gap-3 border-t pt-4 text-base text-slate-500 md:flex-row md:items-center md:justify-between">
                                    <span>
                                        Created {formatDate(report.created_at)}
                                    </span>

                                    {EDITABLE_REPORT_STATUSES.has(
                                        report.status as TeacherFacingStatus,
                                    ) ? (
                                        <div className="flex gap-4">
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    handleEditReport(report)
                                                }
                                                className="w-fit font-semibold text-blue-600 hover:text-blue-700"
                                            >
                                                Edit
                                            </button>

                                            <button
                                                type="button"
                                                onClick={() =>
                                                    void handleDeleteReport(
                                                        report.id,
                                                    )
                                                }
                                                className="w-fit font-semibold text-red-600 hover:text-red-700"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    ) : (
                                        <span className="font-medium text-slate-600">
                                            {report.status === "submitted"
                                                ? "Awaiting review"
                                                : report.status === "tutor_review"
                                                    ? "Under tutor review"
                                                    : report.status ===
                                                        "ready_for_smt"
                                                        ? "Awaiting SMT review"
                                                        : report.status ===
                                                            "approved"
                                                            ? "Approved and awaiting publication"
                                                            : report.status ===
                                                                "published"
                                                                ? "Published"
                                                                : getStatusLabel(
                                                                    report.status,
                                                                )}
                                        </span>
                                    )}
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </section>
        </main>
    );
}
