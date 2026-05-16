"use client";

import { useEffect, useMemo, useState } from "react";

type TimetableEntry = {
    id: number;
    title: string | null;
    room: string | null;
    day_of_week: string;
    timetable_period_id: number;
    class_group_id: number | null;
};

const DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
];

function formatDay(day: string) {
    return day.charAt(0).toUpperCase() + day.slice(1);
}

export default function ParentTimetablePage() {
    const [entries, setEntries] = useState<TimetableEntry[]>([]);
    const [selectedDay, setSelectedDay] = useState("monday");
    const [selectedChildId] = useState(1);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadTimetable() {
            try {
                setLoading(true);
                setError(null);

                const response = await fetch(
                    `/api/v1/timetables/parent/child/${selectedChildId}?class_group_id=1`,
                    {
                        credentials: "include",
                    },
                );

                if (!response.ok) {
                    throw new Error(
                        "Failed to load child timetable.",
                    );
                }

                const data =
                    (await response.json()) as TimetableEntry[];

                setEntries(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load timetable.",
                );
            } finally {
                setLoading(false);
            }
        }

        void loadTimetable();
    }, [selectedChildId]);

    const filteredEntries = useMemo(() => {
        return entries
            .filter(
                (entry) =>
                    entry.day_of_week === selectedDay,
            )
            .sort(
                (first, second) =>
                    first.timetable_period_id -
                    second.timetable_period_id,
            );
    }, [entries, selectedDay]);

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Child Timetable
                </h1>

                <p className="mt-2 text-slate-500">
                    View your child&apos;s weekly lessons.
                </p>
            </div>

            {/* Day selector */}
            <div className="flex flex-wrap gap-2">
                {DAYS.map((day) => (
                    <button
                        key={day}
                        type="button"
                        onClick={() =>
                            setSelectedDay(day)
                        }
                        className={`rounded-xl border px-4 py-2 font-semibold transition ${selectedDay === day
                            ? "bg-slate-950 text-white"
                            : "bg-white text-slate-700 hover:bg-slate-50"
                            }`}
                    >
                        {formatDay(day)}
                    </button>
                ))}
            </div>

            {/* Loading */}
            {loading ? (
                <div className="rounded-2xl border bg-white p-6 text-slate-500">
                    Loading timetable...
                </div>
            ) : error ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-700">
                    {error}
                </div>
            ) : filteredEntries.length === 0 ? (
                <div className="rounded-2xl border bg-white p-6 text-slate-500">
                    No lessons found for{" "}
                    {formatDay(selectedDay)}.
                </div>
            ) : (
                <section className="grid gap-4">
                    {filteredEntries.map((entry) => (
                        <article
                            key={entry.id}
                            className="rounded-2xl border bg-white p-5 shadow-sm"
                        >
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        {entry.title ??
                                            "Untitled Lesson"}
                                    </h2>

                                    <p className="mt-1 text-slate-500">
                                        Room:{" "}
                                        {entry.room ??
                                            "TBC"}
                                    </p>
                                </div>

                                <span className="rounded-full bg-indigo-50 px-4 py-2 text-sm font-bold text-indigo-700">
                                    Period{" "}
                                    {
                                        entry.timetable_period_id
                                    }
                                </span>
                            </div>
                        </article>
                    ))}
                </section>
            )}
        </main>
    );
}