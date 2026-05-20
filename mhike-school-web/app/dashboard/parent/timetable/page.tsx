"use client";

import { useEffect, useState } from "react";

import TimetableDayFilter from "@/components/timetable/TimetableDayFilter";
import TimetableTable from "@/components/timetable/TimetableTable";

import {
    getParentChildTimetable,
    TimetableEntry,
} from "@/lib/services/timetable";

export default function ParentTimetablePage() {
    const [entries, setEntries] = useState<TimetableEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedDay, setSelectedDay] =
        useState<string>("monday");

    // Temporary hardcoded child selection.
    // Replace with parent-child selector integration later.
    const childId = 1;

    useEffect(() => {
        async function loadTimetable() {
            try {
                setLoading(true);
                setError(null);

                const data = await getParentChildTimetable(
                    childId,
                    undefined,
                    selectedDay
                );

                setEntries(data);
            } catch (err) {
                console.error(err);

                setError("Failed to load child timetable.");
            } finally {
                setLoading(false);
            }
        }

        loadTimetable();
    }, [selectedDay]);

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="mx-auto max-w-7xl">
                <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            Child Timetable
                        </h1>

                        <p className="mt-2 text-sm text-gray-600">
                            View your child&apos;s weekly class schedule.
                        </p>
                    </div>

                    <TimetableDayFilter
                        selectedDay={selectedDay}
                        onChange={setSelectedDay}
                    />
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

                {!loading && !error && (
                    <TimetableTable
                        entries={entries}
                        emptyTitle="No timetable entries found"
                        emptyMessage="No classes are scheduled for this day."
                    />
                )}
            </div>
        </div>
    );
}