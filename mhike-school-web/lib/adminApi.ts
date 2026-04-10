import { apiGet, apiPost } from "@/lib/api";

const PLATFORM_ADMIN_BASE = "/platform-admin";

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

type GetPlatformSchoolsParams = {
    search?: string;
};

type GetAdminUsersParams = {
    school_id?: number;
    role?: string;
    search?: string;
    skip?: number;
    limit?: number;
};

type GetAdminCoursesParams = {
    school_id?: number;
    search?: string;
    skip?: number;
    limit?: number;
};

function buildQuery(
    params?: Record<string, string | number | undefined | null>
): string {
    const qs = new URLSearchParams();

    if (!params) return "";

    Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") return;
        qs.set(key, String(value));
    });

    const query = qs.toString();
    return query ? `?${query}` : "";
}

export async function getAdminStats(token: string) {
    return apiGet<AdminStatsOut>(`${PLATFORM_ADMIN_BASE}/dashboard`, token);
}

export async function getPlatformSchools(
    token: string,
    params?: GetPlatformSchoolsParams
) {
    const query = buildQuery({
        search: params?.search,
    });

    return apiGet<PlatformSchoolSummaryOut[]>(
        `${PLATFORM_ADMIN_BASE}/schools${query}`,
        token
    );
}

export async function getAdminUsers(
    token: string,
    params?: GetAdminUsersParams
) {
    const query = buildQuery({
        school_id: params?.school_id,
        role: params?.role && params.role !== "all" ? params.role : undefined,
        search: params?.search,
        skip: params?.skip,
        limit: params?.limit,
    });

    return apiGet<AdminUsersResponse>(
        `${PLATFORM_ADMIN_BASE}/users${query}`,
        token
    );
}

export async function getAdminCourses(
    token: string,
    params?: GetAdminCoursesParams
) {
    const query = buildQuery({
        school_id: params?.school_id,
        search: params?.search,
        skip: params?.skip,
        limit: params?.limit,
    });

    return apiGet<AdminCoursesResponse>(
        `${PLATFORM_ADMIN_BASE}/courses${query}`,
        token
    );
}

export async function updateUserRole(
    token: string,
    userId: number,
    role: "student" | "teacher" | "admin"
) {
    return apiPost<AdminUserOut>(
        `${PLATFORM_ADMIN_BASE}/users/${userId}/role`,
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
        `${PLATFORM_ADMIN_BASE}/users/${userId}/active`,
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
        `${PLATFORM_ADMIN_BASE}/courses/${courseId}/publish`,
        { published },
        token
    );
}

export async function deleteCourseAdmin(token: string, courseId: number) {
    return apiPost<{ success: boolean }>(
        `${PLATFORM_ADMIN_BASE}/courses/${courseId}/delete`,
        {},
        token
    );
}