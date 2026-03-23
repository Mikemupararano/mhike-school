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
    teacher_name?: string | null;
    published: boolean;
};

export type AdminUsersResponse = {
    items: AdminUserOut[];
    total: number;
    skip: number;
    limit: number;
};

export type AdminCoursesResponse = {
    items: AdminCourseOut[];
    total: number;
    skip: number;
    limit: number;
};

export async function getAdminStats(token: string) {
    return apiGet<AdminStatsOut>("/admin/stats", token);
}

export async function getAdminUsers(
    token: string,
    params?: {
        role?: string;
        search?: string;
        skip?: number;
        limit?: number;
    }
) {
    const qs = new URLSearchParams();

    if (params?.role && params.role !== "all") qs.set("role", params.role);
    if (params?.search) qs.set("search", params.search);
    if (params?.skip !== undefined) qs.set("skip", String(params.skip));
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));

    const query = qs.toString();

    return apiGet<AdminUsersResponse>(
        `/admin/users${query ? `?${query}` : ""}`,
        token
    );
}

export async function getAdminCourses(
    token: string,
    params?: {
        search?: string;
        skip?: number;
        limit?: number;
    }
) {
    const qs = new URLSearchParams();

    if (params?.search) qs.set("search", params.search);
    if (params?.skip !== undefined) qs.set("skip", String(params.skip));
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));

    const query = qs.toString();

    return apiGet<AdminCoursesResponse>(
        `/admin/courses${query ? `?${query}` : ""}`,
        token
    );
}

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
    return apiPost<AdminUserOut>(
        `/admin/users/${userId}/active`,
        { is_active },
        token
    );
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