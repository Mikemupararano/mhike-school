"use client";

const DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
] as const;

export type TimetableFilterDay = (typeof DAYS)[number];

type TimetableDayFilterProps = {
    selectedDay: string;
    onChange: (day: string) => void;
};

function formatDay(day: string): string {
    return day.charAt(0).toUpperCase() + day.slice(1);
}

export default function TimetableDayFilter({
    selectedDay,
    onChange,
}: TimetableDayFilterProps) {
    return (
        <div className="flex flex-wrap gap-2">
            {DAYS.map((day) => (
                <button
                    key={day}
                    type="button"
                    onClick={() => onChange(day)}
                    className={`rounded-xl border px-4 py-2 text-sm font-medium transition ${selectedDay === day
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
                        }`}
                >
                    {formatDay(day)}
                </button>
            ))}
        </div>
    );
}