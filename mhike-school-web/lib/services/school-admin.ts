import { User, type CreateUserInput, type UpdateUserInput } from "@/types/user";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000/api/v1";

const TOKEN_KEY = "mhike_token";

async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
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
    const error = await res.json().catch(() => null);
    throw new Error(error?.detail || "API request failed");
  }

  if (res.status === 204) {
    return null as T;
  }

  return (await res.json()) as T;
}

export async function getSchoolUsers(): Promise<User[]> {
  return apiFetch<User[]>("/school-admin/users");
}

export async function createSchoolUser(data: CreateUserInput): Promise<User> {
  return apiFetch<User>("/school-admin/users", {
    method: "POST",
    body: JSON.stringify({
      ...data,
      roles: data.roles,
      role: data.role ?? data.roles[0],
    }),
  });
}

export async function updateSchoolUser(
  userId: number,
  data: UpdateUserInput,
): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({
      ...data,
      role: data.role ?? data.roles?.[0],
    }),
  });
}

export async function deactivateUser(userId: number): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}/deactivate`, {
    method: "POST",
  });
}

export async function requestErasure(userId: number): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}/request-erasure`, {
    method: "POST",
  });
}

export async function anonymiseUser(userId: number): Promise<User> {
  return apiFetch<User>(`/school-admin/users/${userId}/anonymise`, {
    method: "POST",
  });
}