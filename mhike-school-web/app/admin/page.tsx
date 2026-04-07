"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearToken, getToken } from "@/lib/api";
import DashboardShell from "@/components/layout/DashboardShell";
import SchoolHero from "@/components/school/SchoolHero";
import SchoolStatsCards from "@/components/school/SchoolStatsCards";
import {
    AdminCourseOut,
    AdminCoursesResponse,
    AdminStatsOut,
    AdminUserOut,
    AdminUsersResponse,
    PlatformSchoolSummaryOut,
    deleteCourseAdmin,
    getAdminCourses,
    getAdminStats,
    getAdminUsers,
    getPlatformSchools,
    setCoursePublished,
    toggleUserActive,
    updateUserRole,
} from "@/lib/adminApi";

<div className="mb-6 rounded-2xl bg-red-500 p-6 text-2xl font-bold text-white">
    Tailwind test
</div>

function cardStyle(): React.CSSProperties {
    return {
        background: "rgba(255,255,255,0.96)",
        border: "1px solid #E2E8F0",
        borderRadius: 24,
        padding: 22,
        boxShadow: "0 12px 32px rgba(15, 23, 42, 0.06)",
        backdropFilter: "blur(10px)",
    };
}

function actionButtonStyle(
    kind: "primary" | "secondary" | "danger" = "secondary",
    disabled = false
): React.CSSProperties {
    const styles: Record<string, React.CSSProperties> = {
        primary: {
            background: "linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)",
            color: "#FFFFFF",
            border: "1px solid #2563EB",
            boxShadow: "0 10px 24px rgba(37, 99, 235, 0.18)",
        },
        secondary: {
            background: "#FFFFFF",
            color: "#0F172A",
            border: "1px solid #E2E8F0",
        },
        danger: {
            background: "#FEF2F2",
            color: "#991B1B",
            border: "1px solid #FECACA",
        },
    };

    return {
        padding: "10px 14px",
        borderRadius: 12,
        fontWeight: 800,
        fontSize: 14,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.65 : 1,
        transition: "all 160ms ease",
        ...styles[kind],
    };
}

function Badge({
    text,
    kind = "neutral",
}: {
    text: string;
    kind?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
    const styles: Record<string, React.CSSProperties> = {
        neutral: {
            background: "#F3F4F6",
            color: "#374151",
        },
        success: {
            background: "#DCFCE7",
            color: "#166534",
        },
        warning: {
            background: "#FEF3C7",
            color: "#92400E",
        },
        danger: {
            background: "#FEE2E2",
            color: "#991B1B",
        },
        info: {
            background: "#DBEAFE",
            color: "#1D4ED8",
        },
    };

    return (
        <span
            style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "6px 10px",
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 800,
                ...styles[kind],
            }}
        >
            {text}
        </span>
    );
}

function sectionTitleStyle(): React.CSSProperties {
    return {
        margin: 0,
        fontSize: 28,
        fontWeight: 900,
        letterSpacing: "-0.02em",
        color: "#0F172A",
    };
}

function roleBadge(role: string) {
    if (role === "platform_admin") return <Badge text="Platform Admin" kind="danger" />;
    if (role === "admin") return <Badge text="Admin" kind="danger" />;
    if (role === "teacher") return <Badge text="Teacher" kind="info" />;
    return <Badge text="Student" kind="neutral" />;
}

function courseBadge(published: boolean) {
    return published ? (
        <Badge text="Published" kind="success" />
    ) : (
        <Badge text="Draft" kind="warning" />
    );
}

export default function AdminPage() {
    const router = useRouter();

    const [token, setToken] = useState("");
    const [stats, setStats] = useState<AdminStatsOut | null>(null);
    const [schools, setSchools] = useState<PlatformSchoolSummaryOut[]>([]);
    const [usersRes, setUsersRes] = useState<AdminUsersResponse | null>(null);
    const [coursesRes, setCoursesRes] = useState<AdminCoursesResponse | null>(null);

    const [selectedSchoolId, setSelectedSchoolId] = useState<number | null>(null);

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [busyKey, setBusyKey] = useState("");

    useEffect(() => {
        const t = getToken();

        if (!t) {
            setLoading(false);
            router.push("/login");
            return;
        }

        setToken(t);
    }, [router]);

    async function loadOverview(authToken: string, silent = false) {
        if (!silent) setLoading(true);
        if (silent) setRefreshing(true);
        setError("");

        try {
            const [statsData, schoolsData] = await Promise.all([
                getAdminStats(authToken),
                getPlatformSchools(authToken),
            ]);

            setStats(statsData);
            setSchools(schoolsData);
        } catch (e: unknown) {
            const message =
                e instanceof Error ? e.message : "Failed to load platform overview";

            setError(message);

            if (
                message.includes("401") ||
                message.includes("403") ||
                message.toLowerCase().includes("forbidden")
            ) {
                clearToken();
                router.push("/login");
            }
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }

    async function loadSchoolData(authToken: string, schoolId: number, silent = false) {
        if (silent) setRefreshing(true);
        setError("");

        try {
            const [usersData, coursesData] = await Promise.all([
                getAdminUsers(authToken, { school_id: schoolId, skip: 0, limit: 8 }),
                getAdminCourses(authToken, { school_id: schoolId, skip: 0, limit: 8 }),
            ]);

            setUsersRes(usersData);
            setCoursesRes(coursesData);
        } catch (e: unknown) {
            const message = e instanceof Error ? e.message : "Failed to load school data";
            setError(message);
        } finally {
            setRefreshing(false);
        }
    }

    useEffect(() => {
        if (!token) return;
        void loadOverview(token);
    }, [token]);

    useEffect(() => {
        if (!token || selectedSchoolId == null) {
            setUsersRes(null);
            setCoursesRes(null);
            return;
        }

        void loadSchoolData(token, selectedSchoolId);
    }, [token, selectedSchoolId]);

    async function handleRoleChange(
        userId: number,
        role: "student" | "teacher" | "admin"
    ) {
        if (!token || selectedSchoolId == null) return;

        const key = `role-${userId}-${role}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await updateUserRole(token, userId, role);
            setSuccess("User role updated.");
            await loadSchoolData(token, selectedSchoolId, true);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to update user role");
        } finally {
            setBusyKey("");
        }
    }

    async function handleToggleActive(userId: number, nextActive: boolean) {
        if (!token || selectedSchoolId == null) return;

        const key = `active-${userId}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await toggleUserActive(token, userId, nextActive);
            setSuccess(nextActive ? "User activated." : "User deactivated.");
            await loadSchoolData(token, selectedSchoolId, true);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to update user status");
        } finally {
            setBusyKey("");
        }
    }

    async function handleSetPublished(courseId: number, published: boolean) {
        if (!token || selectedSchoolId == null) return;

        const key = `publish-${courseId}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await setCoursePublished(token, courseId, published);
            setSuccess(published ? "Course published." : "Course unpublished.");
            await loadSchoolData(token, selectedSchoolId, true);
        } catch (e: unknown) {
            setError(
                e instanceof Error ? e.message : "Failed to update course publication"
            );
        } finally {
            setBusyKey("");
        }
    }

    async function handleDeleteCourse(courseId: number, title: string) {
        if (!token || selectedSchoolId == null) return;

        const confirmed = window.confirm(`Delete "${title}"?`);
        if (!confirmed) return;

        const key = `delete-${courseId}`;
        setBusyKey(key);
        setError("");
        setSuccess("");

        try {
            await deleteCourseAdmin(token, courseId);
            setSuccess("Course deleted.");
            await loadSchoolData(token, selectedSchoolId, true);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to delete course");
        } finally {
            setBusyKey("");
        }
    }

    const users: AdminUserOut[] = usersRes?.items ?? [];
    const courses: AdminCourseOut[] = coursesRes?.items ?? [];

    const recentUsers = useMemo(() => users.slice(0, 8), [users]);
    const recentCourses = useMemo(() => courses.slice(0, 8), [courses]);

    const selectedSchool = useMemo(
        () => schools.find((s) => s.id === selectedSchoolId) ?? null,
        [schools, selectedSchoolId]
    );

    const derived = useMemo(() => {
        const draftCourses = Math.max(
            0,
            (stats?.total_courses ?? 0) - (stats?.published_courses ?? 0)
        );

        const publishedRate =
            stats && stats.total_courses > 0
                ? Math.round((stats.published_courses / stats.total_courses) * 100)
                : 0;

        return {
            draftCourses,
            publishedRate,
            scopeLabel: "Global platform",
        };
    }, [stats]);

    const handleRefresh = () => {
        if (!token) return;
        void loadOverview(token, true);
        if (selectedSchoolId != null) {
            void loadSchoolData(token, selectedSchoolId, true);
        }
    };

    const statItems = useMemo(
        () => [
            {
                label: "Total users",
                value: stats?.total_users ?? 0,
                tone: "blue" as const,
            },
            {
                label: "Total students",
                value: stats?.total_students ?? 0,
            },
            {
                label: "Total teachers",
                value: stats?.total_teachers ?? 0,
            },
            {
                label: "Total admins",
                value: stats?.total_admins ?? 0,
            },
            {
                label: "Total courses",
                value: stats?.total_courses ?? 0,
            },
            {
                label: "Published courses",
                value: stats?.published_courses ?? 0,
                tone: "green" as const,
            },
            {
                label: "Draft courses",
                value: derived.draftCourses,
            },
            {
                label: "Total enrollments",
                value: stats?.total_enrollments ?? 0,
            },
        ],
        [stats, derived.draftCourses]
    );

    if (loading) {
        return (
            <DashboardShell
                userName="Platform Admin"
                schoolName="Global platform"
                showRefresh={false}
                showSidebar={false}
                showLogout={true}
                contentClassName="bg-[linear-gradient(180deg,#F8FAFC_0%,#EEF4FF_100%)]"
            >
                <div style={cardStyle()}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: "#0F172A" }}>
                        Loading platform admin dashboard...
                    </div>
                </div>
            </DashboardShell>
        );
    }

    return (
        <DashboardShell
            userName="Platform Admin"
            schoolName={derived.scopeLabel}
            showSidebar={false}
            showRefresh={true}
            refreshLabel={refreshing ? "Refreshing..." : "Refresh"}
            onRefresh={handleRefresh}
            showLogout={true}
            contentClassName="bg-[linear-gradient(180deg,#F8FAFC_0%,#EEF4FF_100%)]"
        >
            <div style={{ maxWidth: 1320, margin: "0 auto" }}>
                <SchoolHero
                    schoolName="Global platform"
                    roleLabel="Platform admin dashboard"
                    title="Manage Mhike School LMS"
                    subtitle="Monitor schools, users, courses, publications, and enrollments across the platform. Select a school below to manage its users and courses."
                    actions={[
                        {
                            label: "Main Dashboard",
                            href: "/dashboard",
                            variant: "primary",
                        },
                        {
                            label: "Teacher View",
                            href: "/teacher",
                            variant: "secondary",
                        },
                    ]}
                    rightContent={
                        <div className="flex h-full min-h-[180px] w-full flex-col justify-between text-white">
                            <div>
                                <div className="text-sm font-medium text-white/80">
                                    System snapshot
                                </div>
                                <div className="mt-3 text-4xl font-black tracking-tight">
                                    {stats?.total_users ?? 0}
                                </div>
                                <div className="mt-1 text-sm text-white/80">
                                    active users across platform
                                </div>
                            </div>

                            <div className="mt-5 flex flex-wrap gap-2">
                                <Badge text="Operational" kind="success" />
                                <Badge text={`${schools.length} schools`} kind="info" />
                            </div>

                            <div className="mt-5 grid grid-cols-2 gap-3">
                                <div className="rounded-2xl bg-white/10 px-4 py-3">
                                    <div className="text-xs text-white/70">Courses</div>
                                    <div className="mt-1 text-xl font-extrabold">
                                        {stats?.total_courses ?? 0}
                                    </div>
                                </div>
                                <div className="rounded-2xl bg-white/10 px-4 py-3">
                                    <div className="text-xs text-white/70">Enrollments</div>
                                    <div className="mt-1 text-xl font-extrabold">
                                        {stats?.total_enrollments ?? 0}
                                    </div>
                                </div>
                            </div>
                        </div>
                    }
                />

                {error ? (
                    <div
                        style={{
                            marginTop: 16,
                            padding: 14,
                            borderRadius: 16,
                            background: "#FEF2F2",
                            color: "#991B1B",
                            border: "1px solid #FECACA",
                            fontWeight: 600,
                            fontSize: 15,
                        }}
                    >
                        {error}
                    </div>
                ) : null}

                {success ? (
                    <div
                        style={{
                            marginTop: 16,
                            padding: 14,
                            borderRadius: 16,
                            background: "#ECFDF5",
                            color: "#065F46",
                            border: "1px solid #A7F3D0",
                            fontWeight: 600,
                            fontSize: 15,
                        }}
                    >
                        {success}
                    </div>
                ) : null}

                <div style={{ marginTop: 18 }}>
                    <SchoolStatsCards items={statItems} />
                </div>

                <section style={{ marginTop: 22 }}>
                    <div style={cardStyle()}>
                        <div
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                gap: 12,
                                marginBottom: 16,
                                flexWrap: "wrap",
                            }}
                        >
                            <div>
                                <h2 style={sectionTitleStyle()}>Schools</h2>
                                <p
                                    style={{
                                        margin: "8px 0 0 0",
                                        color: "#64748B",
                                        fontSize: 15,
                                    }}
                                >
                                    Select a school to view and manage its users and courses.
                                </p>
                            </div>

                            <div style={{ minWidth: 280 }}>
                                <select
                                    value={selectedSchoolId ?? ""}
                                    onChange={(e) => {
                                        const value = e.target.value;
                                        setSelectedSchoolId(value ? Number(value) : null);
                                        setSuccess("");
                                        setError("");
                                    }}
                                    style={{
                                        width: "100%",
                                        padding: "12px 14px",
                                        borderRadius: 14,
                                        border: "1px solid #E2E8F0",
                                        fontSize: 15,
                                        background: "white",
                                        color: "#0F172A",
                                    }}
                                >
                                    <option value="">Select a school</option>
                                    {schools.map((school) => (
                                        <option key={school.id} value={school.id}>
                                            {school.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {schools.length === 0 ? (
                            <div style={{ color: "#6B7280", fontSize: 15 }}>
                                No schools found.
                            </div>
                        ) : (
                            <div
                                style={{
                                    display: "grid",
                                    gridTemplateColumns:
                                        "repeat(auto-fit, minmax(260px, 1fr))",
                                    gap: 14,
                                }}
                            >
                                {schools.map((school) => {
                                    const isSelected = selectedSchoolId === school.id;

                                    return (
                                        <button
                                            key={school.id}
                                            type="button"
                                            onClick={() => {
                                                setSelectedSchoolId(school.id);
                                                setSuccess("");
                                                setError("");
                                            }}
                                            style={{
                                                textAlign: "left",
                                                borderRadius: 20,
                                                border: isSelected
                                                    ? "2px solid #2563EB"
                                                    : "1px solid #E2E8F0",
                                                background: isSelected
                                                    ? "linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%)"
                                                    : "#F8FAFC",
                                                padding: 18,
                                                cursor: "pointer",
                                                boxShadow: isSelected
                                                    ? "0 10px 24px rgba(37, 99, 235, 0.10)"
                                                    : "none",
                                                transition: "all 160ms ease",
                                            }}
                                        >
                                            <div
                                                style={{
                                                    fontWeight: 900,
                                                    fontSize: 18,
                                                    color: "#0F172A",
                                                }}
                                            >
                                                {school.name}
                                            </div>

                                            <div
                                                style={{
                                                    marginTop: 12,
                                                    display: "grid",
                                                    gap: 6,
                                                    color: "#475569",
                                                    fontSize: 14,
                                                }}
                                            >
                                                <div>{school.total_users} users</div>
                                                <div>{school.total_students} students</div>
                                                <div>{school.total_teachers} teachers</div>
                                                <div>{school.total_courses} courses</div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </section>

                <section
                    style={{
                        marginTop: 22,
                        display: "grid",
                        gridTemplateColumns: "minmax(0, 1.25fr) minmax(340px, 1fr)",
                        gap: 16,
                        alignItems: "start",
                    }}
                >
                    <div style={{ display: "grid", gap: 16 }}>
                        <div style={cardStyle()}>
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    gap: 12,
                                    marginBottom: 14,
                                    flexWrap: "wrap",
                                }}
                            >
                                <div>
                                    <h2 style={sectionTitleStyle()}>Users</h2>
                                    <p
                                        style={{
                                            margin: "8px 0 0 0",
                                            color: "#64748B",
                                            fontSize: 15,
                                        }}
                                    >
                                        {selectedSchool
                                            ? `Manage roles and account status for ${selectedSchool.name}.`
                                            : "Select a school to view users."}
                                    </p>
                                </div>
                                <Badge text={`${usersRes?.total ?? 0} total`} kind="info" />
                            </div>

                            {!selectedSchool ? (
                                <div style={{ color: "#6B7280", fontSize: 15 }}>
                                    Select a school to view users.
                                </div>
                            ) : recentUsers.length === 0 ? (
                                <div style={{ color: "#6B7280", fontSize: 15 }}>
                                    No users found for this school.
                                </div>
                            ) : (
                                <div style={{ display: "grid", gap: 12 }}>
                                    {recentUsers.map((user) => {
                                        const isPlatformAdminUser =
                                            user.role === "platform_admin";
                                        const isDisabled =
                                            busyKey !== "" || isPlatformAdminUser;

                                        return (
                                            <div
                                                key={user.id}
                                                style={{
                                                    border: "1px solid #E2E8F0",
                                                    borderRadius: 18,
                                                    padding: 16,
                                                    background: "#F8FAFC",
                                                    display: "grid",
                                                    gap: 12,
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        display: "flex",
                                                        justifyContent: "space-between",
                                                        gap: 12,
                                                        alignItems: "center",
                                                        flexWrap: "wrap",
                                                    }}
                                                >
                                                    <div>
                                                        <div
                                                            style={{
                                                                fontWeight: 900,
                                                                fontSize: 17,
                                                                color: "#0F172A",
                                                            }}
                                                        >
                                                            {user.full_name || "Unnamed user"}
                                                        </div>
                                                        <div
                                                            style={{
                                                                marginTop: 6,
                                                                color: "#64748B",
                                                                fontSize: 14,
                                                            }}
                                                        >
                                                            {user.email}
                                                        </div>
                                                    </div>

                                                    <div
                                                        style={{
                                                            display: "flex",
                                                            gap: 8,
                                                            alignItems: "center",
                                                            flexWrap: "wrap",
                                                        }}
                                                    >
                                                        {roleBadge(user.role)}
                                                        {user.is_active === false ? (
                                                            <Badge text="Inactive" kind="danger" />
                                                        ) : (
                                                            <Badge text="Active" kind="success" />
                                                        )}
                                                    </div>
                                                </div>

                                                <div
                                                    style={{
                                                        display: "flex",
                                                        gap: 8,
                                                        flexWrap: "wrap",
                                                    }}
                                                >
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleRoleChange(user.id, "student")
                                                        }
                                                        disabled={isDisabled}
                                                        style={actionButtonStyle(
                                                            "secondary",
                                                            isDisabled
                                                        )}
                                                    >
                                                        Make Student
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleRoleChange(user.id, "teacher")
                                                        }
                                                        disabled={isDisabled}
                                                        style={actionButtonStyle(
                                                            "primary",
                                                            isDisabled
                                                        )}
                                                    >
                                                        Promote Teacher
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleRoleChange(user.id, "admin")
                                                        }
                                                        disabled={isDisabled}
                                                        style={actionButtonStyle(
                                                            "danger",
                                                            isDisabled
                                                        )}
                                                    >
                                                        Make Admin
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleToggleActive(
                                                                user.id,
                                                                user.is_active === false
                                                            )
                                                        }
                                                        disabled={isDisabled}
                                                        style={actionButtonStyle(
                                                            "secondary",
                                                            isDisabled
                                                        )}
                                                    >
                                                        {user.is_active === false
                                                            ? "Activate"
                                                            : "Deactivate"}
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div style={cardStyle()}>
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    gap: 12,
                                    marginBottom: 14,
                                    flexWrap: "wrap",
                                }}
                            >
                                <div>
                                    <h2 style={sectionTitleStyle()}>Courses</h2>
                                    <p
                                        style={{
                                            margin: "8px 0 0 0",
                                            color: "#64748B",
                                            fontSize: 15,
                                        }}
                                    >
                                        {selectedSchool
                                            ? `Moderate course publication for ${selectedSchool.name}.`
                                            : "Select a school to view courses."}
                                    </p>
                                </div>
                                <Badge text={`${coursesRes?.total ?? 0} total`} kind="info" />
                            </div>

                            {!selectedSchool ? (
                                <div style={{ color: "#6B7280", fontSize: 15 }}>
                                    Select a school to view courses.
                                </div>
                            ) : recentCourses.length === 0 ? (
                                <div style={{ color: "#6B7280", fontSize: 15 }}>
                                    No courses found for this school.
                                </div>
                            ) : (
                                <div style={{ display: "grid", gap: 12 }}>
                                    {recentCourses.map((course) => {
                                        const isBusy = busyKey !== "";

                                        return (
                                            <div
                                                key={course.id}
                                                style={{
                                                    border: "1px solid #E2E8F0",
                                                    borderRadius: 18,
                                                    padding: 16,
                                                    background: "#F8FAFC",
                                                    display: "grid",
                                                    gap: 12,
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        display: "flex",
                                                        justifyContent: "space-between",
                                                        alignItems: "flex-start",
                                                        gap: 10,
                                                        flexWrap: "wrap",
                                                    }}
                                                >
                                                    <div>
                                                        <div
                                                            style={{
                                                                fontWeight: 900,
                                                                fontSize: 17,
                                                                color: "#0F172A",
                                                            }}
                                                        >
                                                            {course.title}
                                                        </div>

                                                        <div
                                                            style={{
                                                                marginTop: 6,
                                                                color: "#6B7280",
                                                                fontSize: 14,
                                                            }}
                                                        >
                                                            {course.teacher_name
                                                                ? `Teacher: ${course.teacher_name}`
                                                                : `Teacher ID: ${course.teacher_id}`}
                                                        </div>

                                                        {course.description ? (
                                                            <div
                                                                style={{
                                                                    marginTop: 8,
                                                                    color: "#475569",
                                                                    fontSize: 14,
                                                                    lineHeight: 1.55,
                                                                }}
                                                            >
                                                                {course.description}
                                                            </div>
                                                        ) : null}
                                                    </div>

                                                    <div>{courseBadge(course.published)}</div>
                                                </div>

                                                <div
                                                    style={{
                                                        display: "flex",
                                                        gap: 8,
                                                        flexWrap: "wrap",
                                                    }}
                                                >
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleSetPublished(
                                                                course.id,
                                                                !course.published
                                                            )
                                                        }
                                                        disabled={isBusy}
                                                        style={actionButtonStyle(
                                                            course.published
                                                                ? "secondary"
                                                                : "primary",
                                                            isBusy
                                                        )}
                                                    >
                                                        {course.published ? "Unpublish" : "Publish"}
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            void handleDeleteCourse(
                                                                course.id,
                                                                course.title
                                                            )
                                                        }
                                                        disabled={isBusy}
                                                        style={actionButtonStyle("danger", isBusy)}
                                                    >
                                                        Delete Course
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>

                    <div style={{ display: "grid", gap: 16 }}>
                        <div style={cardStyle()}>
                            <h2 style={sectionTitleStyle()}>Publishing overview</h2>

                            <div
                                style={{
                                    color: "#6B7280",
                                    marginTop: 8,
                                    marginBottom: 18,
                                    fontSize: 15,
                                }}
                            >
                                Quick view of course publishing health across the platform.
                            </div>

                            <div
                                style={{
                                    marginBottom: 10,
                                    display: "flex",
                                    justifyContent: "space-between",
                                }}
                            >
                                <span
                                    style={{
                                        color: "#475569",
                                        fontWeight: 700,
                                        fontSize: 15,
                                    }}
                                >
                                    Published rate
                                </span>
                                <span style={{ fontWeight: 900, fontSize: 15 }}>
                                    {derived.publishedRate}%
                                </span>
                            </div>

                            <div
                                style={{
                                    height: 12,
                                    width: "100%",
                                    background: "#E5E7EB",
                                    borderRadius: 999,
                                    overflow: "hidden",
                                }}
                            >
                                <div
                                    style={{
                                        width: `${derived.publishedRate}%`,
                                        height: "100%",
                                        background:
                                            "linear-gradient(90deg, #2563EB 0%, #60A5FA 100%)",
                                    }}
                                />
                            </div>

                            <div
                                style={{
                                    display: "grid",
                                    gap: 10,
                                    marginTop: 18,
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        padding: "12px 14px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <span
                                        style={{
                                            color: "#475569",
                                            fontWeight: 700,
                                            fontSize: 15,
                                        }}
                                    >
                                        Published
                                    </span>
                                    <strong>{stats?.published_courses ?? 0}</strong>
                                </div>

                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        padding: "12px 14px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <span
                                        style={{
                                            color: "#475569",
                                            fontWeight: 700,
                                            fontSize: 15,
                                        }}
                                    >
                                        Draft
                                    </span>
                                    <strong>{derived.draftCourses}</strong>
                                </div>

                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        padding: "12px 14px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <span
                                        style={{
                                            color: "#475569",
                                            fontWeight: 700,
                                            fontSize: 15,
                                        }}
                                    >
                                        Enrollments
                                    </span>
                                    <strong>{stats?.total_enrollments ?? 0}</strong>
                                </div>
                            </div>
                        </div>

                        <div style={cardStyle()}>
                            <h2 style={sectionTitleStyle()}>Quick actions</h2>

                            <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
                                <Link
                                    href="/teacher"
                                    style={{
                                        textDecoration: "none",
                                        padding: "14px 16px",
                                        borderRadius: 14,
                                        background:
                                            "linear-gradient(90deg, #2563EB 0%, #3B82F6 100%)",
                                        color: "#FFFFFF",
                                        fontWeight: 800,
                                        fontSize: 15,
                                        boxShadow: "0 10px 24px rgba(37, 99, 235, 0.16)",
                                    }}
                                >
                                    Open teacher dashboard
                                </Link>

                                <Link
                                    href="/courses"
                                    style={{
                                        textDecoration: "none",
                                        padding: "14px 16px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        color: "#0F172A",
                                        fontWeight: 800,
                                        border: "1px solid #E5E7EB",
                                        fontSize: 15,
                                    }}
                                >
                                    Browse course catalog
                                </Link>

                                <button
                                    type="button"
                                    onClick={handleRefresh}
                                    disabled={refreshing}
                                    style={{
                                        textAlign: "left",
                                        padding: "14px 16px",
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        color: "#0F172A",
                                        fontWeight: 800,
                                        border: "1px solid #E5E7EB",
                                        cursor: refreshing ? "not-allowed" : "pointer",
                                        opacity: refreshing ? 0.7 : 1,
                                        fontSize: 15,
                                    }}
                                >
                                    {refreshing
                                        ? "Refreshing admin data..."
                                        : "Refresh admin data"}
                                </button>
                            </div>
                        </div>

                        <div style={cardStyle()}>
                            <h2 style={sectionTitleStyle()}>Platform summary</h2>

                            <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
                                <div
                                    style={{
                                        padding: 14,
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <div style={{ fontSize: 14, color: "#6B7280" }}>User mix</div>
                                    <div
                                        style={{
                                            marginTop: 6,
                                            fontWeight: 800,
                                            color: "#0F172A",
                                            fontSize: 15,
                                        }}
                                    >
                                        {stats?.total_students ?? 0} students •{" "}
                                        {stats?.total_teachers ?? 0} teachers •{" "}
                                        {stats?.total_admins ?? 0} admins
                                    </div>
                                </div>

                                <div
                                    style={{
                                        padding: 14,
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <div style={{ fontSize: 14, color: "#6B7280" }}>
                                        Course health
                                    </div>
                                    <div
                                        style={{
                                            marginTop: 6,
                                            fontWeight: 800,
                                            color: "#0F172A",
                                            fontSize: 15,
                                        }}
                                    >
                                        {stats?.total_courses ?? 0} total courses with{" "}
                                        {stats?.published_courses ?? 0} published
                                    </div>
                                </div>

                                <div
                                    style={{
                                        padding: 14,
                                        borderRadius: 14,
                                        background: "#F8FAFC",
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    <div style={{ fontSize: 14, color: "#6B7280" }}>
                                        Learning activity
                                    </div>
                                    <div
                                        style={{
                                            marginTop: 6,
                                            fontWeight: 800,
                                            color: "#0F172A",
                                            fontSize: 15,
                                        }}
                                    >
                                        {stats?.total_enrollments ?? 0} enrollments recorded on
                                        the platform
                                    </div>
                                </div>

                                {selectedSchool ? (
                                    <div
                                        style={{
                                            padding: 14,
                                            borderRadius: 14,
                                            background: "#EFF6FF",
                                            border: "1px solid #BFDBFE",
                                        }}
                                    >
                                        <div style={{ fontSize: 14, color: "#1D4ED8" }}>
                                            Selected school
                                        </div>
                                        <div
                                            style={{
                                                marginTop: 6,
                                                fontWeight: 900,
                                                color: "#0F172A",
                                                fontSize: 16,
                                            }}
                                        >
                                            {selectedSchool.name}
                                        </div>
                                        <div
                                            style={{
                                                marginTop: 8,
                                                color: "#475569",
                                                fontSize: 14,
                                            }}
                                        >
                                            {selectedSchool.total_users} users •{" "}
                                            {selectedSchool.total_courses} courses
                                        </div>
                                    </div>
                                ) : null}
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </DashboardShell>
    );
}