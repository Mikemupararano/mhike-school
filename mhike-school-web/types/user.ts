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

    role: UserRole;
    roles: UserRole[];

    status: UserStatus;

    school_id?: number | null;
    school_name?: string | null;

    is_active: boolean;
    created_at: string;
}