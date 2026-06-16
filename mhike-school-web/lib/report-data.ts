import { apiGet } from "@/lib/api";

export type ReportTeacher = {
    id: number;
    full_name: string;
    email: string | null;
};

export type ReportClass = {
    id: number;
    name: string;
    subject_name?: string | null;
    teacher_id?: number | null;
};

export type ReportStudent = {
    id: number;
    full_name: string;
    email: string | null;
};

export async function listReportTeachers(): Promise<ReportTeacher[]> {
    return apiGet<ReportTeacher[]>("/school-users/teachers");
}

export async function listReportClasses(
    teacherId?: number | string | null,
): Promise<ReportClass[]> {
    const query = teacherId ? `?teacher_id=${teacherId}` : "";

    return apiGet<ReportClass[]>(`/classes${query}`);
}

export async function listReportClassStudents(
    classId: number | string,
): Promise<ReportStudent[]> {
    return apiGet<ReportStudent[]>(`/classes/${classId}/students`);
}