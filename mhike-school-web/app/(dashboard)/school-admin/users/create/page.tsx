"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";
import { createSchoolUser } from "@/lib/services/school-admin";

const ROLE_OPTIONS = [
  UserRole.SCHOOL_ADMIN,
  UserRole.TEACHER,
  UserRole.STUDENT,
];

export default function CreateUserPage() {
  return (
    <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
      <CreateUserForm />
    </RoleGate>
  );
}

function CreateUserForm() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [roles, setRoles] = useState<UserRole[]>([UserRole.STUDENT]);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    email.trim().length > 3 &&
    password.length >= 6 &&
    roles.length > 0 &&
    !isLoading;

  function toggleRole(role: UserRole) {
    setRoles((prev) =>
      prev.includes(role)
        ? prev.filter((r) => r !== role)
        : [...prev, role]
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      setIsLoading(true);

      await createSchoolUser({
        email: email.trim(),
        full_name: fullName.trim() || undefined,
        password,
        roles,
      });

      router.push("/school-admin/users");
      router.refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create user.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="max-w-xl p-6">
      <h1 className="text-3xl font-extrabold">Create User</h1>
      <p className="mt-2 text-slate-500">
        Add a new user to your school.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {/* EMAIL */}
        <div>
          <label className="block text-sm font-medium">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          />
        </div>

        {/* NAME */}
        <div>
          <label className="block text-sm font-medium">Full name</label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          />
        </div>

        {/* PASSWORD */}
        <div>
          <label className="block text-sm font-medium">Password</label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          />
        </div>

        {/* ROLES (MULTI ROLE ✅) */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Roles
          </label>

          <div className="flex flex-wrap gap-2">
            {ROLE_OPTIONS.map((role) => (
              <button
                type="button"
                key={role}
                onClick={() => toggleRole(role)}
                className={`rounded-full px-3 py-1 text-sm border ${roles.includes(role)
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-700"
                  }`}
              >
                {role.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="text-sm text-red-500">{error}</div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-lg bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
          >
            {isLoading ? "Creating..." : "Create user"}
          </button>

          <button
            type="button"
            onClick={() => router.push("/school-admin/users")}
            className="rounded-lg border px-4 py-2"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}