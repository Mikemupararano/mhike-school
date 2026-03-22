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

export async function getMyCourses(token: string) {
    return apiGet<CourseOut[]>("/courses/me", token);
}

export async function createCourse(
    token: string,
    body: { title: string; description?: string | null }
) {
    return apiPost<CourseOut>("/courses", body, token);
}

export async function publishCourse(token: string, courseId: number) {
    return apiPost<CourseOut>(`/courses/${courseId}/publish`, {}, token);
}

export async function listModules(courseId: number, token?: string) {
    return apiGet<ModuleOut[]>(`/courses/${courseId}/modules`, token);
}

export async function createModule(
    token: string,
    courseId: number,
    body: { title: string; order: number }
) {
    return apiPost<ModuleOut>(`/courses/${courseId}/modules`, body, token);
}

export async function listLessons(moduleId: number, token?: string) {
    return apiGet<LessonOut[]>(`/modules/${moduleId}/lessons`, token);
}

export async function createLesson(
    token: string,
    moduleId: number,
    body: {
        title: string;
        content_type: string;
        content?: string | null;
        order: number;
    }
) {
    return apiPost<LessonOut>(`/modules/${moduleId}/lessons`, body, token);
}