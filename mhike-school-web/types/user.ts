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
    full_name?: string | null;

    /**
     * Legacy primary role.
     * Keep during Phase 1 migration.
     * Prefer roles[] for all new checks.
     */
    role?: UserRole | null;

    /**
     * Source of truth for frontend permissions.
     * Supports users like ["school_admin", "teacher"].
     */
    roles: UserRole[];

    status: UserStatus;

    school_id?: number | null;
    school_name?: string | null;

    is_active: boolean;
    created_at: string;
}

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

export function hasRole(user: User | null | undefined, role: UserRole): boolean {
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