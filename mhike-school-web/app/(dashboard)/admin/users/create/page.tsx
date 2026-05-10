"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiGet, apiPost } from "@/lib/api";

type School = {
  id: number;
  name: string;
};

export default function AdminCreateUserPage() {
  const router = useRouter();

  const [schools, setSchools] = useState<School[]>([]);
  const [schoolId, setSchoolId] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSchools() {
      try {
        const data = await apiGet<School[]>("/admin/schools");
        setSchools(data);
      } catch (err) {
        console.error(err);
        setError("Failed to load schools.");
      }
    }

    loadSchools();
  }, []);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    setError("");

    if (!schoolId) {
      setError("Please select a school.");
      return;
    }

    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }

    try {
      setLoading(true);

      await apiPost(`/admin/schools/${schoolId}/admins`, {
        full_name: fullName.trim() || null,
        email: email.trim().toLowerCase(),
        password,
        school_id: Number(schoolId),
        role: "school_admin",
        roles: ["school_admin"],
      });

      router.push("/admin/users");
      router.refresh();
    } catch (err) {
      console.error(err);

      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to create school admin.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl p-8">
      <h1 className="text-3xl font-extrabold">
        Create School Admin
      </h1>

      <p className="mt-2 text-slate-500">
        Add a school administrator to a selected school.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-4"
      >
        <select
          value={schoolId}
          onChange={(e) => setSchoolId(e.target.value)}
          className="w-full rounded-xl border px-4 py-3"
        >
          <option value="">
            Select school
          </option>

          {schools.map((school) => (
            <option
              key={school.id}
              value={school.id}
            >
              {school.id} — {school.name}
            </option>
          ))}
        </select>

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

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading
              ? "Creating..."
              : "Create School Admin"}
          </button>

          <button
            type="button"
            onClick={() => router.push("/admin/users")}
            className="rounded-xl border px-6 py-3 font-semibold"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}