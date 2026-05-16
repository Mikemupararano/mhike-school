"use client";

import { useEffect, useMemo, useState } from "react";

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

    useEffect(() => {
        fetchTimetable();
    }, []);

    async function fetchTimetable() {
        try {
            setLoading(true);

            const response = await fetch(
                "/api/v1/timetables/teacher/me",
                {
                    credentials: "include",
                }
            );

            if (!response.ok) {
                throw new Error("Failed to load timetable");
            }

            const data = await response.json();

            setEntries(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    const filteredEntries = useMemo(() => {
        return entries
            .filter(
                (entry) => entry.day_of_week === selectedDay
            )
            .sort(
                (a, b) =>
                    a.timetable_period_id -
                    b.timetable_period_id
            );
    }, [entries, selectedDay]);

    return (
        <div className="p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold">
                    My Timetable
                </h1>

                <p className="text-gray-500 mt-1">
                    View your weekly teaching schedule.
                </p>
            </div>

            {/* Day Tabs */}
            <div className="flex flex-wrap gap-2">
                {DAYS.map((day) => (
                    <button
                        key={day}
                        onClick={() => setSelectedDay(day)}
                        className={`px-4 py-2 rounded-xl border transition ${selectedDay === day
                            ? "bg-black text-white"
                            : "bg-white hover:bg-gray-100"
                            }`}
                    >
                        {day.charAt(0).toUpperCase() +
                            day.slice(1)}
                    </button>
                ))}
            </div>

            {/* Loading */}
            {loading && (
                <div className="rounded-2xl border p-6">
                    Loading timetable...
                </div>
            )}

            {/* Empty */}
            {!loading &&
                filteredEntries.length === 0 && (
                    <div className="rounded-2xl border p-6 text-gray-500">
                        No timetable entries found for{" "}
                        {selectedDay}.
                    </div>
                )}

            {/* Timetable */}
            {!loading &&
                filteredEntries.length > 0 && (
                    <div className="grid gap-4">
                        {filteredEntries.map((entry) => (
                            <div
                                key={entry.id}
                                className="rounded-2xl border p-5 shadow-sm bg-white"
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h2 className="text-xl font-semibold">
                                            {entry.title ??
                                                "Untitled Lesson"}
                                        </h2>

                                        <p className="text-gray-500 mt-1">
                                            Room:{" "}
                                            {entry.room ?? "TBC"}
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
                )}
        </div>
    );
}