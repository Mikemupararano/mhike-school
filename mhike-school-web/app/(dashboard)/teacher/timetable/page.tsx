"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type TimetableEntry = {
    id: number;
    title: string | null;
    room: string | null;
    day_of_week: string;
    timetable_period_id: number;
    teacher_id: number | null;
};

const DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
];

export default function TeacherTimetablePage() {
    const [entries, setEntries] = useState<TimetableEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDay, setSelectedDay] = useState("monday");

    const fetchTimetable = useCallback(async () => {
        try {
            setLoading(true);

            const response = await fetch(
                "/api/v1/timetables/teacher/me",
                {
                    credentials: "include",
                },
            );

            if (!response.ok) {
                throw new Error("Failed to load timetable");
            }

            const data = (await response.json()) as TimetableEntry[];

            setEntries(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void fetchTimetable();
    }, [fetchTimetable]);

    const filteredEntries = useMemo(() => {
        return entries
            .filter((entry) => entry.day_of_week === selectedDay)
            .sort(
                (a, b) =>
                    a.timetable_period_id -
                    b.timetable_period_id,
            );
    }, [entries, selectedDay]);

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-3xl font-bold">
                    My Timetable
                </h1>

                <p className="mt-1 text-gray-500">
                    View your weekly teaching schedule.
                </p>
            </div>

            <div className="flex flex-wrap gap-2">
                {DAYS.map((day) => (
                    <button
                        key={day}
                        type="button"
                        onClick={() => setSelectedDay(day)}
                        className={`rounded-xl border px-4 py-2 transition ${selectedDay === day
                            ? "bg-black text-white"
                            : "bg-white hover:bg-gray-100"
                            }`}
                    >
                        {day.charAt(0).toUpperCase() +
                            day.slice(1)}
                    </button>
                ))}
            </div>

            {loading ? (
                <div className="rounded-2xl border p-6">
                    Loading timetable...
                </div>
            ) : null}

            {!loading && filteredEntries.length === 0 ? (
                <div className="rounded-2xl border p-6 text-gray-500">
                    No timetable entries found for {selectedDay}.
                </div>
            ) : null}

            {!loading && filteredEntries.length > 0 ? (
                <div className="grid gap-4">
                    {filteredEntries.map((entry) => (
                        <div
                            key={entry.id}
                            className="rounded-2xl border bg-white p-5 shadow-sm"
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-xl font-semibold">
                                        {entry.title ??
                                            "Untitled Lesson"}
                                    </h2>

                                    <p className="mt-1 text-gray-500">
                                        Room: {entry.room ?? "TBC"}
                                    </p>
                                </div>

                                <div className="text-sm text-gray-600">
                                    Period{" "}
                                    {entry.timetable_period_id}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : null}
        </div>
    );
}