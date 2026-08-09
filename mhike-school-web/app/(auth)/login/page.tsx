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

  if (roles.includes(UserRole.PLATFORM_ADMIN)) {
    return "/admin";
  }

  if (roles.includes(UserRole.SCHOOL_ADMIN)) {
    return "/school-admin";
  }

  if (roles.includes(UserRole.TEACHER)) {
    return "/teacher";
  }

  return "/student";
}


function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "string") {
    return error;
  }

  if (
    typeof error === "object"
    && error !== null
  ) {
    const maybeError = error as {
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
      return JSON.stringify(
        maybeError,
        null,
        2,
      );
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


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    setError("");

    const trimmedEmail = email
      .trim()
      .toLowerCase();

    const trimmedSchoolId = schoolId.trim();

    if (!trimmedEmail || password.length === 0) {
      setError(
        "Please enter your email and password.",
      );
      return;
    }

    if (needsSchoolId && !trimmedSchoolId) {
      setError(
        "Please enter your school ID.",
      );
      return;
    }

    const parsedSchoolId = Number(
      trimmedSchoolId,
    );

    if (
      needsSchoolId
      && (
        !Number.isInteger(parsedSchoolId)
        || parsedSchoolId <= 0
      )
    ) {
      setError(
        "School ID must be a valid positive whole number.",
      );
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

      const response =
        await apiPost<LoginResponse>(
          "/auth/login",
          payload,
        );

      if (!response.access_token) {
        throw new Error(
          "The server did not return an access token.",
        );
      }

      saveToken(
        response.access_token,
      );

      const user = await getCurrentUser(
        response.access_token,
      );

      window.location.replace(
        resolveRedirectPath(user),
      );
    } catch (error) {
      console.error(
        "Login error:",
        error,
      );

      setError(
        getErrorMessage(error),
      );
    } finally {
      setLoading(false);
    }
  }


  const inputClass = [
    "h-12",
    "w-full",
    "rounded-xl",
    "border",
    "border-[#D7E0EA]",
    "bg-white",
    "px-5",
    "text-base",
    "font-semibold",
    "text-[#0F172A]",
    "outline-none",
    "transition",
    "placeholder:text-base",
    "placeholder:font-medium",
    "placeholder:text-[#64748B]",
    "hover:border-[#94A3B8]",
    "focus:border-[#2563EB]",
    "focus:ring-4",
    "focus:ring-[#2563EB]/15",
    "disabled:cursor-not-allowed",
    "disabled:bg-slate-100",
    "disabled:text-slate-500",
    "sm:text-lg",
    "sm:placeholder:text-lg",
  ].join(" ");


  const activeTabClass = [
    "border-[#163A5F]",
    "bg-[#163A5F]",
    "text-white",
    "shadow-md",
    "shadow-[#163A5F]/20",
  ].join(" ");


  const inactiveTabClass = [
    "border-[#D7E0EA]",
    "bg-white",
    "text-[#163A5F]",
    "hover:border-[#2563EB]",
    "hover:bg-[#F8FAFC]",
  ].join(" ");


  return (
    <main
      data-auth-page="true"
      className="
        min-h-[calc(100dvh-5rem)]
        overflow-x-hidden
        bg-[#F4F7FB]
        text-[#0F172A]
      "
    >
      <div
        className="
          mx-auto
          flex
          min-h-[calc(100dvh-5rem)]
          w-full
          max-w-4xl
          flex-col
          items-center
          px-4
          pb-6
          pt-5
          sm:px-6
          sm:pt-6
          lg:px-8
        "
      >
        <h1
          className="
            mb-4
            text-center
            text-3xl
            font-black
            leading-tight
            tracking-tight
            text-[#071126]
            sm:text-4xl
          "
        >
          Welcome to MHike School
        </h1>

        <section
          aria-label="Sign in to MHike School"
          className="
            w-full
            max-w-2xl
            rounded-2xl
            border
            border-[#DCE4EC]
            bg-white
            p-4
            shadow-[0_16px_38px_rgba(15,23,42,0.10)]
            sm:p-5
          "
        >
          <div
            role="group"
            aria-label="Account type"
            className="
              mb-4
              grid
              grid-cols-1
              gap-2
              rounded-xl
              border
              border-[#DCE4EC]
              bg-[#F4F7FB]
              p-2
              sm:grid-cols-2
            "
          >
            <button
              type="button"
              data-custom-button="true"
              data-auth-button="tab"
              aria-pressed={
                mode === "school_user"
              }
              disabled={loading}
              onClick={() =>
                changeMode("school_user")
              }
              className={`
                flex
                min-h-[78px]
                flex-col
                items-center
                justify-center
                rounded-lg
                border
                px-4
                py-2.5
                text-center
                transition
                duration-200
                focus-visible:outline-none
                focus-visible:ring-4
                focus-visible:ring-[#2563EB]/30
                disabled:cursor-not-allowed
                disabled:opacity-70
                ${mode === "school_user"
                  ? activeTabClass
                  : inactiveTabClass
                }
              `}
            >
              <span
                className="
                  text-xl
                  font-black
                  leading-tight
                "
              >
                School User
              </span>

              <span
                className="
                  mt-1
                  text-sm
                  font-bold
                  leading-snug
                "
              >
                Students • Teachers • Admins
              </span>
            </button>

            <button
              type="button"
              data-custom-button="true"
              data-auth-button="tab"
              aria-pressed={
                mode === "platform_admin"
              }
              disabled={loading}
              onClick={() =>
                changeMode("platform_admin")
              }
              className={`
                flex
                min-h-[78px]
                flex-col
                items-center
                justify-center
                rounded-lg
                border
                px-4
                py-2.5
                text-center
                transition
                duration-200
                focus-visible:outline-none
                focus-visible:ring-4
                focus-visible:ring-[#2563EB]/30
                disabled:cursor-not-allowed
                disabled:opacity-70
                ${mode === "platform_admin"
                  ? activeTabClass
                  : inactiveTabClass
                }
              `}
            >
              <span
                className="
                  text-xl
                  font-black
                  leading-tight
                "
              >
                Platform Admin
              </span>

              <span
                className="
                  mt-1
                  text-sm
                  font-bold
                  leading-snug
                "
              >
                Global administration
              </span>
            </button>
          </div>

          <form
            onSubmit={handleSubmit}
            className="space-y-3"
            noValidate
          >
            <div>
              <label
                htmlFor="email"
                className="sr-only"
              >
                Email address
              </label>

              <input
                id="email"
                name="email"
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(
                    event.target.value,
                  )
                }
                placeholder="Email address"
                autoComplete="email"
                autoCapitalize="none"
                spellCheck={false}
                disabled={loading}
                required
                className={inputClass}
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="sr-only"
              >
                Password
              </label>

              <input
                id="password"
                name="password"
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value,
                  )
                }
                placeholder="Password"
                autoComplete="current-password"
                disabled={loading}
                required
                className={inputClass}
              />
            </div>

            {needsSchoolId ? (
              <div>
                <label
                  htmlFor="school-id"
                  className="sr-only"
                >
                  School ID
                </label>

                <input
                  id="school-id"
                  name="schoolId"
                  type="number"
                  value={schoolId}
                  onChange={(event) =>
                    setSchoolId(
                      event.target.value,
                    )
                  }
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

            <div
              className="
                flex
                flex-col
                gap-2
                text-sm
                font-bold
                text-[#0F172A]
                sm:flex-row
                sm:items-center
                sm:justify-between
                sm:text-base
              "
            >
              <label
                htmlFor="remember-me"
                className="
                  flex
                  cursor-pointer
                  items-center
                  gap-2.5
                "
              >
                <input
                  id="remember-me"
                  name="rememberMe"
                  type="checkbox"
                  disabled={loading}
                  className="
                    h-5
                    w-5
                    cursor-pointer
                    rounded
                    border-[#94A3B8]
                    accent-[#2563EB]
                    focus:ring-4
                    focus:ring-[#2563EB]/20
                    disabled:cursor-not-allowed
                  "
                />

                <span>
                  Remember me
                </span>
              </label>

              <button
                type="button"
                data-custom-button="true"
                data-auth-button="link"
                disabled={loading}
                className="
                  rounded-md
                  bg-transparent
                  text-left
                  font-bold
                  text-[#175CD3]
                  underline
                  decoration-2
                  underline-offset-4
                  transition
                  hover:text-[#0B4AA2]
                  focus-visible:outline-none
                  focus-visible:ring-4
                  focus-visible:ring-[#2563EB]/20
                  disabled:cursor-not-allowed
                  disabled:opacity-60
                  sm:text-right
                "
              >
                Forgotten password?
              </button>
            </div>

            {error ? (
              <div
                role="alert"
                aria-live="polite"
                className="
                  rounded-lg
                  border
                  border-red-300
                  bg-red-50
                  px-4
                  py-2.5
                  text-sm
                  font-bold
                  leading-snug
                  text-red-800
                  sm:text-base
                "
              >
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              data-custom-button="true"
              data-auth-button="submit"
              disabled={loading}
              aria-busy={loading}
              className="
                flex
                h-12
                w-full
                items-center
                justify-center
                rounded-xl
                border
                border-[#163A5F]
                bg-[#163A5F]
                px-6
                text-lg
                font-black
                leading-none
                text-white
                shadow-md
                shadow-[#163A5F]/20
                transition
                duration-200
                hover:border-[#1D4D78]
                hover:bg-[#1D4D78]
                focus-visible:outline-none
                focus-visible:ring-4
                focus-visible:ring-[#2563EB]/35
                disabled:cursor-not-allowed
                disabled:opacity-70
                sm:text-xl
              "
            >
              {loading
                ? "Signing in..."
                : "Sign in"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}