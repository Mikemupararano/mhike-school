"use client";

import Link from "next/link";
import { useMemo } from "react";

import ChildSelector from "@/components/parent/ChildSelector";

import { useParentChildren } from "@/hooks/useParentChildren";

import {
    type StudentAttendanceHistoryRecord,
    type StudentAttendanceProfile,
} from "@/lib/parent";

function formatStatus(status: StudentAttendanceHistoryRecord["status"]) {
    return status.replaceAll("_", " ");
}

function getStatusBadge(status: StudentAttendanceHistoryRecord["status"]) {
    switch (status) {
        case "present":
            return "bg-green-100 text-green-700";
        case "late":
            return "bg-yellow-100 text-yellow-700";
        case "authorised_absence":
            return "bg-blue-100 text-blue-700";
        case "unauthorised_absence":
            return "bg-red-100 text-red-700";
        default:
            return "bg-slate-100 text-slate-700";
    }
}

function getAttendanceHealth(profile: StudentAttendanceProfile) {
    if (profile.attendance_percentage >= 95) {
        return {
            label: "Excellent",
            className: "bg-green-100 text-green-700",
        };
    }

    if (profile.attendance_percentage >= 90) {
        return {
            label: "Good",
            className: "bg-blue-100 text-blue-700",
        };
    }

    if (profile.attendance_percentage >= 80) {
        return {
            label: "Concern",
            className: "bg-yellow-100 text-yellow-700",
        };
    }

    return {
        label: "Persistent absence risk",
        className: "bg-red-100 text-red-700",
    };
}

export default function ParentDashboardPage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading,
        error,
    } = useParentChildren();

    const recentHistory = useMemo(() => {
        return selectedProfile?.history.slice(0, 10) ?? [];
    }, [selectedProfile]);

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Parent Dashboard
                </h1>

                <p className="mt-2 text-slate-500">
                    View your child&apos;s attendance summary, recent records,
                    and attendance health.
                </p>
            </div>

            {loading ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Loading parent dashboard...
                </section>
            ) : error ? (
                <section className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-700">
                    {error}
                </section>
            ) : profiles.length === 0 ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    No linked students found for this parent account.
                </section>
            ) : selectedProfile ? (
                <>
                    <ChildSelector
                        profiles={profiles}
                        selectedStudentId={selectedStudentId}
                        onSelectStudent={setSelectedStudentId}
                        title="Linked Students"
                        description="Select a child to view their attendance profile."
                    />

                    <section className="grid gap-4 md:grid-cols-4">
                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Student
                            </div>

                            <div className="mt-2 text-2xl font-extrabold text-slate-950">
                                {selectedProfile.student_name ??
                                    `Student ${selectedProfile.student_id}`}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-green-50 p-5">
                            <div className="text-sm font-semibold text-green-700">
                                Attendance
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-green-900">
                                {selectedProfile.attendance_percentage}%
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-blue-50 p-5">
                            <div className="text-sm font-semibold text-blue-700">
                                Total Records
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-blue-900">
                                {selectedProfile.total_records}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Attendance Health
                            </div>

                            <div className="mt-4">
                                <span
                                    className={`rounded-full px-3 py-2 text-sm font-bold ${getAttendanceHealth(selectedProfile)
                                        .className
                                        }`}
                                >
                                    {getAttendanceHealth(selectedProfile).label}
                                </span>
                            </div>
                        </article>
                    </section>

                    <section className="grid gap-4 md:grid-cols-4">
                        <article className="rounded-2xl border bg-green-50 p-5">
                            <div className="text-sm font-semibold text-green-700">
                                Present
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-green-900">
                                {selectedProfile.present}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-yellow-50 p-5">
                            <div className="text-sm font-semibold text-yellow-700">
                                Late
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-yellow-900">
                                {selectedProfile.late}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-blue-50 p-5">
                            <div className="text-sm font-semibold text-blue-700">
                                Authorised
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-blue-900">
                                {selectedProfile.authorised_absence}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-red-50 p-5">
                            <div className="text-sm font-semibold text-red-700">
                                Unauthorised
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-red-900">
                                {selectedProfile.unauthorised_absence}
                            </div>
                        </article>
                    </section>

                    <section className="rounded-2xl border bg-white p-6">
                        <div className="flex items-center justify-between gap-4">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Recent Attendance
                                </h2>

                                <p className="mt-1 text-sm text-slate-500">
                                    Latest attendance records for the selected
                                    student.
                                </p>
                            </div>

                            <Link
                                href={`/parent/attendance/students/${selectedProfile.student_id}`}
                                className="shrink-0 font-semibold text-blue-600 hover:text-blue-700"
                            >
                                View full history
                            </Link>
                        </div>

                        {recentHistory.length === 0 ? (
                            <p className="mt-6 text-slate-500">
                                No attendance history found.
                            </p>
                        ) : (
                            <div className="mt-6 overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="border-b text-slate-500">
                                        <tr>
                                            <th className="py-3 pr-4">Date</th>
                                            <th className="py-3 pr-4">
                                                Session
                                            </th>
                                            <th className="py-3 pr-4">
                                                Class
                                            </th>
                                            <th className="py-3 pr-4">
                                                Status
                                            </th>
                                            <th className="py-3 pr-4">
                                                Notes
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {recentHistory.map((record) => (
                                            <tr
                                                key={record.record_id}
                                                className="border-b last:border-0"
                                            >
                                                <td className="py-4 pr-4 font-semibold">
                                                    {record.session_date}
                                                </td>

                                                <td className="py-4 pr-4 uppercase">
                                                    {record.session_type}
                                                </td>

                                                <td className="py-4 pr-4">
                                                    {record.class_name ??
                                                        `Class ${record.class_group_id}`}
                                                </td>

                                                <td className="py-4 pr-4">
                                                    <span
                                                        className={`rounded-full px-3 py-1 text-xs font-bold capitalize ${getStatusBadge(
                                                            record.status,
                                                        )}`}
                                                    >
                                                        {formatStatus(
                                                            record.status,
                                                        )}
                                                    </span>
                                                </td>

                                                <td className="py-4 pr-4">
                                                    {record.notes ?? "—"}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>
                </>
            ) : null}
        </main>
    );
}