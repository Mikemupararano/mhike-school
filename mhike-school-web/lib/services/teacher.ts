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

export type TeacherDashboard = {
    teacher_id: number;
    total_courses: number;
    total_students: number;
    total_assignments: number;
    pending_submissions: number;
};

export async function getTeacherDashboard(): Promise<TeacherDashboard> {
    return apiFetch<TeacherDashboard>("/teacher-dashboard/me");
}