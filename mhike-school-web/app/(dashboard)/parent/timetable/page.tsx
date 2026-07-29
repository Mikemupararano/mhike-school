"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

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
    class_group_id?: number | null;
};

function formatDayName(day: TimetableDay): string {
    return day.charAt(0).toUpperCase() + day.slice(1);
}

export default function ParentTimetablePage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
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

    const [lastUpdated, setLastUpdated] =
        useState<Date | null>(null);

    const loadTimetable = useCallback(async () => {
        if (!selectedStudentId) {
            setEntries([]);
            setError(null);
            setLastUpdated(null);
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
            setLastUpdated(new Date());
        } catch (err) {
            setEntries([]);
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load timetable.",
            );
        } finally {
            setLoading(false);
        }
    }, [selectedStudentId]);

    useEffect(() => {
        void loadTimetable();
    }, [loadTimetable]);

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

    const selectedStudentName = useMemo(() => {
        if (!selectedProfile) {
            return "Selected student";
        }

        return (
            selectedProfile.student_name ??
            `Student ${selectedProfile.student_id}`
        );
    }, [selectedProfile]);

    const isLoading =
        childrenLoading || loading;

    const pageError =
        childrenError || error;

    const selectedDayName =
        formatDayName(selectedDay);

    function handlePrint(): void {
        window.print();
    }

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Child Timetable
                    </h1>

                    <p className="mt-2 max-w-3xl text-base text-slate-600">
                        View your child&apos;s weekly lessons,
                        lesson order and daily schedule.
                    </p>
                </div>

                <div className="flex flex-wrap gap-3 print:hidden">
                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() => {
                            void loadTimetable();
                        }}
                        disabled={
                            loading ||
                            !selectedStudentId
                        }
                        className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {loading
                            ? "Refreshing..."
                            : "Refresh"}
                    </button>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={handlePrint}
                        disabled={
                            !selectedStudentId ||
                            entries.length === 0
                        }
                        className="inline-flex items-center justify-center rounded-xl bg-slate-950 px-4 py-2 text-base font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        Print timetable
                    </button>
                </div>
            </header>

            <ParentPageState
                loading={childrenLoading}
                error={childrenError}
                isEmpty={profiles.length === 0}
                loadingMessage="Loading linked students..."
            >
                <div className="print:hidden">
                    <ChildSelector
                        profiles={profiles}
                        selectedStudentId={selectedStudentId}
                        onSelectStudent={setSelectedStudentId}
                        title="Linked Students"
                        description="Select a child to view their timetable."
                    />
                </div>

                {selectedProfile && (
                    <section className="rounded-2xl border border-indigo-100 bg-indigo-50 p-5 sm:p-6">
                        <p className="text-sm font-bold uppercase tracking-wide text-indigo-700">
                            Weekly timetable
                        </p>

                        <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                            <div>
                                <h2 className="text-2xl font-extrabold text-slate-950">
                                    {selectedStudentName}
                                </h2>

                                <p className="mt-1 text-base text-slate-600">
                                    {entries.length}{" "}
                                    {entries.length === 1
                                        ? "lesson"
                                        : "lessons"}{" "}
                                    scheduled across the week.
                                </p>
                            </div>

                            <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
                                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                    Viewing
                                </p>

                                <p className="mt-1 text-lg font-extrabold text-slate-950">
                                    {selectedDayName}
                                </p>
                            </div>
                        </div>

                        {lastUpdated && (
                            <p aria-live="polite" className="mt-4 text-sm text-slate-500 print:hidden">
                                Last refreshed{" "}
                                {lastUpdated.toLocaleTimeString(
                                    "en-GB",
                                    {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                    },
                                )}
                            </p>
                        )}
                    </section>
                )}

                <div className="print:hidden">
                    <TimetableDayTabs
                        selectedDay={selectedDay}
                        onSelectDay={setSelectedDay}
                    />
                </div>

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
                        <section
                            aria-labelledby="daily-timetable-heading"
                            className="rounded-2xl border bg-white p-4 sm:p-6"
                        >
                            <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <h2
                                        id="daily-timetable-heading"
                                        className="text-xl font-bold text-slate-950"
                                    >
                                        {selectedDayName}&apos;s Lessons
                                    </h2>

                                    <p className="mt-1 text-base text-slate-600">
                                        Daily lesson schedule for{" "}
                                        <span className="font-semibold text-slate-900">
                                            {selectedStudentName}
                                        </span>
                                        .
                                    </p>
                                </div>

                                <p className="text-sm font-semibold text-slate-500">
                                    {filteredEntries.length}{" "}
                                    {filteredEntries.length === 1
                                        ? "lesson"
                                        : "lessons"}
                                </p>
                            </div>

                            <div className="grid gap-4">
                                {filteredEntries.map((entry) => (
                                    <TimetableLessonCard
                                        key={entry.id}
                                        entry={entry}
                                        accent="indigo"
                                    />
                                ))}
                            </div>
                        </section>
                    )}
            </ParentPageState>
        </main>
    );
}
