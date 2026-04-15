import { User } from "@/types/user"

const API_BASE =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

async function apiFetch<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const token =
        typeof window !== "undefined" ? localStorage.getItem("token") : null

    const res = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.headers || {}),
        },
    })

    if (!res.ok) {
        const error = await res.json().catch(() => ({}))
        throw new Error(error.detail || "API request failed")
    }

    if (res.status === 204) {
        return undefined as T
    }

    return res.json()
}

export type ClassGroup = {
    id: number
    name: string
    school_id: number
    teacher_id?: number | null
    created_at: string
}

export type CreateClassInput = {
    name: string
    teacher_id?: number | null
}

export type AssignTeacherResponse = ClassGroup

export type EnrollmentCreateInput = {
    user_id: number
    class_id: number
}

export type EnrollmentResponse = {
    id: number
    user_id: number
    class_id: number
    created_at: string
}

// 📚 Get all classes for current school
export async function getClasses(): Promise<ClassGroup[]> {
    return apiFetch<ClassGroup[]>("/classes")
}

// 📘 Get one class
export async function getClassById(classId: number): Promise<ClassGroup> {
    return apiFetch<ClassGroup>(`/classes/${classId}`)
}

// ➕ Create class
export async function createClass(
    data: CreateClassInput
): Promise<ClassGroup> {
    return apiFetch<ClassGroup>("/classes", {
        method: "POST",
        body: JSON.stringify(data),
    })
}

// 👨‍🏫 Assign teacher to class
export async function assignTeacher(
    classId: number,
    teacherId: number
): Promise<AssignTeacherResponse> {
    return apiFetch<AssignTeacherResponse>(
        `/classes/${classId}/assign-teacher?teacher_id=${teacherId}`,
        {
            method: "PATCH",
        }
    )
}

// 👥 Get students in class
export async function getClassStudents(classId: number): Promise<User[]> {
    return apiFetch<User[]>(`/classes/${classId}/students`)
}

// ➕ Assign student to class
export async function assignStudentToClass(
    data: EnrollmentCreateInput
): Promise<EnrollmentResponse> {
    return apiFetch<EnrollmentResponse>("/enrollments", {
        method: "POST",
        body: JSON.stringify(data),
    })
}

// ❌ Remove student from class
export async function removeStudentFromClass(
    data: EnrollmentCreateInput
): Promise<void> {
    await apiFetch<void>("/enrollments", {
        method: "DELETE",
        body: JSON.stringify(data),
    })
}