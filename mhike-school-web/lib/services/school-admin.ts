import { User, CreateUserInput, UpdateUserInput } from "@/types/user"

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

/* =========================
   Helper
========================= */
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

  return res.json()
}

/* =========================
   School Admin Service
========================= */

// 👥 Get users
export async function getSchoolUsers(): Promise<User[]> {
  return apiFetch<User[]>("/school-admin/users")
}

// ➕ Create user
export async function createSchoolUser(
  data: CreateUserInput
): Promise<User> {
  return apiFetch<User>("/school-admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

// ✏️ Update user
export async function updateSchoolUser(
  userId: number,
  data: UpdateUserInput
): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

// ⛔ Deactivate user
export async function deactivateUser(userId: number): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}/deactivate`, {
    method: "POST",
  })
}

// 🗑 Request erasure (GDPR)
export async function requestErasure(userId: number): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}/request-erasure`, {
    method: "POST",
  })
}

// 🧼 Anonymise user (GDPR)
export async function anonymiseUser(userId: number): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}/anonymise`, {
    method: "POST",
  })
}