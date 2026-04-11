import { apiGet } from "@/lib/api";

export type CurrentUser = {
    id: number;
    email: string;
    role: "student" | "teacher" | "admin" | "school_admin" | "platform_admin" | string;

    full_name?: string | null;
    fullName?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    firstName?: string | null;
    lastName?: string | null;
    name?: string | null;

    school_id?: number | null;
    school_name?: string | null;
};

export async function getCurrentUser(token?: string): Promise<CurrentUser> {
    return apiGet<CurrentUser>("/auth/me", token);
}