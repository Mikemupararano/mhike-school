"use client";

import { useState, type FormEvent } from "react";

import { apiPost, saveToken } from "@/lib/api";
import { getCurrentUser, type CurrentUser } from "@/lib/authApi";
import { UserRole } from "@/types/user";

type LoginResponse = {
  access_token: string;
  token_type?: string;
};

type LoginMode = "school_user" | "platform_admin";

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
    if (typeof maybeError.error === "string") return maybeError.error;

    return JSON.stringify(maybeError, null, 2);
  }

  return "Login failed.";
}

export default function LoginPage() {
  const [mode, setMode] = useState<LoginMode>("school_user");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [schoolId, setSchoolId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const needsSchoolId = mode === "school_user";

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();
    const trimmedSchoolId = schoolId.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setError("Please enter your email and password.");
      return;
    }

    if (needsSchoolId && !trimmedSchoolId) {
      setError("Please enter your school ID.");
      return;
    }

    const parsedSchoolId = Number(trimmedSchoolId);

    if (needsSchoolId && Number.isNaN(parsedSchoolId)) {
      setError("School ID must be a valid number.");
      return;
    }

    try {
      setLoading(true);

      const payload = needsSchoolId
        ? {
          email: trimmedEmail,
          password: trimmedPassword,
          school_id: parsedSchoolId,
        }
        : {
          email: trimmedEmail,
          password: trimmedPassword,
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
    "h-14 w-full rounded-2xl border-2 border-slate-300 bg-white px-6 text-xl font-bold text-slate-950 outline-none placeholder:text-xl placeholder:font-bold placeholder:text-slate-500 focus:border-[#6F1A07] focus:ring-4 focus:ring-[#6F1A07]/20 xl:h-16 xl:text-2xl xl:placeholder:text-2xl";

  return (
    <main
      data-auth-page="true"
      className="min-h-screen bg-[#F4FAFF] text-slate-950"
    >
      <div className="flex min-h-screen flex-col items-center justify-start px-6 py-4 xl:px-12">
        <h1 className="mb-5 text-center text-4xl font-black leading-none tracking-tight text-[#111827] md:text-5xl xl:text-6xl">
          Welcome to MHike School
        </h1>

        <section className="w-[90vw] max-w-[1450px] rounded-[36px] bg-white px-8 py-7 shadow-2xl ring-1 ring-slate-200 md:px-16 md:py-8 xl:px-24 xl:py-9">
          <div className="mb-6 grid grid-cols-1 gap-5 rounded-[28px] bg-[#EAF5FF] p-4 md:grid-cols-2 xl:gap-6">
            <button
              type="button"
              data-custom-button="true"
              data-auth-button="tab"
              onClick={() => {
                setMode("school_user");
                setError("");
              }}
              className={`min-h-[92px] rounded-[22px] px-6 py-4 text-center text-3xl font-black leading-none transition xl:min-h-[105px] xl:text-4xl ${mode === "school_user"
                ? "bg-[#6F1A07] text-white shadow-xl"
                : "bg-white text-[#6F1A07] hover:bg-[#F9FCFF]"
                }`}
            >
              School User
              <span className="mt-2 block text-xl font-bold leading-tight xl:text-2xl">
                Students • Teachers • Admins
              </span>
            </button>

            <button
              type="button"
              data-custom-button="true"
              data-auth-button="tab"
              onClick={() => {
                setMode("platform_admin");
                setError("");
              }}
              className={`min-h-[92px] rounded-[22px] px-6 py-4 text-center text-3xl font-black leading-none transition xl:min-h-[105px] xl:text-4xl ${mode === "platform_admin"
                ? "bg-[#6F1A07] text-white shadow-xl"
                : "bg-white text-[#6F1A07] hover:bg-[#F9FCFF]"
                }`}
            >
              Platform Admin
              <span className="mt-2 block text-xl font-bold leading-tight xl:text-2xl">
                Global administration
              </span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 xl:space-y-5">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              autoComplete="email"
              className={inputClass}
            />

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              autoComplete="current-password"
              className={inputClass}
            />

            {needsSchoolId ? (
              <input
                type="number"
                value={schoolId}
                onChange={(e) => setSchoolId(e.target.value)}
                placeholder="School ID"
                inputMode="numeric"
                className={inputClass}
              />
            ) : null}

            <div className="flex flex-col gap-3 text-xl font-black text-[#111827] md:flex-row md:items-center md:justify-between xl:text-2xl">
              <label className="flex items-center gap-4">
                <input
                  type="checkbox"
                  className="h-7 w-7 rounded border-slate-400 text-[#6F1A07] focus:ring-[#6F1A07] xl:h-8 xl:w-8"
                />
                Remember me
              </label>

              <button
                type="button"
                data-custom-button="true"
                data-auth-button="link"
                className="bg-transparent text-left text-[#6F1A07] underline underline-offset-4 hover:text-[#8A220A] md:text-right"
              >
                Forgotten password?
              </button>
            </div>

            {error ? (
              <div className="rounded-[22px] border-2 border-red-200 bg-red-50 px-6 py-4 text-xl font-black leading-tight text-red-800 xl:text-2xl">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              data-custom-button="true"
              data-auth-button="submit"
              disabled={loading}
              className="flex h-20 w-full items-center justify-center rounded-[24px] bg-[#6F1A07] px-10 text-5xl font-black text-white shadow-xl transition hover:bg-[#8A220A] disabled:cursor-not-allowed disabled:opacity-70 xl:h-24 xl:text-6xl"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}