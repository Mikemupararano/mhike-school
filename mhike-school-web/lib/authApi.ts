import { apiGet } from "@/lib/api";

export type CurrentUser = {
    id: number;
    full_name?: string | null;
    email: string;
    role: "student" | "teacher" | "admin" | "platform_admin" | string;
    school_id?: number | null;
    school_name?: string | null;
};

export async function getCurrentUser(token?: string) {
    return apiGet<CurrentUser>("/auth/me", token);
}