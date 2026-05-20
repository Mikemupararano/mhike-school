"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type ParentStudentLink = {
    id: number;
    parent_id: number;
    student_id: number;
};

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
    const [links, setLinks] = useState<ParentStudentLink[]>([]);
    const [profiles, setProfiles] = useState<StudentAttendanceProfile[]>([]);
    const [selectedStudentId, setSelectedStudentId] = useState<number | null>(
        null,
    );

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadParentDashboard() {
            try {
                setLoading(true);
                setError(null);

                const linksResponse = await fetch(
                    "/api/v1/parent-students/me/children",
                    {
                        credentials: "include",
                    },
                );

                if (!linksResponse.ok) {
                    throw new Error("Failed to load linked children.");
                }

                const linkData =
                    (await linksResponse.json()) as ParentStudentLink[];

                setLinks(linkData);

                const loadedProfiles = await Promise.all(
                    linkData.map(async (link) => {
                        const response = await fetch(
                            `/api/v1/parent-attendance/students/${link.student_id}/profile`,
                            {
                                credentials: "include",
                            },
                        );

                        if (!response.ok) {
                            throw new Error(
                                "Failed to load child attendance profile.",
                            );
                        }

                        return (await response.json()) as StudentAttendanceProfile;
                    }),
                );

                setProfiles(loadedProfiles);

                if (loadedProfiles.length > 0) {
                    setSelectedStudentId(loadedProfiles[0].student_id);
                }
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load parent dashboard.",
                );
            } finally {
                setLoading(false);
            }
        }

        void loadParentDashboard();
    }, []);

    const selectedProfile = useMemo(() => {
        return (
            profiles.find(
                (profile) => profile.student_id === selectedStudentId,
            ) ?? null
        );
    }, [profiles, selectedStudentId]);

    const recentHistory = useMemo(() => {
        if (!selectedProfile) {
            return [];
        }

        return selectedProfile.history.slice(0, 10);
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
                    <section className="rounded-2xl border bg-white p-6">
                        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Linked Students
                                </h2>

                                <p className="mt-1 text-sm text-slate-500">
                                    Select a child to view their attendance
                                    profile.
                                </p>
                            </div>

                            <select
                                value={selectedProfile.student_id}
                                onChange={(event) =>
                                    setSelectedStudentId(
                                        Number(event.target.value),
                                    )
                                }
                                className="rounded-xl border px-4 py-3"
                            >
                                {profiles.map((profile) => (
                                    <option
                                        key={profile.student_id}
                                        value={profile.student_id}
                                    >
                                        {profile.student_name ??
                                            `Student ${profile.student_id}`}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </section>

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
                        <div className="flex items-center justify-between">
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
                                className="font-semibold text-blue-600 hover:text-blue-700"
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