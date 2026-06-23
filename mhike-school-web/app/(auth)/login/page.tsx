"use client";

import { useMemo, useState, type FormEvent } from "react";

import { apiPost, saveToken } from "@/lib/api";
import { getCurrentUser, type CurrentUser } from "@/lib/authApi";
import { UserRole } from "@/types/user";

type LoginResponse = {
  access_token: string;
  token_type?: string;
};

function resolveRedirectPath(user: CurrentUser): string {
  const roles = Array.from(
    new Set([
      ...(Array.isArray(user.roles) ? user.roles : []),
      ...(user.role ? [user.role] : []),
    ]),
  );

  if (roles.includes(UserRole.PLATFORM_ADMIN)) return "/admin";
  if (roles.includes(UserRole.SCHOOL_ADMIN)) return "/school-admin";
  if (roles.includes(UserRole.TEACHER)) return "/teacher";

  return "/student";
}

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;

  if (typeof err === "object" && err !== null) {
    const maybeError = err as {
      detail?: unknown;
      message?: unknown;
      error?: unknown;
    };

    if (typeof maybeError.detail === "string") return maybeError.detail;
    if (typeof maybeError.message === "string") return maybeError.message;

    return JSON.stringify(maybeError, null, 2);
  }

  return "Login failed.";
}

export default function LoginPage() {
  const [mode, setMode] = useState<"school_user" | "platform_admin">(
    "school_user",
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [schoolId, setSchoolId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const needsSchoolId = mode === "school_user";

  const subtitle = useMemo(
    () =>
      needsSchoolId
        ? "Students, teachers and school administrators sign in using the school ID provided by their administrator."
        : "Platform administrators sign in without a school ID.",
    [needsSchoolId],
  );

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setError("Please enter your email and password.");
      return;
    }

    if (needsSchoolId && !schoolId.trim()) {
      setError("Please enter your school ID.");
      return;
    }

    if (needsSchoolId && Number.isNaN(Number(schoolId))) {
      setError("School ID must be a valid number.");
      return;
    }

    try {
      setLoading(true);

      const payload =
        mode === "platform_admin"
          ? { email: trimmedEmail, password: trimmedPassword }
          : {
            email: trimmedEmail,
            password: trimmedPassword,
            school_id: Number(schoolId),
          };

      const res = await apiPost<LoginResponse>("/auth/login", payload);

      saveToken(res.access_token);

      const user = await getCurrentUser(res.access_token);

      window.location.replace(resolveRedirectPath(user));
    } catch (err) {
      console.error("Login error:", err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "h-24 w-full rounded-2xl border-2 border-slate-300 bg-white px-10 text-[2rem] font-semibold text-slate-950 outline-none transition placeholder:text-[1.75rem] placeholder:font-medium placeholder:text-slate-500 focus:border-blue-700 focus:ring-4 focus:ring-blue-100";

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100 pb-28 text-slate-950">
      <div className="flex min-h-screen items-center justify-center px-10 py-10">
        <section className="w-[90vw] max-w-[1900px] rounded-[3rem] bg-white px-32 py-16 shadow-2xl ring-1 ring-slate-200">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-blue-700 text-4xl font-black text-white shadow-xl shadow-blue-700/25">
              M
            </div>

            <h1 className="text-[5.5rem] font-black leading-none tracking-tight text-slate-950">
              MHike <span className="text-blue-700">School</span>
            </h1>

            <p className="mt-4 text-[2.1rem] font-bold text-slate-700">
              Modern school management platform
            </p>
          </div>

          <div className="mx-auto max-w-[1650px]">
            <div className="text-center">
              <p className="text-[1.8rem] font-black uppercase tracking-wide text-blue-700">
                Sign in
              </p>

              <h2 className="mt-2 text-[6rem] font-black leading-none tracking-tight text-slate-950">
                Welcome back
              </h2>

              <p className="mt-4 text-[2.2rem] font-semibold leading-[2.8rem] text-slate-700">
                Sign in to access your MHike School workspace.
              </p>
            </div>

            <div className="mt-8 grid grid-cols-2 gap-5 rounded-2xl bg-slate-100 p-4">
              <button
                type="button"
                onClick={() => {
                  setMode("school_user");
                  setError("");
                }}
                className={`h-24 rounded-2xl px-8 transition ${mode === "school_user"
                  ? "bg-blue-700 text-white shadow-lg shadow-blue-700/25"
                  : "bg-white text-slate-950 hover:text-blue-800"
                  }`}
              >
                <span className="block text-[3.2rem] font-black leading-none">
                  School User
                </span>
                <span className="mt-2 block text-[1.8rem] font-semibold leading-7">
                  Students, teachers & school admins
                </span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode("platform_admin");
                  setError("");
                }}
                className={`h-24 rounded-2xl px-8 transition ${mode === "platform_admin"
                  ? "bg-blue-700 text-white shadow-lg shadow-blue-700/25"
                  : "bg-white text-slate-950 hover:text-blue-800"
                  }`}
              >
                <span className="block text-[3.2rem] font-black leading-none">
                  Platform Admin
                </span>
                <span className="mt-2 block text-[1.8rem] font-semibold leading-7">
                  Global platform administration
                </span>
              </button>
            </div>

            <div className="mt-7 rounded-2xl bg-blue-50 px-8 py-6 text-[2rem] font-bold leading-[2.7rem] text-blue-950 ring-1 ring-blue-100">
              {subtitle}
            </div>

            <form onSubmit={handleSubmit} className="mt-8 space-y-6">
              <label className="grid grid-cols-[330px_1fr] items-center gap-8">
                <span className="text-[2rem] font-black text-slate-950">
                  Email address
                </span>

                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email address e.g. john.doe@school.com"
                  autoComplete="email"
                  className={inputClass}
                />
              </label>

              <label className="grid grid-cols-[330px_1fr] items-center gap-8">
                <span className="text-[2rem] font-black text-slate-950">
                  Password
                </span>

                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className={inputClass}
                />
              </label>

              {needsSchoolId ? (
                <div>
                  <label className="grid grid-cols-[330px_1fr] items-center gap-8">
                    <span className="text-[2rem] font-black text-slate-950">
                      School ID
                    </span>

                    <input
                      type="number"
                      value={schoolId}
                      onChange={(e) => setSchoolId(e.target.value)}
                      placeholder="Enter your school ID provided by your administrator"
                      inputMode="numeric"
                      className={inputClass}
                    />
                  </label>

                  <p className="ml-[362px] mt-2 text-[1.45rem] font-bold leading-7 text-slate-700">
                    You can find your school ID in the welcome email from your
                    school, or ask your administrator.
                  </p>
                </div>
              ) : null}

              <div className="flex items-center justify-between gap-8 text-[1.8rem]">
                <label className="flex items-center gap-4 font-bold text-slate-800">
                  <input
                    type="checkbox"
                    className="h-8 w-8 rounded border-slate-400 text-blue-700 focus:ring-blue-600"
                  />
                  Remember me on this device
                </label>

                <button
                  type="button"
                  className="font-black text-blue-700 hover:text-blue-800"
                >
                  Forgot your password?
                </button>
              </div>

              {error ? (
                <div className="rounded-2xl border-2 border-red-200 bg-red-50 px-8 py-5 text-[1.6rem] font-bold leading-8 text-red-800">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={loading}
                className="h-24 w-full rounded-2xl bg-blue-700 px-12 text-[2.2rem] font-black tracking-tight text-white shadow-xl shadow-blue-700/25 transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? "Signing in..." : "Sign in to your account"}
              </button>
            </form>

            <p className="mt-7 text-center text-[1.5rem] font-bold leading-7 text-slate-700">
              Secure and encrypted access for authorised MHike School users.
            </p>
          </div>
        </section>
      </div>

      <footer className="fixed bottom-0 left-0 right-0 z-50 border-t border-blue-800 bg-blue-700">
        <div className="flex h-20 w-full items-center justify-between px-12">
          <div className="text-xl font-semibold text-white">
            © {new Date().getFullYear()} MHike School. All Rights Reserved.
          </div>

          <div className="flex items-center gap-12">
            <a
              href="/privacy-policy"
              className="text-xl font-semibold text-white hover:underline"
            >
              Privacy Policy
            </a>

            <a
              href="/contact-support"
              className="text-xl font-semibold text-white hover:underline"
            >
              Contact Support
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}