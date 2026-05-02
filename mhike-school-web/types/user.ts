export enum UserRole {
    PLATFORM_ADMIN = "platform_admin",
    SCHOOL_ADMIN = "school_admin",
    TEACHER = "teacher",
    STUDENT = "student",
}

export enum UserStatus {
    ACTIVE = "active",
    DEACTIVATED = "deactivated",
    PENDING_ERASURE = "pending_erasure",
    ANONYMISED = "anonymised",
}

export interface User {
    id: number;
    email: string;

    // Structured names
    first_name?: string | null;
    last_name?: string | null;

    // Backwards compatibility
    full_name?: string | null;

    /**
     * Legacy primary role (Phase 1 compatibility)
     */
    role?: UserRole | null;

    /**
     * Source of truth
     */
    roles: UserRole[];

    status: UserStatus;

    school_id?: number | null;
    school_name?: string | null;

    is_active: boolean;

    // GDPR fields
    erasure_requested_at?: string | null;
    is_anonymised?: boolean;

    created_at: string;
}

/* =========================
   Form Input Types (FIX)
========================= */

export type CreateUserInput = {
    email: string;
    password?: string;
    first_name?: string;
    last_name?: string;
    full_name?: string;

    // support both during transition
    role?: UserRole;
    roles?: UserRole[];

    school_id?: number | null;
};

export type UpdateUserInput = {
    email?: string;
    first_name?: string;
    last_name?: string;
    full_name?: string;

    role?: UserRole;
    roles?: UserRole[];

    is_active?: boolean;
    status?: UserStatus;
};

/* =========================
   Role Groups
========================= */

export const SCHOOL_STAFF_ROLES: UserRole[] = [
    UserRole.SCHOOL_ADMIN,
    UserRole.TEACHER,
];

export const TEACHING_ROLES: UserRole[] = [
    UserRole.PLATFORM_ADMIN,
    UserRole.SCHOOL_ADMIN,
    UserRole.TEACHER,
];

export const ADMIN_ROLES: UserRole[] = [
    UserRole.PLATFORM_ADMIN,
    UserRole.SCHOOL_ADMIN,
];

/* =========================
   Helpers
========================= */

export function hasRole(
    user: User | null | undefined,
    role: UserRole,
): boolean {
    return user?.roles?.includes(role) ?? false;
}

export function hasAnyRole(
    user: User | null | undefined,
    roles: UserRole[],
): boolean {
    return roles.some((role) => user?.roles?.includes(role));
}

export function canTeach(user: User | null | undefined): boolean {
    return hasAnyRole(user, TEACHING_ROLES);
}

/* =========================
   UI Helper
========================= */

export function getDisplayName(user: User): string {
    if (user.full_name) return user.full_name;

    const name = `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim();
    if (name) return name;

    return user.email;
}