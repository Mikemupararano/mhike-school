const API_BASE =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
    "http://localhost:8000/api/v1";

const TOKEN_KEY = "mhike_token";

async function apiFetch<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const token =
        typeof window !== "undefined"
            ? sessionStorage.getItem(TOKEN_KEY)
            : null;

    const res = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers || {}),
        },
        cache: "no-store",
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error?.detail || "API request failed");
    }

    return res.json();
}

/* =========================
   Types
========================= */

export type TeacherDashboard = {
    teacher_id: number;
    total_courses: number;
    total_students: number;
    total_assignments: number;
    pending_submissions: number;
};

export type TeacherCourse = {
    id: number;
    title: string;
    students: number;
    assignments: number;
};

export type TeacherAssignment = {
    id: number;
    course_id: number;
    school_id: number;
    created_by: number;
    title: string;
    description?: string | null;
    due_date?: string | null;
    max_score: number;
    is_published: boolean;
    created_at: string;
};

/* =========================
   API Calls
========================= */

export async function getTeacherDashboard(): Promise<TeacherDashboard> {
    return apiFetch<TeacherDashboard>("/teacher-dashboard/me");
}

export async function getTeacherCourses(): Promise<TeacherCourse[]> {
    return apiFetch<TeacherCourse[]>("/teacher-dashboard/courses");
}

export async function getTeacherAssignments(): Promise<TeacherAssignment[]> {
    return apiFetch<TeacherAssignment[]>("/assignments/me");
}