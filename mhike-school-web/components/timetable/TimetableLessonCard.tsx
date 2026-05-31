"use client";

export type TimetableLesson = {
    id: number;
    title: string | null;
    room: string | null;
    day_of_week: string;
    timetable_period_id: number;
    class_group_id?: number | null;
    teacher_id?: number | null;
};

type TimetableLessonCardProps = {
    entry: TimetableLesson;
    accent?: "blue" | "indigo";
};

const accentClasses = {
    blue: "bg-blue-50 text-blue-700",
    indigo: "bg-indigo-50 text-indigo-700",
};

export default function TimetableLessonCard({
    entry,
    accent = "blue",
}: TimetableLessonCardProps) {
    return (
        <article className="rounded-2xl border bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="text-xl font-bold text-slate-950">
                        {entry.title ?? "Untitled Lesson"}
                    </h2>

                    <p className="mt-1 text-slate-500">
                        Room: {entry.room ?? "TBC"}
                    </p>
                </div>

                <span
                    className={`rounded-full px-4 py-2 text-sm font-bold ${accentClasses[accent]}`}
                >
                    Period {entry.timetable_period_id}
                </span>
            </div>
        </article>
    );
}