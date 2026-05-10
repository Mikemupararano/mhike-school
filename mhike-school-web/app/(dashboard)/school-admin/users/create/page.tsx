"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiGet, apiPost } from "@/lib/api";

type CurrentUser = {
  id: number;
  email: string;
  school_id?: number | null;
};

export default function SchoolAdminCreateUserPage() {
  const router = useRouter();

  const [schoolId, setSchoolId] = useState<number | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("teacher");

  const [loadingUser, setLoadingUser] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadCurrentUser() {
      try {
        setLoadingUser(true);
        setError("");

        const user = await apiGet<CurrentUser>("/auth/me");

        if (!user.school_id) {
          setError("Your account is not assigned to a school.");
          return;
        }

        setSchoolId(user.school_id);
      } catch (err) {
        console.error(err);
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load current user.",
        );
      } finally {
        setLoadingUser(false);
      }
    }

    loadCurrentUser();
  }, []);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    if (!schoolId) {
      setError("School ID could not be resolved.");
      return;
    }

    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }

    try {
      setSubmitting(true);

      await apiPost("/school-admin/users", {
        full_name: fullName.trim() || null,
        email: email.trim().toLowerCase(),
        password,
        school_id: schoolId,
        role,
        roles: [role],
      });

      router.push("/school-admin/users");
      router.refresh();
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Failed to create user.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl p-8">
      <h1 className="text-3xl font-extrabold">
        Create User
      </h1>

      <p className="mt-2 text-slate-500">
        Add a teacher or student to your school.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-4"
      >
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Full name"
          className="w-full rounded-xl border px-4 py-3"
        />

        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="w-full rounded-xl border px-4 py-3"
        />

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Temporary password"
          className="w-full rounded-xl border px-4 py-3"
        />

        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="w-full rounded-xl border px-4 py-3"
        >
          <option value="teacher">Teacher</option>
          <option value="student">Student</option>
        </select>

        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            {error}
          </div>
        ) : null}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting || loadingUser}
            className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting ? "Creating..." : "Create User"}
          </button>

          <button
            type="button"
            onClick={() => router.push("/school-admin/users")}
            className="rounded-xl border px-6 py-3 font-semibold"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}