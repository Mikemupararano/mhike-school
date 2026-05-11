import { apiGet } from "@/lib/api";
import { UserRole, UserStatus } from "@/types/user";

export type CurrentUser = {
    id: number;
    email: string;

    role: UserRole;
    roles: UserRole[];

    status: UserStatus;

    full_name: string | null;

    school_id: number | null;
    school_name: string | null;

    is_active: boolean;
    created_at: string;
};

export async function getCurrentUser(
    token?: string,
): Promise<CurrentUser> {
    const data = await apiGet<CurrentUser>(
        "/auth/me",
        token,
    );

    return {
        ...data,

        roles: Array.isArray(data.roles)
            ? data.roles
            : data.role
                ? [data.role]
                : [],

        full_name: data.full_name ?? null,

        school_id: data.school_id ?? null,
        school_name: data.school_name ?? null,
    };
}