import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import { User, type CreateUserInput, type UpdateUserInput } from "@/types/user";

export async function listSchoolUsers(): Promise<User[]> {
  return apiGet<User[]>("/school-admin/users");
}

export async function getSchoolUser(userId: number): Promise<User> {
  return apiGet<User>(`/school-admin/users/${userId}`);
}

export async function createSchoolUser(
  data: CreateUserInput,
): Promise<User> {
  const primaryRole = data.role ?? data.roles?.[0];

  return apiPost<User>("/school-admin/users", {
    ...data,
    role: primaryRole,
    roles: data.roles ?? (primaryRole ? [primaryRole] : []),
  });
}

export async function updateSchoolUser(
  userId: number,
  data: UpdateUserInput,
): Promise<User> {
  const primaryRole = data.role ?? data.roles?.[0];

  return apiPatch<User>(`/school-admin/users/${userId}`, {
    ...data,
    ...(primaryRole ? { role: primaryRole } : {}),
  });
}

export async function deactivateSchoolUser(userId: number): Promise<User> {
  return apiPost<User>(`/school-admin/users/${userId}/deactivate`);
}

export async function assignUserRole(
  userId: number,
  role: string,
): Promise<User> {
  return apiPost<User>(`/school-admin/users/${userId}/roles`, { role });
}

export async function removeUserRole(
  userId: number,
  role: string,
): Promise<User> {
  return apiDelete<User>(`/school-admin/users/${userId}/roles/${role}`);
}

export async function requestUserErasure(userId: number): Promise<User> {
  return apiPost<User>(`/school-admin/users/${userId}/request-erasure`);
}

export async function anonymiseSchoolUser(userId: number): Promise<User> {
  return apiPost<User>(`/school-admin/users/${userId}/anonymise`);
}