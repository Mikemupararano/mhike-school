// 🔐 Roles (must match backend exactly)
export enum UserRole {
    PLATFORM_ADMIN = "platform_admin",
    SCHOOL_ADMIN = "school_admin",
    TEACHER = "teacher",
    STUDENT = "student",
}

// 📊 Status (GDPR lifecycle)
export enum UserStatus {
    ACTIVE = "active",
    DEACTIVATED = "deactivated",
    PENDING_ERASURE = "pending_erasure",
    ANONYMISED = "anonymised",
}

// 👤 Core User (matches UserOut from backend)
export interface User {
    id: number
    email: string
    full_name?: string | null

    role: UserRole
    status: UserStatus

    school_id?: number | null
    school_name?: string | null

    is_active: boolean
    created_at: string // ISO string
}