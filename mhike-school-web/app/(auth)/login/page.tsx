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

    if (typeof maybeError.detail === "string") {
      return maybeError.detail;
    }

    if (typeof maybeError.message === "string") {
      return maybeError.message;
    }

    if (typeof maybeError.error === "string") {
      return maybeError.error;
    }

    try {
      return JSON.stringify(maybeError, null, 2);
    } catch {
      return "Login failed.";
    }
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

  function changeMode(nextMode: LoginMode) {
    setMode(nextMode);
    setError("");

    if (nextMode === "platform_admin") {
      setSchoolId("");
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedSchoolId = schoolId.trim();

    if (!trimmedEmail || password.length === 0) {
      setError("Please enter your email and password.");
      return;
    }

    if (needsSchoolId && !trimmedSchoolId) {
      setError("Please enter your school ID.");
      return;
    }

    const parsedSchoolId = Number(trimmedSchoolId);

    if (
      needsSchoolId &&
      (!Number.isInteger(parsedSchoolId) || parsedSchoolId <= 0)
    ) {
      setError("School ID must be a valid positive whole number.");
      return;
    }

    try {
      setLoading(true);

      const payload = needsSchoolId
        ? {
          email: trimmedEmail,
          password,
          school_id: parsedSchoolId,
        }
        : {
          email: trimmedEmail,
          password,
        };

      const response = await apiPost<LoginResponse>("/auth/login", payload);

      if (!response.access_token) {
        throw new Error("The server did not return an access token.");
      }

      saveToken(response.access_token);

      const user = await getCurrentUser(response.access_token);

      window.location.replace(resolveRedirectPath(user));
    } catch (err) {
      console.error("Login error:", err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "h-14 w-full rounded-2xl border border-[#D7E0EA] bg-white px-6 text-xl font-bold text-[#0F172A] outline-none transition placeholder:text-xl placeholder:font-semibold placeholder:text-[#64748B] hover:border-[#94A3B8] focus:border-[#2563EB] focus:ring-4 focus:ring-[#2563EB]/15 disabled:cursor-not-allowed disabled:bg-slate-100 xl:h-16 xl:text-2xl xl:placeholder:text-2xl";

  const activeTabClass =
    "border-[#163A5F] bg-[#163A5F] text-white shadow-lg shadow-[#163A5F]/20";

  const inactiveTabClass =
    "border-[#D7E0EA] bg-white text-[#163A5F] hover:border-[#2563EB] hover:bg-[#F4F7FB]";

  return (
    <main
      data-auth-page="true"
      className="overflow-x-hidden bg-[#F4F7FB] text-[#0F172A]"
    >
      <div className="flex h-[calc(100dvh-5rem)] flex-col items-center justify-center overflow-y-auto px-4 py-3 sm:h-[calc(100dvh-6rem)] sm:px-6 xl:px-12">
        <h1 className="mb-3 text-center text-4xl font-black leading-none tracking-tight text-[#071126] md:text-5xl xl:text-[3.4rem]">
          Welcome to MHike School
        </h1>

        <section className="w-full max-w-[1280px] rounded-[32px] border border-[#DCE4EC] bg-white px-6 py-5 shadow-[0_20px_50px_rgba(15,23,42,0.12)] sm:w-[90vw] md:px-14 md:py-6 xl:px-20 xl:py-7">
          <div className="mb-5 grid grid-cols-1 gap-4 rounded-[26px] border border-[#DCE4EC] bg-[#F4F7FB] p-4 md:grid-cols-2 xl:gap-6">
            <button
              type="button"
              data-custom-button="true"
              data-auth-button="tab"
              aria-pressed={mode === "school_user"}
              onClick={() => changeMode("school_user")}
              className={`min-h-[92px] rounded-[20px] border px-6 py-4 text-center text-3xl font-black leading-none transition duration-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#2563EB]/30 xl:min-h-[100px] xl:text-4xl ${mode === "school_user"
                ? activeTabClass
                : inactiveTabClass
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
              aria-pressed={mode === "platform_admin"}
              onClick={() => changeMode("platform_admin")}
              className={`min-h-[92px] rounded-[20px] border px-6 py-4 text-center text-3xl font-black leading-none transition duration-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#2563EB]/30 xl:min-h-[100px] xl:text-4xl ${mode === "platform_admin"
                ? activeTabClass
                : inactiveTabClass
                }`}
            >
              Platform Admin

              <span className="mt-2 block text-xl font-bold leading-tight xl:text-2xl">
                Global administration
              </span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>

              <input
                id="email"
                name="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                autoComplete="email"
                disabled={loading}
                required
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>

              <input
                id="password"
                name="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="current-password"
                disabled={loading}
                required
                className={inputClass}
              />
            </div>

            {needsSchoolId ? (
              <div>
                <label htmlFor="school-id" className="sr-only">
                  School ID
                </label>

                <input
                  id="school-id"
                  name="schoolId"
                  type="number"
                  value={schoolId}
                  onChange={(e) => setSchoolId(e.target.value)}
                  placeholder="School ID"
                  inputMode="numeric"
                  autoComplete="off"
                  min={1}
                  step={1}
                  disabled={loading}
                  required
                  className={inputClass}
                />
              </div>
            ) : null}

            <div className="flex flex-col gap-3 text-xl font-black text-[#0F172A] md:flex-row md:items-center md:justify-between xl:text-2xl">
              <label
                htmlFor="remember-me"
                className="flex cursor-pointer items-center gap-4"
              >
                <input
                  id="remember-me"
                  name="rememberMe"
                  type="checkbox"
                  disabled={loading}
                  className="h-7 w-7 cursor-pointer rounded-md border-[#94A3B8] accent-[#2563EB] focus:ring-4 focus:ring-[#2563EB]/20 disabled:cursor-not-allowed xl:h-8 xl:w-8"
                />

                <span>Remember me</span>
              </label>

              <button
                type="button"
                data-custom-button="true"
                data-auth-button="link"
                disabled={loading}
                className="rounded-md bg-transparent text-left font-black text-[#175CD3] underline decoration-2 underline-offset-4 transition hover:text-[#0B4AA2] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#2563EB]/20 disabled:cursor-not-allowed disabled:opacity-60 md:text-right"
              >
                Forgotten password?
              </button>
            </div>

            {error ? (
              <div
                role="alert"
                aria-live="polite"
                className="rounded-[18px] border border-red-300 bg-red-50 px-6 py-4 text-xl font-bold leading-tight text-red-800 xl:text-2xl"
              >
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              data-custom-button="true"
              data-auth-button="submit"
              disabled={loading}
              className="flex h-20 w-full items-center justify-center rounded-[22px] bg-[#163A5F] px-10 text-4xl font-black text-white shadow-lg shadow-[#163A5F]/20 transition duration-200 hover:bg-[#1D4D78] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#2563EB]/35 disabled:cursor-not-allowed disabled:opacity-70 sm:text-5xl xl:h-[5.5rem] xl:text-[3.5rem]"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}