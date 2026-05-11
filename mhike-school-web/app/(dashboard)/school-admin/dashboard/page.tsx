"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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

export default function SchoolAdminDashboardPage() {
    const [stats, setStats] = useState<DashboardStats>({
        total_teachers: 0,
        total_students: 0,
        total_courses: 0,
        active_users: 0,
    });

    const [recentUsers, setRecentUsers] = useState<UserItem[]>([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        async function loadDashboard() {
            try {
                setLoading(true);
                setError("");

                const users = await apiGet<UserItem[]>(
                    "/school-admin/users",
                );

                const coursesResponse = await apiGet<{
                    items?: unknown[];
                }>("/courses");

                const teachers = users.filter(
                    (user) => user.role === "teacher",
                );

                const students = users.filter(
                    (user) => user.role === "student",
                );

                const activeUsers = users.length;

                setStats({
                    total_teachers: teachers.length,
                    total_students: students.length,
                    total_courses:
                        coursesResponse.items?.length ?? 0,
                    active_users: activeUsers,
                });

                setRecentUsers(users.slice(0, 5));
            } catch (err) {
                console.error(err);

                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load dashboard.",
                );
            } finally {
                setLoading(false);
            }
        }

        loadDashboard();
    }, []);

    return (
        <div className="p-8 space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold">
                        School Admin Dashboard
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Manage your school users, teachers,
                        students, and courses.
                    </p>
                </div>

                <div className="flex gap-3">
                    <Link
                        href="/school-admin/users/create"
                        className="rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700"
                    >
                        Create User
                    </Link>

                    <Link
                        href="/school-admin/users"
                        className="rounded-xl border px-5 py-3 font-semibold hover:bg-slate-50"
                    >
                        View Users
                    </Link>
                </div>
            </div>

            {error ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                    {error}
                </div>
            ) : null}

            <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
                <DashboardCard
                    title="Total Teachers"
                    value={stats.total_teachers}
                />

                <DashboardCard
                    title="Total Students"
                    value={stats.total_students}
                />

                <DashboardCard
                    title="Total Courses"
                    value={stats.total_courses}
                />

                <DashboardCard
                    title="Active Users"
                    value={stats.active_users}
                />
            </div>

            <div className="rounded-2xl border bg-white p-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold">
                        Recent Users
                    </h2>

                    <Link
                        href="/school-admin/users"
                        className="text-sm font-semibold text-blue-600 hover:text-blue-700"
                    >
                        View all
                    </Link>
                </div>

                {loading ? (
                    <div className="mt-4 text-slate-500">
                        Loading dashboard...
                    </div>
                ) : recentUsers.length === 0 ? (
                    <div className="mt-4 text-slate-500">
                        No users found.
                    </div>
                ) : (
                    <div className="mt-4 space-y-3">
                        {recentUsers.map((user) => (
                            <div
                                key={user.id}
                                className="flex items-center justify-between rounded-xl border p-4"
                            >
                                <div>
                                    <div className="font-semibold">
                                        {user.full_name ||
                                            "Unnamed User"}
                                    </div>

                                    <div className="text-sm text-slate-500">
                                        {user.email}
                                    </div>
                                </div>

                                <div className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium capitalize">
                                    {user.role}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

type DashboardCardProps = {
    title: string;
    value: number;
};

function DashboardCard({
    title,
    value,
}: DashboardCardProps) {
    return (
        <div className="rounded-2xl border bg-white p-6">
            <div className="text-sm text-slate-500">
                {title}
            </div>

            <div className="mt-2 text-3xl font-extrabold">
                {value}
            </div>
        </div>
    );
}