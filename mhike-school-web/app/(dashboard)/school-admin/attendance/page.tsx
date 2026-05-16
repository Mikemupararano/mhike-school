"use client";

import { useEffect, useState } from "react";

type RegisterSummary = {
    session_id: number;
    class_group_id: number;
    class_name: string | null;
    session_date: string;
    session_type: string;
    is_submitted: boolean;
    total_records: number;
};

type ClassSummary = {
    class_group_id: number;
    class_name: string | null;
    total_records: number;
    present: number;
    late: number;
    authorised_absence: number;
    unauthorised_absence: number;
};

type AttendanceDashboardSummary = {
    school_id: number;
    summary_date: string;
    total_records: number;
    submitted_registers: number;
    unsubmitted_registers: number;
    present: number;
    late: number;
    authorised_absence: number;
    unauthorised_absence: number;
    registers: RegisterSummary[];
    classes: ClassSummary[];
};

function getTodayIsoDate() {
    return new Date().toISOString().slice(0, 10);
}

export default function SchoolAdminAttendanceDashboardPage() {
    const [summaryDate, setSummaryDate] = useState(getTodayIsoDate());
    const [summary, setSummary] =
        useState<AttendanceDashboardSummary | null>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadSummary() {
            try {
                setLoading(true);
                setError(null);

                const response = await fetch(
                    `/api/v1/attendance-dashboard/summary?summary_date=${summaryDate}`,
                    {
                        credentials: "include",
                    },
                );

                if (!response.ok) {
                    throw new Error("Failed to load attendance dashboard.");
                }

                const data =
                    (await response.json()) as AttendanceDashboardSummary;

                setSummary(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load attendance dashboard.",
                );
            } finally {
                setLoading(false);
            }
        }

        void loadSummary();
    }, [summaryDate]);

    return (
        <main className="space-y-6 p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Attendance Overview
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Monitor today&apos;s registers, absences, and class
                        attendance patterns.
                    </p>
                </div>

                <label className="space-y-2">
                    <span className="block text-sm font-semibold text-slate-700">
                        Summary date
                    </span>

                    <input
                        type="date"
                        value={summaryDate}
                        onChange={(event) =>
                            setSummaryDate(event.target.value)
                        }
                        className="rounded-xl border px-4 py-3"
                    />
                </label>
            </div>

            {loading ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Loading attendance summary...
                </section>
            ) : error ? (
                <section className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-700">
                    {error}
                </section>
            ) : !summary ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    No attendance summary found.
                </section>
            ) : (
                <>
                    <section className="grid gap-4 md:grid-cols-4">
                        <article className="rounded-2xl border bg-green-50 p-5">
                            <div className="text-sm font-semibold text-green-700">
                                Present
                            </div>
                            <div className="mt-2 text-3xl font-extrabold text-green-900">
                                {summary.present}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-yellow-50 p-5">
                            <div className="text-sm font-semibold text-yellow-700">
                                Late
                            </div>
                            <div className="mt-2 text-3xl font-extrabold text-yellow-900">
                                {summary.late}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-blue-50 p-5">
                            <div className="text-sm font-semibold text-blue-700">
                                Authorised Absence
                            </div>
                            <div className="mt-2 text-3xl font-extrabold text-blue-900">
                                {summary.authorised_absence}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-red-50 p-5">
                            <div className="text-sm font-semibold text-red-700">
                                Unauthorised Absence
                            </div>
                            <div className="mt-2 text-3xl font-extrabold text-red-900">
                                {summary.unauthorised_absence}
                            </div>
                        </article>
                    </section>

                    <section className="grid gap-4 md:grid-cols-3">
                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Total Records
                            </div>
                            <div className="mt-2 text-3xl font-extrabold text-slate-950">
                                {summary.total_records}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Submitted Registers
                            </div>
                            <div className="mt-2 text-3xl font-extrabold text-slate-950">
                                {summary.submitted_registers}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-5">
                            <div className="text-sm font-semibold text-slate-500">
                                Unsubmitted Registers
                            </div>
                            <div className="mt-2 text-3xl font-extrabold text-slate-950">
                                {summary.unsubmitted_registers}
                            </div>
                        </article>
                    </section>

                    <section className="rounded-2xl border bg-white p-6">
                        <h2 className="text-xl font-bold text-slate-950">
                            Registers
                        </h2>

                        {summary.registers.length === 0 ? (
                            <p className="mt-4 text-slate-500">
                                No registers found for this date.
                            </p>
                        ) : (
                            <div className="mt-4 overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="border-b text-slate-500">
                                        <tr>
                                            <th className="py-3 pr-4">
                                                Class
                                            </th>
                                            <th className="py-3 pr-4">
                                                Session
                                            </th>
                                            <th className="py-3 pr-4">
                                                Records
                                            </th>
                                            <th className="py-3 pr-4">
                                                Status
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {summary.registers.map((register) => (
                                            <tr
                                                key={register.session_id}
                                                className="border-b last:border-0"
                                            >
                                                <td className="py-3 pr-4 font-semibold">
                                                    {register.class_name ??
                                                        `Class ${register.class_group_id}`}
                                                </td>

                                                <td className="py-3 pr-4 uppercase">
                                                    {register.session_type}
                                                </td>

                                                <td className="py-3 pr-4">
                                                    {register.total_records}
                                                </td>

                                                <td className="py-3 pr-4">
                                                    <span
                                                        className={`rounded-full px-3 py-1 text-xs font-bold ${register.is_submitted
                                                            ? "bg-green-100 text-green-700"
                                                            : "bg-orange-100 text-orange-700"
                                                            }`}
                                                    >
                                                        {register.is_submitted
                                                            ? "Submitted"
                                                            : "Not submitted"}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>

                    <section className="rounded-2xl border bg-white p-6">
                        <h2 className="text-xl font-bold text-slate-950">
                            Attendance by Class
                        </h2>

                        {summary.classes.length === 0 ? (
                            <p className="mt-4 text-slate-500">
                                No class attendance data found for this date.
                            </p>
                        ) : (
                            <div className="mt-4 overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead className="border-b text-slate-500">
                                        <tr>
                                            <th className="py-3 pr-4">
                                                Class
                                            </th>
                                            <th className="py-3 pr-4">
                                                Present
                                            </th>
                                            <th className="py-3 pr-4">Late</th>
                                            <th className="py-3 pr-4">
                                                Authorised
                                            </th>
                                            <th className="py-3 pr-4">
                                                Unauthorised
                                            </th>
                                            <th className="py-3 pr-4">
                                                Total
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {summary.classes.map((classSummary) => (
                                            <tr
                                                key={
                                                    classSummary.class_group_id
                                                }
                                                className="border-b last:border-0"
                                            >
                                                <td className="py-3 pr-4 font-semibold">
                                                    {classSummary.class_name ??
                                                        `Class ${classSummary.class_group_id}`}
                                                </td>
                                                <td className="py-3 pr-4">
                                                    {classSummary.present}
                                                </td>
                                                <td className="py-3 pr-4">
                                                    {classSummary.late}
                                                </td>
                                                <td className="py-3 pr-4">
                                                    {
                                                        classSummary.authorised_absence
                                                    }
                                                </td>
                                                <td className="py-3 pr-4">
                                                    {
                                                        classSummary.unauthorised_absence
                                                    }
                                                </td>
                                                <td className="py-3 pr-4 font-bold">
                                                    {
                                                        classSummary.total_records
                                                    }
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