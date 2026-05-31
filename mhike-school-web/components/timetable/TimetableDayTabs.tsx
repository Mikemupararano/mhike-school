"use client";

export const TIMETABLE_DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
] as const;

export type TimetableDay =
    (typeof TIMETABLE_DAYS)[number];

type TimetableDayTabsProps = {
    selectedDay: TimetableDay;
    onSelectDay: (day: TimetableDay) => void;
};

export function formatTimetableDay(
    day: string,
): string {
    return day.charAt(0).toUpperCase() + day.slice(1);
}

export default function TimetableDayTabs({
    selectedDay,
    onSelectDay,
}: TimetableDayTabsProps) {
    return (
        <div className="flex flex-wrap gap-2">
            {TIMETABLE_DAYS.map((day) => (
                <button
                    key={day}
                    type="button"
                    onClick={() => onSelectDay(day)}
                    className={`rounded-xl border px-4 py-2 font-semibold transition ${selectedDay === day
                        ? "bg-slate-950 text-white"
                        : "bg-white text-slate-700 hover:bg-slate-50"
                        }`}
                >
                    {formatTimetableDay(day)}
                </button>
            ))}
        </div>
    );
}