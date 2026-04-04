import { apiGet, apiPost } from "@/lib/api";

export type AdminStatsOut = {
    scope?: "platform" | "school";
    school_id?: number | null;
    total_users: number;
    total_students: number;
    total_teachers: number;
    total_admins: number;
    total_courses: number;
    published_courses: number;
    draft_courses?: number;
    total_enrollments: number;
    published_rate?: number;
    recent_users?: Array<{
        id: number;
        full_name?: string | null;
        email: string;
        role: "student" | "teacher" | "admin" | "platform_admin" | string;
        school_id?: number | null;
        is_active?: boolean;
        created_at?: string;
    }>;
    recent_courses?: Array<{
        id: number;
        title: string;
        description?: string | null;
        teacher_id: number;
        school_id?: number | null;
        published: boolean;
    }>;
};

export type PlatformSchoolSummaryOut = {
    id: number;
    name: string;
    total_users: number;
    total_students: number;
    total_teachers: number;
    total_courses: number;
};

export type AdminUserOut = {
    id: number;
    full_name?: string | null;
    email: string;
    role: "student" | "teacher" | "admin" | "platform_admin" | string;
    school_id?: number | null;
    school_name?: string | null;
    is_active?: boolean;
};

export type AdminCourseOut = {
    id: number;
    title: string;
    description?: string | null;
    teacher_id: number;
    teacher_name?: string | null;
    school_id?: number | null;
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
    return apiGet<AdminStatsOut>("/platform-admin/dashboard", token);
}

export async function getPlatformSchools(
    token: string,
    params?: {
        search?: string;
    }
) {
    const qs = new URLSearchParams();

    if (params?.search) qs.set("search", params.search);

    const query = qs.toString();

    return apiGet<PlatformSchoolSummaryOut[]>(
        `/platform-admin/schools${query ? `?${query}` : ""}`,
        token
    );
}

export async function getAdminUsers(
    token: string,
    params?: {
        school_id?: number;
        role?: string;
        search?: string;
        skip?: number;
        limit?: number;
    }
) {
    const qs = new URLSearchParams();

    if (params?.school_id !== undefined) {
        qs.set("school_id", String(params.school_id));
    }
    if (params?.role && params.role !== "all") {
        qs.set("role", params.role);
    }
    if (params?.search) {
        qs.set("search", params.search);
    }
    if (params?.skip !== undefined) {
        qs.set("skip", String(params.skip));
    }
    if (params?.limit !== undefined) {
        qs.set("limit", String(params.limit));
    }

    const query = qs.toString();

    return apiGet<AdminUsersResponse>(
        `/platform-admin/users${query ? `?${query}` : ""}`,
        token
    );
}

export async function getAdminCourses(
    token: string,
    params?: {
        school_id?: number;
        search?: string;
        skip?: number;
        limit?: number;
    }
) {
    const qs = new URLSearchParams();

    if (params?.school_id !== undefined) {
        qs.set("school_id", String(params.school_id));
    }
    if (params?.search) {
        qs.set("search", params.search);
    }
    if (params?.skip !== undefined) {
        qs.set("skip", String(params.skip));
    }
    if (params?.limit !== undefined) {
        qs.set("limit", String(params.limit));
    }

    const query = qs.toString();

    return apiGet<AdminCoursesResponse>(
        `/platform-admin/courses${query ? `?${query}` : ""}`,
        token
    );
}

export async function updateUserRole(
    token: string,
    userId: number,
    role: "student" | "teacher" | "admin"
) {
    return apiPost<AdminUserOut>(
        `/platform-admin/users/${userId}/role`,
        { role },
        token
    );
}

export async function toggleUserActive(
    token: string,
    userId: number,
    is_active: boolean
) {
    return apiPost<AdminUserOut>(
        `/platform-admin/users/${userId}/active`,
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
        `/platform-admin/courses/${courseId}/publish`,
        { published },
        token
    );
}

export async function deleteCourseAdmin(token: string, courseId: number) {
    return apiPost<{ success: boolean }>(
        `/platform-admin/courses/${courseId}/delete`,
        {},
        token
    );
}