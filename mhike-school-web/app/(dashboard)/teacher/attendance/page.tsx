"use client";

import { useEffect, useMemo, useState } from "react";

type TimetableEntry = {
    id: number;
    title: string | null;
    room: string | null;
    day_of_week: string;
    timetable_period_id: number;
    class_group_id: number | null;
};

type AttendanceSession = {
    id: number;
    school_id: number;
    class_group_id: number;
    session_date: string;
    session_type: "am" | "pm";
    timetable_entry_id: number | null;
    timetable_period_id: number | null;
};

type AttendanceStatus =
    | "present"
    | "late"
    | "authorised_absence"
    | "unauthorised_absence";

type Student = {
    id: number;
    first_name?: string;
    last_name?: string;
    email?: string;
};

type StudentAttendance = {
    student_id: number;
    status: AttendanceStatus;
    notes: string;
};

const STATUS_OPTIONS: AttendanceStatus[] = [
    "present",
    "late",
    "authorised_absence",
    "unauthorised_absence",
];

function formatStatus(status: AttendanceStatus) {
    return status.replaceAll("_", " ");
}

function getTodayIsoDate() {
    return new Date().toISOString().slice(0, 10);
}

export default function TeacherAttendanceRegisterPage() {
    const [entries, setEntries] = useState<TimetableEntry[]>([]);
    const [students, setStudents] = useState<Student[]>([]);
    const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

    const [session, setSession] =
        useState<AttendanceSession | null>(null);

    const [attendanceMap, setAttendanceMap] = useState<
        Record<number, StudentAttendance>
    >({});

    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadTeacherTimetable() {
            try {
                setIsLoading(true);
                setError(null);

                const response = await fetch(
                    "/api/v1/timetables/teacher/me",
                    {
                        credentials: "include",
                    },
                );

                if (!response.ok) {
                    throw new Error(
                        "Failed to load teacher timetable.",
                    );
                }

                const data =
                    (await response.json()) as TimetableEntry[];

                setEntries(data);

                const todayName = new Date()
                    .toLocaleDateString("en-GB", {
                        weekday: "long",
                    })
                    .toLowerCase();

                const todaysEntries = data.filter(
                    (entry) =>
                        entry.day_of_week.toLowerCase() ===
                        todayName,
                );

                if (todaysEntries.length > 0) {
                    setSelectedEntryId(
                        todaysEntries[0].id,
                    );
                } else if (data.length > 0) {
                    setSelectedEntryId(data[0].id);
                }
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load teacher timetable.",
                );
            } finally {
                setIsLoading(false);
            }
        }

        void loadTeacherTimetable();
    }, []);

    const selectedEntry = useMemo(() => {
        return (
            entries.find(
                (entry) => entry.id === selectedEntryId,
            ) ?? null
        );
    }, [entries, selectedEntryId]);

    useEffect(() => {
        async function loadStudents() {
            if (
                !selectedEntry ||
                selectedEntry.class_group_id === null
            ) {
                setStudents([]);
                setAttendanceMap({});
                return;
            }

            try {
                setError(null);

                const response = await fetch(
                    `/api/v1/classes/${selectedEntry.class_group_id}/students`,
                    {
                        credentials: "include",
                    },
                );

                if (!response.ok) {
                    throw new Error(
                        "Failed to load class pupils.",
                    );
                }

                const data =
                    (await response.json()) as Student[];

                setStudents(data);

                const initialMap: Record<
                    number,
                    StudentAttendance
                > = {};

                for (const student of data) {
                    initialMap[student.id] = {
                        student_id: student.id,
                        status: "present",
                        notes: "",
                    };
                }

                setAttendanceMap(initialMap);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load pupils.",
                );
            }
        }

        void loadStudents();
    }, [selectedEntry]);

    function updateStudentAttendance(
        studentId: number,
        updates: Partial<StudentAttendance>,
    ) {
        setAttendanceMap((previous) => ({
            ...previous,
            [studentId]: {
                student_id: studentId,
                status:
                    previous[studentId]?.status ??
                    "present",
                notes:
                    previous[studentId]?.notes ?? "",
                ...updates,
            },
        }));
    }

    async function createAttendanceSession() {
        if (
            !selectedEntry ||
            selectedEntry.class_group_id === null
        ) {
            setError(
                "Select a timetable entry with a class group first.",
            );
            return;
        }

        try {
            setIsSubmitting(true);
            setError(null);
            setMessage(null);

            const response = await fetch(
                "/api/v1/attendance/sessions",
                {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        school_id: 0,
                        class_group_id:
                            selectedEntry.class_group_id,
                        session_date:
                            getTodayIsoDate(),
                        session_type: "am",
                        timetable_entry_id:
                            selectedEntry.id,
                        timetable_period_id:
                            selectedEntry.timetable_period_id,
                    }),
                },
            );

            if (!response.ok) {
                throw new Error(
                    "Failed to create attendance session.",
                );
            }

            const data =
                (await response.json()) as AttendanceSession;

            setSession(data);

            setMessage(
                "Attendance session created.",
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to create attendance session.",
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    async function submitAllAttendanceRecords() {
        if (!session) {
            setError(
                "Create an attendance session first.",
            );
            return;
        }

        try {
            setIsSubmitting(true);
            setError(null);
            setMessage(null);

            const attendanceValues = Object.values(
                attendanceMap,
            );

            const response = await fetch(
                "/api/v1/attendance/records/bulk",
                {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        records:
                            attendanceValues.map(
                                (item) => ({
                                    attendance_session_id:
                                        session.id,
                                    student_id:
                                        item.student_id,
                                    status: item.status,
                                    notes:
                                        item.notes.trim() ||
                                        null,
                                }),
                            ),
                    }),
                },
            );

            if (!response.ok) {
                throw new Error(
                    "Failed to submit attendance records.",
                );
            }

            setMessage(
                "Attendance records submitted successfully.",
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to submit attendance records.",
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Attendance Register
                </h1>

                <p className="mt-2 text-slate-500">
                    Select a lesson and mark
                    attendance for the class.
                </p>
            </div>

            {message ? (
                <section className="rounded-2xl border border-green-200 bg-green-50 p-4 font-semibold text-green-700">
                    {message}
                </section>
            ) : null}

            {error ? (
                <section className="rounded-2xl border border-red-200 bg-red-50 p-4 font-semibold text-red-700">
                    {error}
                </section>
            ) : null}

            {isLoading ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Loading timetable...
                </section>
            ) : (
                <>
                    <section className="rounded-2xl border bg-white p-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold">
                                Today&apos;s Lessons
                            </h2>

                            <span className="rounded-full bg-blue-100 px-4 py-2 text-sm font-semibold text-blue-700">
                                Auto-selected today&apos;s lesson
                            </span>
                        </div>

                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {entries.map((entry) => (
                                <button
                                    key={entry.id}
                                    type="button"
                                    onClick={() => {
                                        setSelectedEntryId(
                                            entry.id,
                                        );

                                        setSession(null);
                                        setMessage(null);
                                    }}
                                    className={`rounded-xl border p-4 text-left transition ${selectedEntryId ===
                                        entry.id
                                        ? "border-slate-950 bg-slate-950 text-white"
                                        : "bg-white text-slate-700 hover:bg-slate-50"
                                        }`}
                                >
                                    <div className="font-bold">
                                        {entry.title ??
                                            "Untitled Lesson"}
                                    </div>

                                    <div className="mt-1 text-sm opacity-80">
                                        {
                                            entry.day_of_week
                                        }{" "}
                                        · Period{" "}
                                        {
                                            entry.timetable_period_id
                                        }
                                    </div>
                                </button>
                            ))}
                        </div>

                        <button
                            type="button"
                            disabled={
                                isSubmitting ||
                                !selectedEntry
                            }
                            onClick={
                                createAttendanceSession
                            }
                            className="mt-5 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {session
                                ? `Session Created #${session.id}`
                                : "Create Register Session"}
                        </button>
                    </section>

                    <section className="rounded-2xl border bg-white p-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold">
                                Pupil Attendance
                            </h2>

                            <span className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">
                                {students.length} pupils
                            </span>
                        </div>

                        {students.length === 0 ? (
                            <div className="mt-4 text-slate-500">
                                No pupils found for this
                                class.
                            </div>
                        ) : (
                            <div className="mt-5 space-y-4">
                                {students.map(
                                    (student) => {
                                        const attendance =
                                            attendanceMap[
                                            student.id
                                            ];

                                        return (
                                            <div
                                                key={
                                                    student.id
                                                }
                                                className="grid gap-4 rounded-xl border p-4 md:grid-cols-4"
                                            >
                                                <div>
                                                    <div className="font-semibold text-slate-950">
                                                        {
                                                            student.first_name
                                                        }{" "}
                                                        {
                                                            student.last_name
                                                        }
                                                    </div>

                                                    <div className="text-sm text-slate-500">
                                                        #
                                                        {
                                                            student.id
                                                        }
                                                    </div>
                                                </div>

                                                <select
                                                    value={
                                                        attendance?.status ??
                                                        "present"
                                                    }
                                                    onChange={(
                                                        event,
                                                    ) =>
                                                        updateStudentAttendance(
                                                            student.id,
                                                            {
                                                                status:
                                                                    event
                                                                        .target
                                                                        .value as AttendanceStatus,
                                                            },
                                                        )
                                                    }
                                                    className="rounded-xl border px-4 py-3"
                                                >
                                                    {STATUS_OPTIONS.map(
                                                        (
                                                            option,
                                                        ) => (
                                                            <option
                                                                key={
                                                                    option
                                                                }
                                                                value={
                                                                    option
                                                                }
                                                            >
                                                                {formatStatus(
                                                                    option,
                                                                )}
                                                            </option>
                                                        ),
                                                    )}
                                                </select>

                                                <input
                                                    value={
                                                        attendance?.notes ??
                                                        ""
                                                    }
                                                    onChange={(
                                                        event,
                                                    ) =>
                                                        updateStudentAttendance(
                                                            student.id,
                                                            {
                                                                notes:
                                                                    event
                                                                        .target
                                                                        .value,
                                                            },
                                                        )
                                                    }
                                                    placeholder="Notes optional"
                                                    className="rounded-xl border px-4 py-3"
                                                />

                                                <div className="flex items-center text-sm text-slate-500">
                                                    Ready
                                                </div>
                                            </div>
                                        );
                                    },
                                )}
                            </div>
                        )}

                        <button
                            type="button"
                            disabled={
                                isSubmitting ||
                                !session ||
                                students.length === 0
                            }
                            onClick={
                                submitAllAttendanceRecords
                            }
                            className="mt-6 rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            Submit Full Register
                        </button>
                    </section>
                </>
            )}
        </main>
    );
}