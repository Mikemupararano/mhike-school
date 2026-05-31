"use client";

import {
    useEffect,
    useMemo,
    useState,
} from "react";

import ChildSelector from "@/components/parent/ChildSelector";

import TimetableDayTabs, {
    type TimetableDay,
} from "@/components/timetable/TimetableDayTabs";
import TimetableLessonCard, {
    type TimetableLesson,
} from "@/components/timetable/TimetableLessonCard";
import TimetableState from "@/components/timetable/TimetableState";

import { useParentChildren } from "@/hooks/useParentChildren";

import { getChildTimetable } from "@/lib/timetables";

type TimetableEntry = TimetableLesson & {
    class_group_id: number | null;
};

export default function ParentTimetablePage() {
    const {
        profiles,
        selectedStudentId,
        setSelectedStudentId,
        loading: childrenLoading,
        error: childrenError,
    } = useParentChildren();

    const [entries, setEntries] =
        useState<TimetableEntry[]>([]);

    const [selectedDay, setSelectedDay] =
        useState<TimetableDay>("monday");

    const [loading, setLoading] =
        useState(false);

    const [error, setError] =
        useState<string | null>(null);

    useEffect(() => {
        async function loadTimetable() {
            if (!selectedStudentId) {
                setEntries([]);
                return;
            }

            try {
                setLoading(true);
                setError(null);

                const data =
                    await getChildTimetable(
                        selectedStudentId,
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
    }, [selectedStudentId]);

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

    const isLoading =
        childrenLoading || loading;

    const pageError =
        childrenError || error;

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

            {!childrenLoading &&
                !childrenError &&
                profiles.length > 0 && (
                    <ChildSelector
                        profiles={profiles}
                        selectedStudentId={
                            selectedStudentId
                        }
                        onSelectStudent={
                            setSelectedStudentId
                        }
                        title="Linked Students"
                        description="Select a child to view their timetable."
                    />
                )}

            <TimetableDayTabs
                selectedDay={selectedDay}
                onSelectDay={setSelectedDay}
            />

            <TimetableState
                loading={isLoading}
                error={pageError}
                isEmpty={
                    !selectedStudentId ||
                    filteredEntries.length === 0
                }
                selectedDay={selectedDay}
            />

            {!isLoading &&
                !pageError &&
                selectedStudentId &&
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