import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";

export type StudentReport = {
    id: number;
    school_id: number;
    student_id: number;
    teacher_id: number | null;
    report_session_id: number | null;

    title: string;
    report_text: string;
    grade: string | null;

    work_covered: string | null;
    teacher_notes: string | null;
    generated_report_text: string | null;

    academic_year: string;
    term: string | null;

    status: string;

    published: boolean;
    published_at: string | null;
    published_by_id: number | null;

    submitted_at: string | null;
    submitted_by_id: number | null;

    reviewed_at: string | null;
    reviewed_by_id: number | null;
    review_comments: string | null;

    created_at: string;
    updated_at: string;
};

export type StudentReportCreateInput = {
    student_id: number;
    report_session_id?: number | null;

    title: string;
    report_text: string;

    grade?: string | null;

    work_covered?: string | null;
    teacher_notes?: string | null;
    generated_report_text?: string | null;

    academic_year: string;
    term?: string | null;
};

export type StudentReportUpdateInput = {
    title?: string;
    report_text?: string;

    grade?: string | null;

    work_covered?: string | null;
    teacher_notes?: string | null;
    generated_report_text?: string | null;

    academic_year?: string;
    term?: string | null;

    report_session_id?: number | null;
};

export type StudentReportReviewDashboard = {
    draft: number;
    submitted: number;
    approved: number;
    published: number;
};

export type ReviewQueueFilters = {
    teacher_id?: number;
    student_id?: number;
    report_session_id?: number;
    limit?: number;
    offset?: number;
};

export type ReturnStudentReportInput = {
    review_comments?: string | null;
};

export async function listStudentReports(): Promise<StudentReport[]> {
    return apiGet<StudentReport[]>("/student-reports");
}

export async function listReportsForStudent(
    studentId: number,
): Promise<StudentReport[]> {
    return apiGet<StudentReport[]>(
        `/student-reports/student/${studentId}`,
    );
}

export async function listParentStudentReports(): Promise<StudentReport[]> {
    return apiGet<StudentReport[]>("/student-reports/parent");
}

export async function createStudentReport(
    payload: StudentReportCreateInput,
): Promise<StudentReport> {
    return apiPost<StudentReport>("/student-reports", payload);
}

export async function updateStudentReport(
    reportId: number,
    payload: StudentReportUpdateInput,
): Promise<StudentReport> {
    return apiPatch<StudentReport>(
        `/student-reports/${reportId}`,
        payload,
    );
}

export async function deleteStudentReport(
    reportId: number,
): Promise<void> {
    return apiDelete<void>(`/student-reports/${reportId}`);
}

export async function getStudentReport(
    reportId: number,
): Promise<StudentReport> {
    return apiGet<StudentReport>(`/student-reports/${reportId}`);
}

export async function submitStudentReport(
    reportId: number,
): Promise<StudentReport> {
    return apiPost<StudentReport>(
        `/student-reports/${reportId}/submit`,
        {},
    );
}

export async function approveStudentReport(
    reportId: number,
): Promise<StudentReport> {
    return apiPost<StudentReport>(
        `/student-reports/${reportId}/approve`,
        {},
    );
}

export async function returnStudentReport(
    reportId: number,
    payload: ReturnStudentReportInput = {},
): Promise<StudentReport> {
    return apiPost<StudentReport>(
        `/student-reports/${reportId}/return`,
        payload,
    );
}

export async function getStudentReportReviewDashboard(): Promise<StudentReportReviewDashboard> {
    return apiGet<StudentReportReviewDashboard>(
        "/student-reports/review-dashboard",
    );
}

export async function listStudentReportReviewQueue(
    filters: ReviewQueueFilters = {},
): Promise<StudentReport[]> {
    const params = new URLSearchParams();

    if (filters.teacher_id !== undefined) {
        params.set("teacher_id", String(filters.teacher_id));
    }

    if (filters.student_id !== undefined) {
        params.set("student_id", String(filters.student_id));
    }

    if (filters.report_session_id !== undefined) {
        params.set(
            "report_session_id",
            String(filters.report_session_id),
        );
    }

    if (filters.limit !== undefined) {
        params.set("limit", String(filters.limit));
    }

    if (filters.offset !== undefined) {
        params.set("offset", String(filters.offset));
    }

    const query = params.toString();

    return apiGet<StudentReport[]>(
        `/student-reports/review-queue${query ? `?${query}` : ""}`,
    );
}