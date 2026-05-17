"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

type AttendanceSession = {
    id: number;
    school_id: number;
    class_group_id: number;
    session_date: string;
    session_type: string;
    timetable_entry_id: number | null;
    timetable_period_id: number | null;
    is_submitted: boolean;
    submitted_at: string | null;
    submitted_by_id: number | null;
};

type AttendanceRecord = {
    id: number;
    attendance_session_id: number;
    student_id: number;
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

function formatStatus(status: AttendanceRecord["status"]) {
    return status.replaceAll("_", " ");
}

export default function AttendanceRegisterDrillDownPage() {
    const params = useParams<{ sessionId: string }>();
    const sessionId = params.sessionId;

    const [session, setSession] = useState<AttendanceSession | null>(null);
    const [records, setRecords] = useState<AttendanceRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [reopening, setReopening] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        async function loadRegister() {
            try {
                setLoading(true);
                setError(null);

                const [sessionResponse, recordsResponse] = await Promise.all([
                    fetch(`/api/v1/attendance-registers/${sessionId}`, {
                        credentials: "include",
                    }),
                    fetch(`/api/v1/attendance-registers/${sessionId}/records`, {
                        credentials: "include",
                    }),
                ]);

                if (!sessionResponse.ok) {
                    throw new Error("Failed to load attendance register.");
                }

                if (!recordsResponse.ok) {
                    throw new Error("Failed to load attendance records.");
                }

                const sessionData =
                    (await sessionResponse.json()) as AttendanceSession;

                const recordData =
                    (await recordsResponse.json()) as AttendanceRecord[];

                setSession(sessionData);
                setRecords(recordData);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load attendance register.",
                );
            } finally {
                setLoading(false);
            }
        }

        void loadRegister();
    }, [sessionId]);

    async function reopenRegister() {
        try {
            setReopening(true);
            setError(null);
            setMessage(null);

            const response = await fetch(
                `/api/v1/attendance-registers/${sessionId}/reopen`,
                {
                    method: "PATCH",
                    credentials: "include",
                },
            );

            if (!response.ok) {
                throw new Error("Failed to reopen attendance register.");
            }

            const data = (await response.json()) as AttendanceSession;

            setSession(data);
            setMessage("Attendance register reopened successfully.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to reopen attendance register.",
            );
        } finally {
            setReopening(false);
        }
    }

    return (
        <main className="space-y-6 p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <Link
                        href="/school-admin/attendance"
                        className="text-sm font-semibold text-blue-600 hover:text-blue-700"
                    >
                        ← Back to attendance overview
                    </Link>

                    <h1 className="mt-3 text-3xl font-extrabold text-slate-950">
                        Attendance Register
                    </h1>

                    <p className="mt-2 text-slate-500">
                        View register details, attendance records, and export
                        files.
                    </p>
                </div>

                {session ? (
                    <div className="flex flex-wrap gap-2">
                        <a
                            href={`/api/v1/attendance-exports/registers/export/${session.id}`}
                            className="rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white hover:bg-slate-800"
                        >
                            Export CSV
                        </a>

                        <a
                            href={`/api/v1/attendance-pdf-exports/registers/export/${session.id}/pdf`}
                            className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white hover:bg-blue-700"
                        >
                            Export PDF
                        </a>

                        {session.is_submitted ? (
                            <button
                                type="button"
                                disabled={reopening}
                                onClick={reopenRegister}
                                className="rounded-xl bg-orange-600 px-4 py-3 text-sm font-bold text-white hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                {reopening ? "Reopening..." : "Reopen"}
                            </button>
                        ) : null}
                    </div>
                ) : null}
            </div>

            {message ? (
                <section className="rounded-2xl border border-green-200 bg-green-50 p-4 font-semibold text-green-700">
                    {message}
                </section>
            ) : null}

            {error ? (
                <section className="rounded-2xl border border-red-200 bg-red-50 p-4 font-semibold text-red-700">
                    {error}
                </section>
            ) : null}

            {loading ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Loading register...
                </section>
            ) : !session ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Register not found.
                </section>
            ) : (
                <>
                    <section className="grid gap-4 md:grid-cols-4">
                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Session ID
                            </div>
                            <div className="mt-2 text-2xl font-extrabold text-slate-950">
                                {session.id}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Date
                            </div>
                            <div className="mt-2 text-2xl font-extrabold text-slate-950">
                                {session.session_date}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Session
                            </div>
                            <div className="mt-2 text-2xl font-extrabold uppercase text-slate-950">
                                {session.session_type}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Status
                            </div>
                            <div className="mt-2">
                                <span
                                    className={`rounded-full px-3 py-1 text-sm font-bold ${session.is_submitted
                                        ? "bg-green-100 text-green-700"
                                        : "bg-orange-100 text-orange-700"
                                        }`}
                                >
                                    {session.is_submitted
                                        ? "Submitted"
                                        : "Open"}
                                </span>
                            </div>
                        </article>
                    </section>

                    <section className="rounded-2xl border bg-white p-6">
                        <h2 className="text-xl font-bold text-slate-950">
                            Attendance Records
                        </h2>

                        {records.length === 0 ? (
                            <p className="mt-4 text-slate-500">
                                No attendance records found for this register.
                            </p>
                        ) : (
                            <div className="mt-4 overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="border-b text-slate-500">
                                        <tr>
                                            <th className="py-3 pr-4">
                                                Record ID
                                            </th>
                                            <th className="py-3 pr-4">
                                                Student ID
                                            </th>
                                            <th className="py-3 pr-4">
                                                Status
                                            </th>
                                            <th className="py-3 pr-4">
                                                Notes
                                            </th>
                                            <th className="py-3 pr-4">
                                                Marked By
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {records.map((record) => (
                                            <tr
                                                key={record.id}
                                                className="border-b last:border-0"
                                            >
                                                <td className="py-3 pr-4 font-semibold">
                                                    {record.id}
                                                </td>
                                                <td className="py-3 pr-4">
                                                    {record.student_id}
                                                </td>
                                                <td className="py-3 pr-4 capitalize">
                                                    {formatStatus(
                                                        record.status,
                                                    )}
                                                </td>
                                                <td className="py-3 pr-4">
                                                    {record.notes ?? "—"}
                                                </td>
                                                <td className="py-3 pr-4">
                                                    {record.marked_by_id ??
                                                        "—"}
                                                </td>
                                            </tr>
                                        ))}
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