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

import { getMyTeacherTimetable } from "@/lib/timetables";

type TimetableEntry = TimetableLesson & {
    teacher_id?: number | null;
};

export default function TeacherTimetablePage() {
    const [entries, setEntries] =
        useState<TimetableEntry[]>([]);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState<string | null>(null);

    const [selectedDay, setSelectedDay] =
        useState<TimetableDay>("monday");

    useEffect(() => {
        async function fetchTimetable() {
            try {
                setLoading(true);
                setError(null);

                const data =
                    await getMyTeacherTimetable();

                setEntries(data);
            } catch (err) {
                console.error(err);

                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load timetable.",
                );
            } finally {
                setLoading(false);
            }
        }

        void fetchTimetable();
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
                    View your weekly teaching schedule.
                </p>
            </div>

            <TimetableDayTabs
                selectedDay={selectedDay}
                onSelectDay={setSelectedDay}
            />

            <TimetableState
                loading={loading}
                error={error}
                isEmpty={filteredEntries.length === 0}
                selectedDay={selectedDay}
            />

            {!loading &&
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