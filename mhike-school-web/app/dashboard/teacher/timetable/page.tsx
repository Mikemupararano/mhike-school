"use client";

import { useEffect, useMemo, useState } from "react";

import {
    getTeacherTimetable,
    TimetableEntry,
} from "@/lib/services/timetable";

const WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
];

export default function TeacherTimetablePage() {
    const [entries, setEntries] = useState<TimetableEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedDay, setSelectedDay] = useState<string>("monday");

    useEffect(() => {
        async function loadTimetable() {
            try {
                setLoading(true);
                setError(null);

                const data = await getTeacherTimetable(selectedDay);

                setEntries(data);
            } catch (err) {
                console.error(err);

                setError("Failed to load timetable.");
            } finally {
                setLoading(false);
            }
        }

        loadTimetable();
    }, [selectedDay]);

    const groupedEntries = useMemo(() => {
        return [...entries].sort((a, b) => {
            return a.timetable_period_id - b.timetable_period_id;
        });
    }, [entries]);

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="mx-auto max-w-7xl">
                <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            Teacher Timetable
                        </h1>

                        <p className="mt-2 text-sm text-gray-600">
                            View your assigned timetable schedule.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {WEEKDAYS.map((day) => (
                            <button
                                key={day}
                                onClick={() => setSelectedDay(day)}
                                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${selectedDay === day
                                    ? "bg-black text-white"
                                    : "bg-white text-gray-700 shadow-sm hover:bg-gray-100"
                                    }`}
                            >
                                {day.charAt(0).toUpperCase() + day.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                {loading && (
                    <div className="rounded-2xl bg-white p-8 shadow-sm">
                        <p className="text-sm text-gray-500">
                            Loading timetable...
                        </p>
                    </div>
                )}

                {error && (
                    <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
                        <p className="text-sm font-medium text-red-700">
                            {error}
                        </p>
                    </div>
                )}

                {!loading && !error && groupedEntries.length === 0 && (
                    <div className="rounded-2xl bg-white p-10 text-center shadow-sm">
                        <h2 className="text-lg font-semibold text-gray-900">
                            No timetable entries found
                        </h2>

                        <p className="mt-2 text-sm text-gray-500">
                            No timetable entries are available for this day.
                        </p>
                    </div>
                )}

                {!loading && !error && groupedEntries.length > 0 && (
                    <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-100">
                                    <tr>
                                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                            Period
                                        </th>

                                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                            Subject
                                        </th>

                                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                            Room
                                        </th>

                                        <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                            Class Group
                                        </th>
                                    </tr>
                                </thead>

                                <tbody className="divide-y divide-gray-100 bg-white">
                                    {groupedEntries.map((entry) => (
                                        <tr
                                            key={entry.id}
                                            className="hover:bg-gray-50"
                                        >
                                            <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                                                Period {entry.timetable_period_id}
                                            </td>

                                            <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                                {entry.title}
                                            </td>

                                            <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                                {entry.room || "-"}
                                            </td>

                                            <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                                {entry.class_group_id}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}