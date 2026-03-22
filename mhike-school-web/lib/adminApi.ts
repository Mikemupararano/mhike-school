import { apiGet, apiPost } from "@/lib/api";

export type AdminStatsOut = {
    total_users: number;
    total_students: number;
    total_teachers: number;
    total_admins: number;
    total_courses: number;
    published_courses: number;
    total_enrollments: number;
};

export type AdminUserOut = {
    id: number;
    full_name?: string | null;
    email: string;
    role: "student" | "teacher" | "admin" | string;
    is_active?: boolean;
};

export type AdminCourseOut = {
    id: number;
    title: string;
    description?: string | null;
    teacher_id: number;
    published: boolean;
};

export async function getAdminStats(token: string) {
    return apiGet<AdminStatsOut>("/admin/stats", token);
}

export async function getAdminUsers(token: string) {
    return apiGet<AdminUserOut[]>("/admin/users", token);
}

export async function getAdminCourses(token: string) {
    return apiGet<AdminCourseOut[]>("/admin/courses", token);
}

/**
 * Admin actions.
 * Only call these if the matching backend endpoints exist.
 */
export async function updateUserRole(
    token: string,
    userId: number,
    role: "student" | "teacher" | "admin"
) {
    return apiPost<AdminUserOut>(`/admin/users/${userId}/role`, { role }, token);
}

export async function toggleUserActive(
    token: string,
    userId: number,
    is_active: boolean
) {
    return apiPost<AdminUserOut>(`/admin/users/${userId}/active`, { is_active }, token);
}

export async function setCoursePublished(
    token: string,
    courseId: number,
    published: boolean
) {
    return apiPost<AdminCourseOut>(
        `/admin/courses/${courseId}/publish`,
        { published },
        token
    );
}

export async function deleteCourseAdmin(token: string, courseId: number) {
    return apiPost<{ success: boolean }>(
        `/admin/courses/${courseId}/delete`,
        {},
        token
    );
}