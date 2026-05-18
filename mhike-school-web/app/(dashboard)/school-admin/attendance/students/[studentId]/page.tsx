"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type StudentAttendanceHistoryRecord = {
    record_id: number;
    attendance_session_id: number;
    session_date: string;
    session_type: string;
    class_group_id: number;
    class_name: string | null;
    status:
    | "present"
    | "late"
    | "authorised_absence"
    | "unauthorised_absence";
    notes: string | null;
    marked_by_id: number | null;
    created_at: string;
    updated_at: string;
};

type StudentAttendanceProfile = {
    student_id: number;
    student_name: string | null;
    school_id: number;
    total_records: number;
    present: number;
    late: number;
    authorised_absence: number;
    unauthorised_absence: number;
    attendance_percentage: number;
    history: StudentAttendanceHistoryRecord[];
};

function formatStatus(
    status: StudentAttendanceHistoryRecord["status"],
) {
    return status.replaceAll("_", " ");
}

function getStatusBadge(
    status: StudentAttendanceHistoryRecord["status"],
) {
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

export default function StudentAttendanceProfilePage() {
    const params = useParams<{ studentId: string }>();

    const studentId = params.studentId;

    const [profile, setProfile] =
        useState<StudentAttendanceProfile | null>(null);

    const [loading, setLoading] = useState(true);

    const [error, setError] =
        useState<string | null>(null);

    useEffect(() => {
        async function loadProfile() {
            try {
                setLoading(true);
                setError(null);

                const response = await fetch(
                    `/api/v1/student-attendance/students/${studentId}/profile`,
                    {
                        credentials: "include",
                    },
                );

                if (!response.ok) {
                    throw new Error(
                        "Failed to load student attendance profile.",
                    );
                }

                const data =
                    (await response.json()) as StudentAttendanceProfile;

                setProfile(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load student attendance profile.",
                );
            } finally {
                setLoading(false);
            }
        }

        void loadProfile();
    }, [studentId]);

    const attendanceHealth = useMemo(() => {
        if (!profile) {
            return {
                label: "Unknown",
                className:
                    "bg-slate-100 text-slate-700",
            };
        }

        if (profile.attendance_percentage >= 95) {
            return {
                label: "Excellent",
                className:
                    "bg-green-100 text-green-700",
            };
        }

        if (profile.attendance_percentage >= 90) {
            return {
                label: "Good",
                className:
                    "bg-blue-100 text-blue-700",
            };
        }

        if (profile.attendance_percentage >= 80) {
            return {
                label: "Concern",
                className:
                    "bg-yellow-100 text-yellow-700",
            };
        }

        return {
            label: "Persistent Absence Risk",
            className:
                "bg-red-100 text-red-700",
        };
    }, [profile]);

    return (
        <main className="space-y-6 p-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <Link
                        href="/school-admin/attendance"
                        className="text-sm font-semibold text-blue-600 hover:text-blue-700"
                    >
                        ← Back to attendance overview
                    </Link>

                    <h1 className="mt-3 text-3xl font-extrabold text-slate-950">
                        Student Attendance Profile
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Attendance history, trends,
                        and attendance health overview.
                    </p>
                </div>

                {profile ? (
                    <div
                        className={`rounded-full px-4 py-3 text-sm font-bold ${attendanceHealth.className}`}
                    >
                        {attendanceHealth.label}
                    </div>
                ) : null}
            </div>

            {loading ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Loading student attendance
                    profile...
                </section>
            ) : error ? (
                <section className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-700">
                    {error}
                </section>
            ) : !profile ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Student attendance profile not
                    found.
                </section>
            ) : (
                <>
                    <section className="grid gap-4 md:grid-cols-4">
                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Student ID
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-slate-950">
                                {profile.student_id}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-green-50 p-5">
                            <div className="text-sm font-semibold text-green-700">
                                Attendance %
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-green-900">
                                {
                                    profile.attendance_percentage
                                }
                                %
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-blue-50 p-5">
                            <div className="text-sm font-semibold text-blue-700">
                                Total Records
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-blue-900">
                                {profile.total_records}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-red-50 p-5">
                            <div className="text-sm font-semibold text-red-700">
                                Unauthorised
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-red-900">
                                {
                                    profile.unauthorised_absence
                                }
                            </div>
                        </article>
                    </section>

                    <section className="grid gap-4 md:grid-cols-4">
                        <article className="rounded-2xl border bg-green-50 p-5">
                            <div className="text-sm font-semibold text-green-700">
                                Present
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-green-900">
                                {profile.present}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-yellow-50 p-5">
                            <div className="text-sm font-semibold text-yellow-700">
                                Late
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-yellow-900">
                                {profile.late}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-blue-50 p-5">
                            <div className="text-sm font-semibold text-blue-700">
                                Authorised
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-blue-900">
                                {
                                    profile.authorised_absence
                                }
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-red-50 p-5">
                            <div className="text-sm font-semibold text-red-700">
                                Unauthorised
                            </div>

                            <div className="mt-2 text-3xl font-extrabold text-red-900">
                                {
                                    profile.unauthorised_absence
                                }
                            </div>
                        </article>
                    </section>

                    <section className="rounded-2xl border bg-white p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Attendance History
                                </h2>

                                <p className="mt-1 text-sm text-slate-500">
                                    {
                                        profile.history
                                            .length
                                    }{" "}
                                    attendance records
                                    found.
                                </p>
                            </div>
                        </div>

                        {profile.history.length ===
                            0 ? (
                            <p className="mt-6 text-slate-500">
                                No attendance
                                history found for
                                this student.
                            </p>
                        ) : (
                            <div className="mt-6 overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="border-b text-slate-500">
                                        <tr>
                                            <th className="py-3 pr-4">
                                                Date
                                            </th>

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

                                            <th className="py-3 pr-4">
                                                Register
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {profile.history.map(
                                            (
                                                record,
                                            ) => (
                                                <tr
                                                    key={
                                                        record.record_id
                                                    }
                                                    className="border-b last:border-0"
                                                >
                                                    <td className="py-4 pr-4 font-semibold">
                                                        {
                                                            record.session_date
                                                        }
                                                    </td>

                                                    <td className="py-4 pr-4 uppercase">
                                                        {
                                                            record.session_type
                                                        }
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
                                                        {record.notes ??
                                                            "—"}
                                                    </td>

                                                    <td className="py-4 pr-4">
                                                        <Link
                                                            href={`/school-admin/attendance/registers/${record.attendance_session_id}`}
                                                            className="font-semibold text-blue-600 hover:text-blue-700"
                                                        >
                                                            View
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ),
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>
                </>
            )}
        </main>
    );
}