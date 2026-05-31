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

import { getChildTimetable } from "@/lib/timetables";

type TimetableEntry = TimetableLesson & {
    class_group_id: number | null;
};

export default function ParentTimetablePage() {
    const [entries, setEntries] =
        useState<TimetableEntry[]>([]);

    const [selectedDay, setSelectedDay] =
        useState<TimetableDay>("monday");

    /**
     * TODO:
     * Replace with real child selection once
     * parent/student linking UI is implemented.
     */
    const [selectedChildId] =
        useState(1);

    /**
     * TODO:
     * Replace with real class group selection once
     * parent child-selector data is wired in.
     */
    const [selectedClassGroupId] =
        useState(1);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState<string | null>(null);

    useEffect(() => {
        async function loadTimetable() {
            try {
                setLoading(true);
                setError(null);

                const data =
                    await getChildTimetable(
                        selectedChildId,
                        selectedClassGroupId,
                    );

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
    }, [
        selectedChildId,
        selectedClassGroupId,
    ]);

    const filteredEntries =
        useMemo(() => {
            return entries
                .filter(
                    (
                        entry,
                    ) =>
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
                    Child Timetable
                </h1>

                <p className="mt-2 text-slate-500">
                    View your child&apos;s weekly lessons.
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
                                accent="indigo"
                            />
                        ))}
                    </section>
                )}
        </main>
    );
}