"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
    BookOpen,
    ClipboardCheck,
    FileText,
    GraduationCap,
    MessageSquare,
    RefreshCw,
    Users,
} from "lucide-react";

import RoleGate from "@/components/auth/RoleGate";
import {
    getTeacherDashboard,
    type TeacherDashboard,
} from "@/lib/services/teacher";
import { UserRole } from "@/types/user";

type DashboardMetric = {
    label: string;
    value: number;
    description: string;
    icon: typeof BookOpen;
};

const METRIC_DEFINITIONS: Array<
    Omit<DashboardMetric, "value">
> = [
        {
            label: "Courses",
            description: "Courses currently assigned to you",
            icon: BookOpen,
        },
        {
            label: "Students",
            description: "Students across your courses",
            icon: Users,
        },
        {
            label: "Assignments",
            description: "Assignments created for your classes",
            icon: FileText,
        },
        {
            label: "Pending grading",
            description: "Submissions waiting to be marked",
            icon: ClipboardCheck,
        },
    ];

function formatUpdatedTime(value: Date | null): string | null {
    if (!value) {
        return null;
    }

    return value.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

export default function TeacherPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherDashboardContent />
        </RoleGate>
    );
}

function TeacherDashboardContent() {
    const [data, setData] =
        useState<TeacherDashboard | null>(null);
    const [isLoading, setIsLoading] =
        useState(true);
    const [isRefreshing, setIsRefreshing] =
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
                    setIsLoading(true);
                } else {
                    setIsRefreshing(true);
                }

                const dashboard =
                    await getTeacherDashboard();

                setData(dashboard);
                setLastUpdated(new Date());
            } catch (err) {
                console.error(err);

                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load teacher dashboard.",
                );
            } finally {
                requestInProgressRef.current = false;
                setIsLoading(false);
                setIsRefreshing(false);
            }
        },
        [],
    );

    useEffect(() => {
        void loadDashboard(true);
    }, [loadDashboard]);

    const metrics: DashboardMetric[] = data
        ? [
            {
                ...METRIC_DEFINITIONS[0],
                value: data.total_courses,
            },
            {
                ...METRIC_DEFINITIONS[1],
                value: data.total_students,
            },
            {
                ...METRIC_DEFINITIONS[2],
                value: data.total_assignments,
            },
            {
                ...METRIC_DEFINITIONS[3],
                value: data.pending_submissions,
            },
        ]
        : [];

    const isEmpty =
        Boolean(data) &&
        metrics.every((metric) => metric.value === 0);

    const updatedTime =
        formatUpdatedTime(lastUpdated);

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto w-full max-w-7xl">
                <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-700">
                            Teacher workspace
                        </p>

                        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                            Teacher Dashboard
                        </h1>

                        <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
                            Review your courses, students,
                            assignments and current grading
                            workload.
                        </p>

                        {updatedTime && (
                            <p className="mt-2 text-sm text-slate-400">
                                Last updated at {updatedTime}
                            </p>
                        )}
                    </div>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() => {
                            void loadDashboard(false);
                        }}
                        disabled={
                            isLoading || isRefreshing
                        }
                        className="inline-flex w-fit items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        <RefreshCw
                            aria-hidden="true"
                            className={`h-4 w-4 ${isRefreshing
                                ? "animate-spin"
                                : ""
                                }`}
                        />

                        {isRefreshing
                            ? "Refreshing..."
                            : "Refresh"}
                    </button>
                </header>

                <div
                    aria-live="polite"
                    className="sr-only"
                >
                    {isLoading
                        ? "Loading teacher dashboard."
                        : isRefreshing
                            ? "Refreshing teacher dashboard."
                            : error
                                ? error
                                : "Teacher dashboard loaded."}
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
                                    !data,
                                );
                            }}
                            disabled={
                                isLoading ||
                                isRefreshing
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

                {isLoading && !data ? (
                    <DashboardSkeleton />
                ) : data ? (
                    <>
                        <section
                            aria-labelledby="dashboard-overview-heading"
                            className="mt-8"
                        >
                            <div className="flex items-end justify-between gap-4">
                                <div>
                                    <h2
                                        id="dashboard-overview-heading"
                                        className="text-xl font-extrabold text-slate-950"
                                    >
                                        Overview
                                    </h2>

                                    <p className="mt-1 text-sm text-slate-500">
                                        Your current teaching
                                        activity at a glance.
                                    </p>
                                </div>
                            </div>

                            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                                {metrics.map(
                                    (metric) => (
                                        <MetricCard
                                            key={
                                                metric.label
                                            }
                                            {...metric}
                                        />
                                    ),
                                )}
                            </div>
                        </section>

                        {isEmpty && (
                            <section className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-8 text-center">
                                <GraduationCap
                                    aria-hidden="true"
                                    className="mx-auto h-9 w-9 text-slate-400"
                                />

                                <h2 className="mt-3 text-lg font-extrabold text-slate-900">
                                    Your dashboard is ready
                                </h2>

                                <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
                                    Courses, students,
                                    assignments and grading
                                    activity will appear here as
                                    they are added to your
                                    account.
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
                                Open the tools you use most
                                often.
                            </p>

                            <div className="mt-4 grid gap-4 md:grid-cols-2">
                                <QuickActionCard
                                    href="/teacher/reports"
                                    title="Write and review reports"
                                    description="Prepare student reports, save drafts and submit completed reports for review."
                                    icon={FileText}
                                />

                                <QuickActionCard
                                    href="/messages"
                                    title="Open messages"
                                    description="View conversations and communicate securely with colleagues, parents and other authorised users."
                                    icon={MessageSquare}
                                />
                            </div>
                        </section>
                    </>
                ) : null}
            </div>
        </main>
    );
}

function MetricCard({
    label,
    value,
    description,
    icon: Icon,
}: DashboardMetric) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm font-bold text-slate-500">
                        {label}
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
    icon: typeof FileText;
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
            <div className="h-7 w-32 animate-pulse rounded bg-slate-200" />
            <div className="mt-2 h-4 w-64 max-w-full animate-pulse rounded bg-slate-100" />

            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map(
                    (_, index) => (
                        <div
                            key={index}
                            className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                        >
                            <div className="flex items-start justify-between">
                                <div className="h-4 w-24 rounded bg-slate-200" />
                                <div className="h-12 w-12 rounded-2xl bg-slate-100" />
                            </div>

                            <div className="mt-5 h-10 w-20 rounded bg-slate-200" />
                            <div className="mt-5 h-4 w-full rounded bg-slate-100" />
                            <div className="mt-2 h-4 w-4/5 rounded bg-slate-100" />
                        </div>
                    ),
                )}
            </div>
        </section>
    );
}
