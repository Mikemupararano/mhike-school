"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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

function PercentageBar({
    value,
    total,
    colorClass,
}: {
    value: number;
    total: number;
    colorClass: string;
}) {
    const percentage = total > 0 ? Math.round((value / total) * 100) : 0;

    return (
        <div>
            <div className="mb-1 flex justify-between text-xs font-semibold text-slate-600">
                <span>{value}</span>
                <span>{percentage}%</span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-slate-200">
                <div
                    className={`h-full rounded-full ${colorClass}`}
                    style={{
                        width: `${percentage}%`,
                    }}
                />
            </div>
        </div>
    );
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

    const attendanceBreakdown = useMemo(() => {
        if (!summary) {
            return [];
        }

        return [
            {
                label: "Present",
                value: summary.present,
                color: "bg-green-500",
            },
            {
                label: "Late",
                value: summary.late,
                color: "bg-yellow-500",
            },
            {
                label: "Authorised",
                value: summary.authorised_absence,
                color: "bg-blue-500",
            },
            {
                label: "Unauthorised",
                value: summary.unauthorised_absence,
                color: "bg-red-500",
            },
        ];
    }, [summary]);

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

                    <section className="grid gap-4 lg:grid-cols-3">
                        <article className="rounded-2xl border bg-white p-6">
                            <h2 className="text-lg font-bold text-slate-950">
                                Attendance Breakdown
                            </h2>

                            <div className="mt-6 space-y-4">
                                {attendanceBreakdown.map((item) => (
                                    <div key={item.label}>
                                        <div className="mb-2 flex justify-between text-sm font-semibold">
                                            <span>{item.label}</span>
                                            <span>{item.value}</span>
                                        </div>

                                        <PercentageBar
                                            value={item.value}
                                            total={summary.total_records}
                                            colorClass={item.color}
                                        />
                                    </div>
                                ))}
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-6">
                            <h2 className="text-lg font-bold text-slate-950">
                                Register Completion
                            </h2>

                            <div className="mt-6 space-y-6">
                                <div>
                                    <div className="mb-2 flex justify-between text-sm font-semibold">
                                        <span>Submitted</span>
                                        <span>
                                            {summary.submitted_registers}
                                        </span>
                                    </div>

                                    <PercentageBar
                                        value={summary.submitted_registers}
                                        total={
                                            summary.submitted_registers +
                                            summary.unsubmitted_registers
                                        }
                                        colorClass="bg-green-500"
                                    />
                                </div>

                                <div>
                                    <div className="mb-2 flex justify-between text-sm font-semibold">
                                        <span>Unsubmitted</span>
                                        <span>
                                            {summary.unsubmitted_registers}
                                        </span>
                                    </div>

                                    <PercentageBar
                                        value={summary.unsubmitted_registers}
                                        total={
                                            summary.submitted_registers +
                                            summary.unsubmitted_registers
                                        }
                                        colorClass="bg-orange-500"
                                    />
                                </div>
                            </div>
                        </article>

                        <article className="rounded-2xl border bg-white p-6">
                            <h2 className="text-lg font-bold text-slate-950">
                                Overall Totals
                            </h2>

                            <div className="mt-6 space-y-5">
                                <div>
                                    <div className="text-sm font-semibold text-slate-500">
                                        Total Records
                                    </div>

                                    <div className="mt-1 text-3xl font-extrabold text-slate-950">
                                        {summary.total_records}
                                    </div>
                                </div>

                                <div>
                                    <div className="text-sm font-semibold text-slate-500">
                                        Classes
                                    </div>

                                    <div className="mt-1 text-3xl font-extrabold text-slate-950">
                                        {summary.classes.length}
                                    </div>
                                </div>

                                <div>
                                    <div className="text-sm font-semibold text-slate-500">
                                        Registers
                                    </div>

                                    <div className="mt-1 text-3xl font-extrabold text-slate-950">
                                        {summary.registers.length}
                                    </div>
                                </div>
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
                                            <th className="py-3 pr-4">
                                                Actions
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

                                                <td className="py-3 pr-4">
                                                    <Link
                                                        href={`/school-admin/attendance/registers/${register.session_id}`}
                                                        className="font-semibold text-blue-600 hover:text-blue-700"
                                                    >
                                                        View
                                                    </Link>
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
                            <div className="mt-6 space-y-6">
                                {summary.classes.map((classSummary) => (
                                    <div
                                        key={classSummary.class_group_id}
                                        className="rounded-2xl border border-slate-200 p-5"
                                    >
                                        <div className="mb-4 flex items-center justify-between">
                                            <h3 className="text-lg font-bold text-slate-950">
                                                {classSummary.class_name ??
                                                    `Class ${classSummary.class_group_id}`}
                                            </h3>

                                            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-700">
                                                {classSummary.total_records}{" "}
                                                records
                                            </span>
                                        </div>

                                        <div className="grid gap-4 md:grid-cols-2">
                                            <div>
                                                <div className="mb-2 text-sm font-semibold text-slate-700">
                                                    Present
                                                </div>

                                                <PercentageBar
                                                    value={
                                                        classSummary.present
                                                    }
                                                    total={
                                                        classSummary.total_records
                                                    }
                                                    colorClass="bg-green-500"
                                                />
                                            </div>

                                            <div>
                                                <div className="mb-2 text-sm font-semibold text-slate-700">
                                                    Late
                                                </div>

                                                <PercentageBar
                                                    value={classSummary.late}
                                                    total={
                                                        classSummary.total_records
                                                    }
                                                    colorClass="bg-yellow-500"
                                                />
                                            </div>

                                            <div>
                                                <div className="mb-2 text-sm font-semibold text-slate-700">
                                                    Authorised
                                                </div>

                                                <PercentageBar
                                                    value={
                                                        classSummary.authorised_absence
                                                    }
                                                    total={
                                                        classSummary.total_records
                                                    }
                                                    colorClass="bg-blue-500"
                                                />
                                            </div>

                                            <div>
                                                <div className="mb-2 text-sm font-semibold text-slate-700">
                                                    Unauthorised
                                                </div>

                                                <PercentageBar
                                                    value={
                                                        classSummary.unauthorised_absence
                                                    }
                                                    total={
                                                        classSummary.total_records
                                                    }
                                                    colorClass="bg-red-500"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </>
            )}
        </main>
    );
}