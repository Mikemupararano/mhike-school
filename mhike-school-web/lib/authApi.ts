import { apiGet } from "@/lib/api";
import { UserRole, UserStatus } from "@/types/user";

export type CurrentUser = {
    id: number;
    email: string;

    role: UserRole;
    roles: UserRole[];

    status: UserStatus;

    full_name?: string | null;
    fullName?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    firstName?: string | null;
    lastName?: string | null;
    name?: string | null;

    school_id?: number | null;
    school_name?: string | null;

    is_active: boolean;
    created_at: string;
};

export async function getCurrentUser(token?: string): Promise<CurrentUser> {
    const data = await apiGet<CurrentUser>("/auth/me", token);

    return {
        ...data,
        roles: Array.isArray(data.roles)
            ? data.roles
            : data.role
                ? [data.role]
                : [],
    };
}