"use client";

import { formatTimetableDay, type TimetableDay } from "./TimetableDayTabs";

type TimetableStateProps = {
    loading: boolean;
    error?: string | null;
    isEmpty: boolean;
    selectedDay: TimetableDay;
};

export default function TimetableState({
    loading,
    error,
    isEmpty,
    selectedDay,
}: TimetableStateProps) {
    if (loading) {
        return (
            <div className="rounded-2xl border bg-white p-6 text-slate-500">
                Loading timetable...
            </div>
        );
    }

    if (error) {
        return (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-700">
                {error}
            </div>
        );
    }

    if (isEmpty) {
        return (
            <div className="rounded-2xl border bg-white p-6 text-slate-500">
                No lessons found for {formatTimetableDay(selectedDay)}.
            </div>
        );
    }

    return null;
}