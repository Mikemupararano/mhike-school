import { apiGet } from "@/lib/api";

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

export async function getParentReports(): Promise<StudentReport[]> {
    return apiGet<StudentReport[]>("/student-reports/parent");
}