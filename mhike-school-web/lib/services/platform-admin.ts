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

    if (res.status === 204) {
        return undefined as T
    }

    return res.json()
}

// =========================
// School Types
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
// Audit Log Types
// =========================

export type AuditLog = {
    id: number
    action: string
    entity_type: string
    entity_id: number | null
    actor_user_id: number | null
    school_id: number | null
    metadata?: Record<string, unknown> | null
    created_at: string
}

export type AuditLogResponse = {
    items: AuditLog[]
    total: number
    page: number
    page_size: number
}

export type AuditLogQueryParams = {
    page?: number
    page_size?: number
    actor_user_id?: number
    school_id?: number
    action?: string
    entity_type?: string
    search?: string
}

// =========================
// School API calls
// =========================

export async function getPlatformSchools(): Promise<School[]> {
    return apiFetch<School[]>('/platform-admin/schools')
}

export async function createPlatformSchool(
    data: CreateSchoolInput
): Promise<School> {
    return apiFetch<School>('/platform-admin/schools', {
        method: 'POST',
        body: JSON.stringify({
            name: data.name.trim(),
        }),
    })
}

// =========================
// Audit Log API calls
// =========================

export async function getAuditLogs(
    params: AuditLogQueryParams = {}
): Promise<AuditLogResponse> {
    const query = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.append(key, String(value))
        }
    })

    const queryString = query.toString()

    return apiFetch<AuditLogResponse>(
        queryString ? `/audit-logs?${queryString}` : '/audit-logs'
    )
}