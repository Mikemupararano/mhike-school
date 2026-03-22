import { apiGet, apiPost } from "@/lib/api";

export type CourseOut = {
    id: number;
    title: string;
    description?: string | null;
    teacher_id: number;
    published: boolean;
};

export type ModuleOut = {
    id: number;
    course_id: number;
    title: string;
    order: number;
};

export type LessonOut = {
    id: number;
    module_id: number;
    title: string;
    content_type: string;
    content?: string | null;
    order: number;
};

export type EnrollmentOut = {
    id: number;
    course_id: number;
    student_id: number;
};

export async function getCourse(courseId: number, token?: string) {
    return apiGet<CourseOut>(`/courses/${courseId}`, token);
}

export async function listModules(courseId: number, token?: string) {
    return apiGet<ModuleOut[]>(`/courses/${courseId}/modules`, token);
}

export async function listLessons(moduleId: number, token?: string) {
    return apiGet<LessonOut[]>(`/modules/${moduleId}/lessons`, token);
}

export async function enrollInCourse(token: string, courseId: number) {
    return apiPost<EnrollmentOut>(`/courses/${courseId}/enroll`, {}, token);
}