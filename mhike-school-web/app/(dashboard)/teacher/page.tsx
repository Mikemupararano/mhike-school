"use client";

import { useEffect, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import { getTeacherDashboard, type TeacherDashboard } from "@/lib/services/teacher";
import { UserRole } from "@/types/user";

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
    const [data, setData] = useState<TeacherDashboard | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadDashboard() {
            try {
                setError(null);
                const dashboard = await getTeacherDashboard();
                setData(dashboard);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load teacher dashboard.",
                );
            } finally {
                setIsLoading(false);
            }
        }

        void loadDashboard();
    }, []);

    return (
        <div className="p-6">
            <h1 className="text-3xl font-extrabold">Teacher Dashboard</h1>
            <p className="mt-2 text-slate-500">
                Overview of your courses, students, assignments, and grading queue.
            </p>

            {isLoading && <p className="mt-6">Loading dashboard...</p>}

            {error && (
                <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                    {error}
                </div>
            )}

            {data && !isLoading && !error && (
                <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <MetricCard label="Courses" value={data.total_courses} />
                    <MetricCard label="Students" value={data.total_students} />
                    <MetricCard label="Assignments" value={data.total_assignments} />
                    <MetricCard
                        label="Pending grading"
                        value={data.pending_submissions}
                    />
                </div>
            )}
        </div>
    );
}

function MetricCard({ label, value }: { label: string; value: number }) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">{label}</p>
            <p className="mt-3 text-3xl font-extrabold text-slate-900">{value}</p>
        </div>
    );
}