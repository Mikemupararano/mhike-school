const API_BASE =
    process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

async function apiFetch<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const token =
        typeof window !== 'undefined' ? localStorage.getItem('token') : null

    const res = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers || {}),
        },
    })

    if (!res.ok) {
        const error = await res.json().catch(() => ({}))
        throw new Error(error.detail || 'API request failed')
    }

    // ✅ Handle empty responses safely
    if (res.status === 204) {
        return undefined as T
    }

    return res.json()
}

// =========================
// Types
// =========================
export type School = {
    id: number
    name: string
    created_at: string
}

export type CreateSchoolInput = {
    name: string
}

// =========================
// API calls
// =========================

// 📚 Get all schools
export async function getPlatformSchools(): Promise<School[]> {
    return apiFetch<School[]>('/platform-admin/schools')
}

// ➕ Create school
export async function createPlatformSchool(
    data: CreateSchoolInput
): Promise<School> {
    return apiFetch<School>('/platform-admin/schools', {
        method: 'POST',
        body: JSON.stringify({
            name: data.name.trim(), // ✅ prevent empty/whitespace names
        }),
    })
}