import { apiGet } from "@/lib/api";

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
    full_name: string;
    email: string;
    role: string;
};

export type AdminCourseOut = {
    id: number;
    title: string;
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