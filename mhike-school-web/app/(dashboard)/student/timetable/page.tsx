"use client";

import {
    useEffect,
    useMemo,
    useState,
} from "react";

import TimetableDayTabs, {
    type TimetableDay,
} from "@/components/timetable/TimetableDayTabs";
import TimetableLessonCard, {
    type TimetableLesson,
} from "@/components/timetable/TimetableLessonCard";
import TimetableState from "@/components/timetable/TimetableState";

import { getMyStudentTimetable } from "@/lib/timetables";

type TimetableEntry = TimetableLesson & {
    class_group_id?: number | null;
};

export default function StudentTimetablePage() {
    const [entries, setEntries] =
        useState<TimetableEntry[]>([]);

    const [selectedDay, setSelectedDay] =
        useState<TimetableDay>("monday");

    const [isLoading, setIsLoading] =
        useState(true);

    const [error, setError] =
        useState<string | null>(null);

    useEffect(() => {
        async function loadTimetable() {
            try {
                setIsLoading(true);
                setError(null);

                const data =
                    await getMyStudentTimetable();

                setEntries(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load timetable.",
                );
            } finally {
                setIsLoading(false);
            }
        }

        void loadTimetable();
    }, []);

    const filteredEntries =
        useMemo(() => {
            return entries
                .filter(
                    (entry) =>
                        entry.day_of_week ===
                        selectedDay,
                )
                .sort(
                    (
                        first,
                        second,
                    ) =>
                        first.timetable_period_id -
                        second.timetable_period_id,
                );
        }, [
            entries,
            selectedDay,
        ]);

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    My Timetable
                </h1>

                <p className="mt-2 text-slate-500">
                    View your lessons for the school week.
                </p>
            </div>

            <TimetableDayTabs
                selectedDay={selectedDay}
                onSelectDay={setSelectedDay}
            />

            <TimetableState
                loading={isLoading}
                error={error}
                isEmpty={filteredEntries.length === 0}
                selectedDay={selectedDay}
            />

            {!isLoading &&
                !error &&
                filteredEntries.length > 0 && (
                    <section className="grid gap-4">
                        {filteredEntries.map((entry) => (
                            <TimetableLessonCard
                                key={entry.id}
                                entry={entry}
                                accent="blue"
                            />
                        ))}
                    </section>
                )}
        </main>
    );
}