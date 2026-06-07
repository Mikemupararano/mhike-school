import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";

export type StudentReport = {
    id: number;
    school_id: number;
    student_id: number;
    teacher_id: number | null;
    title: string;
    report_text: string;
    grade: string | null;
    academic_year: string;
    term: string | null;
    created_at: string;
    updated_at: string;
};

export type StudentReportCreateInput = {
    student_id: number;
    teacher_id?: number | null;
    title: string;
    report_text: string;
    grade?: string | null;
    academic_year: string;
    term?: string | null;
};

export type StudentReportUpdateInput = {
    teacher_id?: number | null;
    title?: string;
    report_text?: string;
    grade?: string | null;
    academic_year?: string;
    term?: string | null;
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