"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
    BookOpen,
    ClipboardList,
    FileText,
    GraduationCap,
    MessageSquare,
    RefreshCw,
    School,
    Settings,
    UserPlus,
    Users,
} from "lucide-react";

import { apiGet } from "@/lib/api";

type DashboardStats = {
    total_teachers: number;
    total_students: number;
    total_courses: number;
    active_users: number;
};

type UserItem = {
    id: number;
    full_name: string | null;
    email: string;
    role: string;
};

type CoursesResponse = {
    items?: unknown[];
};

type MetricDefinition = {
    title: string;
    description: string;
    value: number;
    icon: typeof Users;
};

const EMPTY_STATS: DashboardStats = {
    total_teachers: 0,
    total_students: 0,
    total_courses: 0,
    active_users: 0,
};

function formatUpdatedTime(value: Date | null): string | null {
    if (!value) {
        return null;
    }

    return value.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatRole(role: string): string {
    return role
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function SchoolAdminDashboardPage() {
    const [stats, setStats] =
        useState<DashboardStats>(EMPTY_STATS);
    const [recentUsers, setRecentUsers] =
        useState<UserItem[]>([]);
    const [loading, setLoading] =
        useState(true);
    const [refreshing, setRefreshing] =
        useState(false);
    const [error, setError] =
        useState<string | null>(null);
    const [lastUpdated, setLastUpdated] =
        useState<Date | null>(null);

    const requestInProgressRef = useRef(false);

    const loadDashboard = useCallback(
        async (showInitialLoader = false) => {
            if (requestInProgressRef.current) {
                return;
            }

            try {
                requestInProgressRef.current = true;
                setError(null);

                if (showInitialLoader) {
                    setLoading(true);
                } else {
                    setRefreshing(true);
                }

                const [users, coursesResponse] =
                    await Promise.all([
                        apiGet<UserItem[]>(
                            "/school-admin/users",
                        ),
                        apiGet<CoursesResponse>(
                            "/courses",
                        ),
                    ]);

                const teachers = users.filter(
                    (user) =>
                        user.role === "teacher",
                );

                const students = users.filter(
                    (user) =>
                        user.role === "student",
                );

                setStats({
                    total_teachers:
                        teachers.length,
                    total_students:
                        students.length,
                    total_courses:
                        coursesResponse.items?.length ??
                        0,
                    active_users: users.length,
                });

                setRecentUsers(users.slice(0, 5));
                setLastUpdated(new Date());
            } catch (err) {
                console.error(err);

                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load dashboard.",
                );
            } finally {
                requestInProgressRef.current = false;
                setLoading(false);
                setRefreshing(false);
            }
        },
        [],
    );

    useEffect(() => {
        void loadDashboard(true);
    }, [loadDashboard]);

    const metrics: MetricDefinition[] = [
        {
            title: "Total Teachers",
            description:
                "Teaching staff currently registered",
            value: stats.total_teachers,
            icon: GraduationCap,
        },
        {
            title: "Total Students",
            description:
                "Students enrolled across the school",
            value: stats.total_students,
            icon: Users,
        },
        {
            title: "Total Courses",
            description:
                "Courses currently available",
            value: stats.total_courses,
            icon: BookOpen,
        },
        {
            title: "Active Users",
            description:
                "All users currently registered",
            value: stats.active_users,
            icon: School,
        },
    ];

    const updatedTime =
        formatUpdatedTime(lastUpdated);

    const isEmpty =
        !loading &&
        metrics.every(
            (metric) => metric.value === 0,
        );

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto w-full max-w-7xl">
                <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-700">
                            School administration
                        </p>

                        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                            School Admin Dashboard
                        </h1>

                        <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
                            Manage users, teaching staff,
                            students, courses, reports and
                            school operations from one place.
                        </p>

                        {updatedTime && (
                            <p className="mt-2 text-sm text-slate-400">
                                Last updated at{" "}
                                {updatedTime}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-3">
                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadDashboard(false);
                            }}
                            disabled={
                                loading || refreshing
                            }
                            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                aria-hidden="true"
                                className={`h-4 w-4 ${refreshing
                                    ? "animate-spin"
                                    : ""
                                    }`}
                            />

                            {refreshing
                                ? "Refreshing..."
                                : "Refresh"}
                        </button>

                        <Link
                            href="/school-admin/users/create"
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                        >
                            <UserPlus
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            Create User
                        </Link>
                    </div>
                </header>

                <div
                    aria-live="polite"
                    className="sr-only"
                >
                    {loading
                        ? "Loading school admin dashboard."
                        : refreshing
                            ? "Refreshing school admin dashboard."
                            : error
                                ? error
                                : "School admin dashboard loaded."}
                </div>

                {error && (
                    <section
                        role="alert"
                        className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5"
                    >
                        <h2 className="text-base font-extrabold text-red-900">
                            Unable to load dashboard
                        </h2>

                        <p className="mt-2 text-sm leading-6 text-red-700">
                            {error}
                        </p>

                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadDashboard(
                                    recentUsers.length === 0,
                                );
                            }}
                            disabled={
                                loading || refreshing
                            }
                            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-red-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            Try again
                        </button>
                    </section>
                )}

                {loading ? (
                    <DashboardSkeleton />
                ) : (
                    <>
                        <section
                            aria-labelledby="admin-overview-heading"
                            className="mt-8"
                        >
                            <div>
                                <h2
                                    id="admin-overview-heading"
                                    className="text-xl font-extrabold text-slate-950"
                                >
                                    School overview
                                </h2>

                                <p className="mt-1 text-sm text-slate-500">
                                    Current school-wide account
                                    and course totals.
                                </p>
                            </div>

                            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                                {metrics.map(
                                    (metric) => (
                                        <DashboardCard
                                            key={
                                                metric.title
                                            }
                                            {...metric}
                                        />
                                    ),
                                )}
                            </div>
                        </section>

                        {isEmpty && (
                            <section className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-8 text-center">
                                <School
                                    aria-hidden="true"
                                    className="mx-auto h-9 w-9 text-slate-400"
                                />

                                <h2 className="mt-3 text-lg font-extrabold text-slate-900">
                                    Your school dashboard is
                                    ready
                                </h2>

                                <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
                                    User and course statistics
                                    will appear here once school
                                    records have been added.
                                </p>
                            </section>
                        )}

                        <section
                            aria-labelledby="quick-actions-heading"
                            className="mt-8"
                        >
                            <h2
                                id="quick-actions-heading"
                                className="text-xl font-extrabold text-slate-950"
                            >
                                Quick actions
                            </h2>

                            <p className="mt-1 text-sm text-slate-500">
                                Open the most frequently used
                                administration areas.
                            </p>

                            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                                <QuickActionCard
                                    href="/school-admin/users"
                                    title="Manage users"
                                    description="View and manage all user accounts."
                                    icon={Users}
                                />

                                <QuickActionCard
                                    href="/school-admin/teachers"
                                    title="Manage teachers"
                                    description="Review teaching staff records."
                                    icon={GraduationCap}
                                />

                                <QuickActionCard
                                    href="/school-admin/students"
                                    title="Manage students"
                                    description="View and maintain student records."
                                    icon={Users}
                                />

                                <QuickActionCard
                                    href="/school-admin/courses"
                                    title="Manage courses"
                                    description="Review courses and teaching allocations."
                                    icon={BookOpen}
                                />

                                <QuickActionCard
                                    href="/school-admin/reports"
                                    title="Review reports"
                                    description="Review, approve and publish student reports."
                                    icon={FileText}
                                />

                                <QuickActionCard
                                    href="/school-admin/report-sessions"
                                    title="Report sessions"
                                    description="Configure reporting windows and fields."
                                    icon={ClipboardList}
                                />

                                <QuickActionCard
                                    href="/school-admin/attendance"
                                    title="Attendance"
                                    description="Review registers and attendance records."
                                    icon={ClipboardList}
                                />

                                <QuickActionCard
                                    href="/messages"
                                    title="Messages"
                                    description="Open school communications."
                                    icon={MessageSquare}
                                />

                                <QuickActionCard
                                    href="/school-admin/classes"
                                    title="Classes"
                                    description="Manage classes and group membership."
                                    icon={Settings}
                                />
                            </div>
                        </section>

                        <section
                            aria-labelledby="recent-users-heading"
                            className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                        >
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <h2
                                        id="recent-users-heading"
                                        className="text-xl font-extrabold text-slate-950"
                                    >
                                        Recent users
                                    </h2>

                                    <p className="mt-1 text-sm text-slate-500">
                                        The first five users
                                        returned by the current
                                        school user list.
                                    </p>
                                </div>

                                <Link
                                    href="/school-admin/users"
                                    className="text-sm font-bold text-blue-700 hover:text-blue-800"
                                >
                                    View all users
                                </Link>
                            </div>

                            {recentUsers.length === 0 ? (
                                <div className="mt-5 rounded-xl border border-dashed border-slate-300 px-5 py-8 text-center">
                                    <p className="font-bold text-slate-800">
                                        No users found
                                    </p>

                                    <p className="mt-1 text-sm text-slate-500">
                                        Create a user to begin
                                        populating this list.
                                    </p>
                                </div>
                            ) : (
                                <div className="mt-5 divide-y divide-slate-100">
                                    {recentUsers.map(
                                        (user) => (
                                            <article
                                                key={
                                                    user.id
                                                }
                                                className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                                            >
                                                <div className="min-w-0">
                                                    <h3 className="truncate font-extrabold text-slate-900">
                                                        {user.full_name ||
                                                            "Unnamed User"}
                                                    </h3>

                                                    <p className="mt-1 truncate text-sm text-slate-500">
                                                        {
                                                            user.email
                                                        }
                                                    </p>
                                                </div>

                                                <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
                                                    {formatRole(
                                                        user.role,
                                                    )}
                                                </span>
                                            </article>
                                        ),
                                    )}
                                </div>
                            )}
                        </section>
                    </>
                )}
            </div>
        </main>
    );
}

function DashboardCard({
    title,
    value,
    description,
    icon: Icon,
}: MetricDefinition) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm font-bold text-slate-500">
                        {title}
                    </p>

                    <p className="mt-3 text-4xl font-extrabold tracking-tight text-slate-950">
                        {value.toLocaleString(
                            "en-GB",
                        )}
                    </p>
                </div>

                <div className="rounded-2xl bg-blue-50 p-3 text-blue-700">
                    <Icon
                        aria-hidden="true"
                        className="h-6 w-6"
                    />
                </div>
            </div>

            <p className="mt-4 text-sm leading-6 text-slate-500">
                {description}
            </p>
        </article>
    );
}

function QuickActionCard({
    href,
    title,
    description,
    icon: Icon,
}: {
    href: string;
    title: string;
    description: string;
    icon: typeof Users;
}) {
    return (
        <Link
            href={href}
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        >
            <div className="flex items-start gap-4">
                <div className="rounded-2xl bg-slate-100 p-3 text-slate-700 transition group-hover:bg-blue-50 group-hover:text-blue-700">
                    <Icon
                        aria-hidden="true"
                        className="h-6 w-6"
                    />
                </div>

                <div>
                    <h3 className="font-extrabold text-slate-950">
                        {title}
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-slate-500">
                        {description}
                    </p>
                </div>
            </div>
        </Link>
    );
}

function DashboardSkeleton() {
    return (
        <section
            aria-label="Loading dashboard summary"
            className="mt-8"
        >
            <div className="h-7 w-40 animate-pulse rounded bg-slate-200" />
            <div className="mt-2 h-4 w-64 max-w-full animate-pulse rounded bg-slate-100" />

            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map(
                    (_, index) => (
                        <div
                            key={index}
                            className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                        >
                            <div className="flex items-start justify-between">
                                <div className="h-4 w-28 rounded bg-slate-200" />
                                <div className="h-12 w-12 rounded-2xl bg-slate-100" />
                            </div>

                            <div className="mt-5 h-10 w-20 rounded bg-slate-200" />
                            <div className="mt-5 h-4 w-full rounded bg-slate-100" />
                            <div className="mt-2 h-4 w-4/5 rounded bg-slate-100" />
                        </div>
                    ),
                )}
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }).map(
                    (_, index) => (
                        <div
                            key={index}
                            className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white"
                        />
                    ),
                )}
            </div>
        </section>
    );
}
