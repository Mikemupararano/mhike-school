"use client";

import {
    useCallback,
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

function formatDayName(day: TimetableDay): string {
    return day.charAt(0).toUpperCase() + day.slice(1);
}

export default function StudentTimetablePage() {
    const [entries, setEntries] =
        useState<TimetableEntry[]>([]);

    const [selectedDay, setSelectedDay] =
        useState<TimetableDay>("monday");

    const [isLoading, setIsLoading] =
        useState(true);

    const [error, setError] =
        useState<string | null>(null);

    const [lastUpdated, setLastUpdated] =
        useState<Date | null>(null);

    const loadTimetable = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);

            const data =
                await getMyStudentTimetable();

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
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadTimetable();
    }, [loadTimetable]);

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

    const selectedDayName =
        formatDayName(selectedDay);

    function handlePrint(): void {
        window.print();
    }

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <header className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 print:border-0 print:p-0 print:shadow-none">
                <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700 print:hidden">
                            Student portal
                        </p>

                        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950">
                            My Timetable
                        </h1>

                        <p className="mt-2 max-w-3xl text-base leading-7 text-slate-600">
                            View your lessons, lesson order and daily
                            schedule for the school week.
                        </p>

                        {lastUpdated && (
                            <p
                                aria-live="polite"
                                className="mt-2 text-sm text-slate-500 print:hidden"
                            >
                                Last refreshed{" "}
                                {lastUpdated.toLocaleTimeString(
                                    "en-GB",
                                    {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                    },
                                )}
                                .
                            </p>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-3 print:hidden">
                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadTimetable();
                            }}
                            disabled={isLoading}
                            className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-base font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {isLoading
                                ? "Refreshing..."
                                : "Refresh"}
                        </button>

                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={handlePrint}
                            disabled={entries.length === 0}
                            className="inline-flex items-center justify-center rounded-xl bg-slate-950 px-4 py-2.5 text-base font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            Print timetable
                        </button>
                    </div>
                </div>
            </header>

            <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5 sm:p-6 print:border-slate-300 print:bg-white">
                <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                    Weekly timetable
                </p>

                <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                        <h2 className="text-2xl font-extrabold text-slate-950">
                            {selectedDayName}
                        </h2>

                        <p className="mt-1 text-base text-slate-600">
                            {filteredEntries.length}{" "}
                            {filteredEntries.length === 1
                                ? "lesson"
                                : "lessons"}{" "}
                            scheduled for this day.
                        </p>
                    </div>

                    <div className="w-fit rounded-xl bg-white px-4 py-3 shadow-sm print:shadow-none">
                        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                            Weekly total
                        </p>

                        <p className="mt-1 text-2xl font-extrabold text-slate-950">
                            {entries.length}
                        </p>
                    </div>
                </div>
            </section>

            <div className="print:hidden">
                <TimetableDayTabs
                    selectedDay={selectedDay}
                    onSelectDay={setSelectedDay}
                />
            </div>

            <TimetableState
                loading={isLoading}
                error={error}
                isEmpty={filteredEntries.length === 0}
                selectedDay={selectedDay}
            />

            {!isLoading &&
                !error &&
                filteredEntries.length > 0 && (
                    <section
                        aria-labelledby="daily-timetable-heading"
                        className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6 print:border-slate-300 print:shadow-none"
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
                                    Your complete lesson schedule for the
                                    selected day.
                                </p>
                            </div>

                            <p className="shrink-0 rounded-full bg-slate-100 px-3 py-1.5 text-sm font-semibold text-slate-600 print:bg-white print:px-0">
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
                                    accent="blue"
                                />
                            ))}
                        </div>
                    </section>
                )}
        </main>
    );
}
