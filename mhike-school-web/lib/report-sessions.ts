import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";

export type ReportSession = {
    id: number;
    school_id: number;
    title: string;
    academic_year: string;
    term: string | null;
    active: boolean;
    include_work_covered: boolean;
    include_student_comment: boolean;
    include_exam_mark: boolean;
    include_attainment_grade: boolean;
    include_effort_grade: boolean;
    include_target_grade: boolean;
    include_next_steps: boolean;
    include_tutor_comment: boolean;
    created_at: string;
};

export type ReportSessionCreateInput = Omit<
    ReportSession,
    "id" | "school_id" | "created_at"
>;

export type ReportSessionUpdateInput =
    Partial<ReportSessionCreateInput>;

export async function listReportSessions(): Promise<
    ReportSession[]
> {
    return apiGet<ReportSession[]>("/report-sessions/");
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