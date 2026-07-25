import {
    apiDelete,
    apiGet,
    apiGetBlob,
    apiPatch,
    apiPost,
} from "@/lib/api";

export type ReportSessionReportingMode =
    | "grade_card"
    | "full_report"
    | "both";

export type ReportSession = {
    id: number;
    school_id: number;

    title: string;
    academic_year: string;
    term: string | null;
    checkpoint_name: string | null;
    active: boolean;

    reporting_mode: ReportSessionReportingMode;
    display_order: number;
    enable_report_generation: boolean;

    include_work_covered: boolean;
    include_student_comment: boolean;
    include_exam_mark: boolean;
    include_attainment_grade: boolean;
    include_effort_grade: boolean;
    include_target_grade: boolean;
    include_next_steps: boolean;
    include_tutor_comment: boolean;

    require_student_comment: boolean;
    require_exam_mark: boolean;
    require_attainment_grade: boolean;
    require_effort_grade: boolean;
    require_target_grade: boolean;
    require_next_steps: boolean;
    require_tutor_comment: boolean;

    allow_teacher_edit_after_submission: boolean;
    allow_smt_edit_after_approval: boolean;

    show_previous_grades: boolean;
    show_previous_tutor_comments: boolean;
    show_progress_journey: boolean;

    copied_from_session_id: number | null;

    draft_count?: number;
    submitted_count?: number;
    tutor_review_count?: number;
    ready_for_smt_count?: number;
    approved_count?: number;
    published_count?: number;
    total_reports?: number;

    created_at: string;
    updated_at?: string;
};

export type ReportSessionCreateInput = {
    title: string;
    academic_year: string;
    term?: string | null;
    checkpoint_name?: string | null;
    active?: boolean;

    reporting_mode?: ReportSessionReportingMode;
    display_order?: number;
    enable_report_generation?: boolean;

    include_work_covered?: boolean;
    include_student_comment?: boolean;
    include_exam_mark?: boolean;
    include_attainment_grade?: boolean;
    include_effort_grade?: boolean;
    include_target_grade?: boolean;
    include_next_steps?: boolean;
    include_tutor_comment?: boolean;

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

export type ReportSessionUpdateInput =
    Partial<ReportSessionCreateInput>;

export type ReportSessionStatistics = {
    report_session_id: number;
    total_reports: number;
    draft_count: number;
    submitted_count: number;
    tutor_review_count: number;
    ready_for_smt_count: number;
    approved_count: number;
    published_count: number;
};

export async function listReportSessions(): Promise<
    ReportSession[]
> {
    return apiGet<ReportSession[]>("/report-sessions/");
}

export async function getReportSession(
    sessionId: number,
): Promise<ReportSession> {
    return apiGet<ReportSession>(
        `/report-sessions/${sessionId}`,
    );
}

export async function createReportSession(
    payload: ReportSessionCreateInput,
): Promise<ReportSession> {
    return apiPost<ReportSession>(
        "/report-sessions/",
        payload,
    );
}

export async function updateReportSession(
    sessionId: number,
    payload: ReportSessionUpdateInput,
): Promise<ReportSession> {
    return apiPatch<ReportSession>(
        `/report-sessions/${sessionId}`,
        payload,
    );
}

export async function deleteReportSession(
    sessionId: number,
): Promise<void> {
    return apiDelete<void>(
        `/report-sessions/${sessionId}`,
    );
}

export async function activateReportSession(
    sessionId: number,
): Promise<ReportSession> {
    return apiPost<ReportSession>(
        `/report-sessions/${sessionId}/activate`,
        {},
    );
}

export async function duplicateReportSession(
    sessionId: number,
    payload?: ReportSessionUpdateInput,
): Promise<ReportSession> {
    return apiPost<ReportSession>(
        `/report-sessions/${sessionId}/duplicate`,
        payload ?? {},
    );
}

export async function getReportSessionStatistics(
    sessionId: number,
): Promise<ReportSessionStatistics> {
    return apiGet<ReportSessionStatistics>(
        `/report-sessions/${sessionId}/statistics`,
    );
}

export async function exportReportSessionZip(
    reportSessionId: number,
): Promise<Blob> {
    return apiGetBlob(
        `/student-reports/export-session/${reportSessionId}`,
    );
}