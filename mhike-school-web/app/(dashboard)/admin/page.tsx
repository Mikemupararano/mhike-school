"use client";

import { useEffect, useMemo, useState } from "react";

import { apiGet } from "@/lib/api";

type RecentSchool = {
    id: number;
    name: string;
    admin_name: string;
    users: number;
    status: string;
};

type PlatformDashboard = {
    total_schools: number;
    total_users: number;
    active_users: number;
    total_courses: number;
    published_content: number;
    total_enrollments: number;
    recent_schools: RecentSchool[];
};

const fallbackChartData = [42, 64, 78, 56, 48, 70, 92];

export default function AdminPage() {
    const [dashboard, setDashboard] = useState<PlatformDashboard | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    async function loadDashboard() {
        try {
            setError(null);
            setIsLoading(true);

            const data = await apiGet<PlatformDashboard>("/admin/dashboard");
            setDashboard(data);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load platform dashboard",
            );
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadDashboard();
    }, []);

    const metricCards = useMemo(
        () => [
            {
                label: "Total Schools",
                value: dashboard?.total_schools ?? 0,
                change: "Live platform count",
            },
            {
                label: "Total Users",
                value: dashboard?.total_users ?? 0,
                change: `${dashboard?.active_users ?? 0} active users`,
            },
            {
                label: "Total Courses",
                value: dashboard?.total_courses ?? 0,
                change: `${dashboard?.total_enrollments ?? 0} enrollments`,
            },
            {
                label: "Published Content",
                value: dashboard?.published_content ?? 0,
                change: "Published courses",
            },
        ],
        [dashboard],
    );

    const activity = useMemo(() => {
        if (!dashboard) return [];

        return [
            `${dashboard.total_schools} school${dashboard.total_schools === 1 ? "" : "s"} on the platform`,
            `${dashboard.total_users} registered user${dashboard.total_users === 1 ? "" : "s"}`,
            `${dashboard.active_users} active user${dashboard.active_users === 1 ? "" : "s"}`,
            `${dashboard.published_content} published course${dashboard.published_content === 1 ? "" : "s"}`,
        ];
    }, [dashboard]);

    return (
        <div className="min-h-screen bg-slate-50 p-10">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-5xl font-black tracking-tight text-slate-950">
                        Platform Admin Dashboard
                    </h1>
                    <p className="mt-3 text-lg font-medium text-slate-600">
                        Overview of platform activity, schools, users, and content.
                    </p>
                </div>

                <button
                    onClick={() => void loadDashboard()}
                    className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-base font-bold text-slate-900 shadow-sm hover:bg-slate-50"
                >
                    Refresh
                </button>
            </div>

            {isLoading && (
                <div className="mt-10 rounded-3xl border border-slate-200 bg-white p-7 text-base font-bold text-slate-700 shadow-sm">
                    Loading dashboard...
                </div>
            )}

            {error && (
                <div className="mt-10 rounded-3xl border border-red-200 bg-red-50 p-7 text-base font-bold text-red-700">
                    {error}
                </div>
            )}

            {!isLoading && !error && dashboard && (
                <>
                    <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
                        {metricCards.map((card) => (
                            <div
                                key={card.label}
                                className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm"
                            >
                                <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                    {card.label}
                                </p>
                                <p className="mt-3 text-4xl font-black tracking-tight text-slate-950">
                                    {card.value.toLocaleString()}
                                </p>
                                <p className="mt-3 text-sm font-bold text-blue-600">
                                    {card.change}
                                </p>
                            </div>
                        ))}
                    </div>

                    <div className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_1fr]">
                        <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                            <div className="flex items-center justify-between">
                                <h2 className="text-2xl font-black text-slate-950">
                                    User Registrations
                                </h2>
                                <span className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-bold text-slate-700">
                                    Last 7 days
                                </span>
                            </div>

                            <div className="mt-8 flex h-72 items-end gap-4 border-b border-slate-200">
                                {fallbackChartData.map((height, index) => (
                                    <div
                                        key={index}
                                        className="flex flex-1 flex-col items-center gap-3"
                                    >
                                        <div
                                            className="w-full rounded-t-2xl bg-blue-600"
                                            style={{ height: `${height}%` }}
                                        />
                                        <span className="text-xs font-bold text-slate-500">
                                            D{index + 1}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                            <div className="flex items-center justify-between">
                                <h2 className="text-2xl font-black text-slate-950">
                                    Recent Schools
                                </h2>
                                <span className="text-sm font-bold text-blue-600">
                                    Live data
                                </span>
                            </div>

                            <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-slate-50 text-slate-500">
                                        <tr>
                                            <th className="px-4 py-3 font-black">
                                                School
                                            </th>
                                            <th className="px-4 py-3 font-black">
                                                Admin
                                            </th>
                                            <th className="px-4 py-3 font-black">
                                                Users
                                            </th>
                                            <th className="px-4 py-3 font-black">
                                                Status
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {dashboard.recent_schools.length === 0 ? (
                                            <tr>
                                                <td
                                                    colSpan={4}
                                                    className="px-4 py-6 text-center font-bold text-slate-500"
                                                >
                                                    No schools found.
                                                </td>
                                            </tr>
                                        ) : (
                                            dashboard.recent_schools.map((school) => (
                                                <tr
                                                    key={school.id}
                                                    className="border-t border-slate-200"
                                                >
                                                    <td className="px-4 py-4 font-bold text-slate-950">
                                                        {school.name}
                                                    </td>
                                                    <td className="px-4 py-4 font-semibold text-slate-700">
                                                        {school.admin_name}
                                                    </td>
                                                    <td className="px-4 py-4 font-bold text-slate-900">
                                                        {school.users}
                                                    </td>
                                                    <td className="px-4 py-4">
                                                        <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-black text-green-800">
                                                            {school.status}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    </div>

                    <div className="mt-8 grid gap-6 xl:grid-cols-[1fr_1fr]">
                        <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                            <h2 className="text-2xl font-black text-slate-950">
                                Platform Health
                            </h2>

                            <div className="mt-6 space-y-5">
                                {[
                                    ["Active users", dashboard.active_users.toLocaleString()],
                                    ["Total enrollments", dashboard.total_enrollments.toLocaleString()],
                                    ["Published content", dashboard.published_content.toLocaleString()],
                                ].map(([label, value]) => (
                                    <div
                                        key={label}
                                        className="flex items-center justify-between rounded-2xl bg-slate-50 p-5"
                                    >
                                        <span className="text-base font-bold text-slate-700">
                                            {label}
                                        </span>
                                        <span className="text-xl font-black text-slate-950">
                                            {value}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                            <div className="flex items-center justify-between">
                                <h2 className="text-2xl font-black text-slate-950">
                                    Recent Activity
                                </h2>
                                <span className="text-sm font-bold text-blue-600">
                                    Snapshot
                                </span>
                            </div>

                            <div className="mt-6 space-y-4">
                                {activity.map((item, index) => (
                                    <div key={item} className="flex items-start gap-4">
                                        <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-full bg-blue-50 text-sm font-black text-blue-700">
                                            {index + 1}
                                        </div>
                                        <div>
                                            <p className="text-base font-bold text-slate-900">
                                                {item}
                                            </p>
                                            <p className="mt-1 text-sm font-medium text-slate-500">
                                                Updated from backend
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>
                </>
            )}
        </div>
    );
}