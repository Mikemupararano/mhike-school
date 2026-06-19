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

    reviewed_at: string | null;
    reviewed_by_id: number | null;

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
    status?: string;
    published?: boolean;
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