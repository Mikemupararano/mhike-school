"use client";

import { useMemo, useState, type CSSProperties, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { apiPost, saveToken } from "@/lib/api";
import { getCurrentUser, type CurrentUser } from "@/lib/authApi";
import { UserRole } from "@/types/user";

type LoginResponse = {
  access_token: string;
  token_type?: string;
};

const DARK_BLUE = "#0f2d4a";
const BORDER = "rgba(255,255,255,0.10)";
const SOFT_TEXT = "rgba(255,255,255,0.84)";

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

  if (
    typeof err === "object" &&
    err !== null &&
    "error" in err &&
    typeof (err as { error?: { message?: unknown } }).error?.message === "string"
  ) {
    return (err as { error: { message: string } }).error.message;
  }

  if (
    typeof err === "object" &&
    err !== null &&
    "message" in err &&
    typeof (err as { message?: unknown }).message === "string"
  ) {
    return (err as { message: string }).message;
  }

  return "Login failed.";
}

export default function LoginPage() {
  const router = useRouter();

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
        ? "Students, teachers, and school admins sign in with their school ID."
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
      router.push(resolveRedirectPath(user));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <style>{`
        .login-shell {
          min-height: calc(100vh - 6rem);
          display: grid;
          align-items: center;
          padding: 32px 64px 48px;
          background:
            radial-gradient(circle at 18% 18%, rgba(37,99,235,0.10), transparent 28%),
            radial-gradient(circle at 82% 24%, rgba(59,130,246,0.08), transparent 30%),
            linear-gradient(180deg, #F8FAFC 0%, #EEF4FA 100%);
        }

        .login-grid {
          width: 100%;
          max-width: 1800px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: 1.15fr 1fr;
          gap: 48px;
          align-items: stretch;
        }

        .left-card,
        .right-card {
          border-radius: 36px;
          background: ${DARK_BLUE};
          color: #fff;
          border: 1px solid ${BORDER};
          box-shadow: 0 38px 90px rgba(15, 23, 42, 0.3);
        }

        .left-card {
          padding: 56px;
          min-height: 780px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .right-card {
          padding: 56px;
          min-height: 780px;
          display: flex;
          flex-direction: column;
          justify-content: center;
        }

        .hero-title {
          margin: 0 0 22px;
          font-size: 76px;
          line-height: 1.02;
          font-weight: 900;
          letter-spacing: -0.06em;
          max-width: 920px;
        }

        .hero-copy {
          margin: 0;
          font-size: 28px;
          line-height: 1.6;
          color: rgba(255,255,255,0.9);
          max-width: 820px;
        }

        .feature-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 20px;
          margin-top: 40px;
        }

        .feature-card {
          border-radius: 24px;
          padding: 24px;
          background: rgba(255,255,255,0.08);
          border: 1px solid ${BORDER};
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }

        .feature-title {
          font-size: 28px;
          font-weight: 900;
          margin-bottom: 10px;
          line-height: 1.15;
        }

        .feature-copy {
          font-size: 19px;
          line-height: 1.65;
          color: rgba(255,255,255,0.82);
        }

        .right-title {
          margin: 0;
          font-size: 64px;
          line-height: 1;
          font-weight: 900;
          letter-spacing: -0.05em;
          color: #fff;
        }

        .right-subtitle {
          margin: 18px 0 0;
          font-size: 24px;
          line-height: 1.65;
          color: ${SOFT_TEXT};
        }

        .mode-wrap {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          padding: 8px;
          border-radius: 22px;
          background: rgba(255,255,255,0.08);
          border: 1px solid ${BORDER};
          margin-bottom: 32px;
        }

        .mode-btn {
          height: 68px;
          border-radius: 18px;
          border: none;
          cursor: pointer;
          font-weight: 900;
          font-size: 20px;
          transition: all 0.2s ease;
        }

        .subtitle-box {
          margin-bottom: 32px;
          padding: 22px 24px;
          border-radius: 22px;
          background: rgba(255,255,255,0.06);
          border: 1px solid ${BORDER};
          color: rgba(255,255,255,0.84);
          font-size: 20px;
          line-height: 1.7;
        }

        .form-grid {
          display: grid;
          gap: 24px;
        }

        .field {
          display: grid;
          gap: 12px;
        }

        .field-label {
          font-size: 22px;
          font-weight: 900;
          color: #fff;
        }

        .submit-btn {
          height: 74px;
          border-radius: 22px;
          border: none;
          cursor: pointer;
          background: linear-gradient(135deg, #1D4ED8, #2563EB);
          color: #FFFFFF;
          font-weight: 900;
          font-size: 24px;
          box-shadow: 0 20px 40px rgba(37, 99, 235, 0.35);
          transition: all 0.2s ease;
        }

        .error-box {
          padding: 18px 20px;
          border-radius: 18px;
          background: #FEF2F2;
          border: 1px solid #FECACA;
          color: #991B1B;
          font-size: 18px;
          font-weight: 700;
          line-height: 1.6;
        }

        @media (max-width: 1199px) {
          .login-shell {
            padding: 28px 32px 40px;
          }

          .login-grid {
            grid-template-columns: 1fr;
            gap: 32px;
            max-width: 980px;
          }

          .left-card,
          .right-card {
            min-height: unset;
            padding: 40px;
          }

          .hero-title {
            font-size: 58px;
            max-width: 100%;
          }

          .hero-copy {
            font-size: 22px;
            max-width: 100%;
          }

          .feature-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-top: 32px;
          }

          .feature-title {
            font-size: 24px;
          }

          .feature-copy {
            font-size: 17px;
          }

          .right-title {
            font-size: 54px;
          }

          .right-subtitle {
            font-size: 22px;
          }

          .field-label {
            font-size: 20px;
          }
        }

        @media (max-width: 767px) {
          .login-shell {
            padding: 20px 16px 28px;
          }

          .login-grid {
            gap: 20px;
          }

          .left-card,
          .right-card {
            padding: 24px;
            border-radius: 24px;
          }

          .hero-title {
            margin: 0 0 16px;
            font-size: 42px;
            line-height: 1.02;
          }

          .hero-copy {
            font-size: 18px;
            line-height: 1.55;
          }

          .feature-grid {
            grid-template-columns: 1fr;
            gap: 14px;
            margin-top: 28px;
          }

          .feature-card {
            padding: 18px;
            border-radius: 18px;
          }

          .feature-title {
            font-size: 22px;
          }

          .feature-copy {
            font-size: 16px;
          }

          .right-title {
            font-size: 44px;
          }

          .right-subtitle {
            margin-top: 14px;
            font-size: 18px;
            line-height: 1.55;
          }

          .mode-wrap {
            grid-template-columns: 1fr;
            gap: 8px;
            border-radius: 18px;
            margin-bottom: 20px;
          }

          .mode-btn {
            height: 58px;
            font-size: 18px;
            border-radius: 14px;
          }

          .subtitle-box {
            margin-bottom: 20px;
            padding: 16px 18px;
            border-radius: 18px;
            font-size: 16px;
            line-height: 1.6;
          }

          .form-grid {
            gap: 18px;
          }

          .field {
            gap: 10px;
          }

          .field-label {
            font-size: 18px;
          }

          .submit-btn {
            height: 62px;
            border-radius: 18px;
            font-size: 20px;
          }

          .error-box {
            font-size: 16px;
            padding: 14px 16px;
          }
        }
      `}</style>

      <main className="login-shell">
        <div className="login-grid">
          <section className="left-card">
            <div>
              <h1 className="hero-title">
                A premium learning platform for modern schools.
              </h1>

              <p className="hero-copy">
                Bring together students, teachers, school admins, and platform
                administrators in one polished, role-aware experience.
              </p>
            </div>

            <div className="feature-grid">
              {[
                ["Secure sign-in", "Role-based access"],
                ["Multi-school ready", "Tenant-aware dashboards"],
                ["Elegant workflows", "Fast and focused UI"],
              ].map(([title, desc]) => (
                <div key={title} className="feature-card">
                  <div className="feature-title">{title}</div>
                  <div className="feature-copy">{desc}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="right-card">
            <div style={{ marginBottom: 32 }}>
              <h2 className="right-title">Welcome back</h2>
              <p className="right-subtitle">
                Sign in to continue to your dashboard.
              </p>
            </div>

            <div className="mode-wrap">
              <button
                type="button"
                onClick={() => {
                  setMode("school_user");
                  setError("");
                }}
                className="mode-btn"
                style={{
                  background:
                    mode === "school_user"
                      ? "linear-gradient(135deg, #2563EB, #3B82F6)"
                      : "transparent",
                  color:
                    mode === "school_user"
                      ? "#FFFFFF"
                      : "rgba(255,255,255,0.85)",
                  boxShadow:
                    mode === "school_user"
                      ? "0 8px 20px rgba(37,99,235,0.25)"
                      : "none",
                }}
              >
                School User
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode("platform_admin");
                  setError("");
                }}
                className="mode-btn"
                style={{
                  background:
                    mode === "platform_admin"
                      ? "linear-gradient(135deg, #2563EB, #3B82F6)"
                      : "transparent",
                  color:
                    mode === "platform_admin"
                      ? "#FFFFFF"
                      : "rgba(255,255,255,0.85)",
                  boxShadow:
                    mode === "platform_admin"
                      ? "0 8px 20px rgba(37,99,235,0.25)"
                      : "none",
                }}
              >
                Platform Admin
              </button>
            </div>

            <div className="subtitle-box">{subtitle}</div>

            <form onSubmit={handleSubmit} className="form-grid">
              <label className="field">
                <span className="field-label">Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@school.com"
                  autoComplete="email"
                  style={inputStyle}
                />
              </label>

              <label className="field">
                <span className="field-label">Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  style={inputStyle}
                />
              </label>

              {needsSchoolId ? (
                <label className="field">
                  <span className="field-label">School ID</span>
                  <input
                    type="number"
                    value={schoolId}
                    onChange={(e) => setSchoolId(e.target.value)}
                    placeholder="Enter your school ID"
                    inputMode="numeric"
                    style={inputStyle}
                  />
                </label>
              ) : null}

              {error ? <div className="error-box">{error}</div> : null}

              <button
                type="submit"
                disabled={loading}
                className="submit-btn"
                style={{
                  opacity: loading ? 0.75 : 1,
                  cursor: loading ? "not-allowed" : "pointer",
                }}
                onMouseEnter={(e) => {
                  if (!loading) e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>
            </form>
          </section>
        </div>
      </main>
    </>
  );
}

const inputStyle: CSSProperties = {
  height: 78,
  borderRadius: 22,
  border: "1px solid rgba(255,255,255,0.18)",
  background: "rgba(255,255,255,0.08)",
  padding: "0 24px",
  fontSize: 22,
  color: "#FFFFFF",
  outline: "none",
  boxShadow:
    "0 0 0 1px rgba(255,255,255,0.05), inset 0 1px 2px rgba(15, 23, 42, 0.10)",
  width: "100%",
  boxSizing: "border-box",
};