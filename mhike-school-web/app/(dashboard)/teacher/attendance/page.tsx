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
    const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
    const [session, setSession] = useState<AttendanceSession | null>(null);

    const [studentId, setStudentId] = useState("");
    const [status, setStatus] = useState<AttendanceStatus>("present");
    const [notes, setNotes] = useState("");

    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadTeacherTimetable() {
            try {
                setIsLoading(true);
                setError(null);

                const response = await fetch("/api/v1/timetables/teacher/me", {
                    credentials: "include",
                });

                if (!response.ok) {
                    throw new Error("Failed to load teacher timetable.");
                }

                const data = (await response.json()) as TimetableEntry[];

                setEntries(data);

                if (data.length > 0) {
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
        return entries.find((entry) => entry.id === selectedEntryId) ?? null;
    }, [entries, selectedEntryId]);

    async function createAttendanceSession() {
        if (!selectedEntry || selectedEntry.class_group_id === null) {
            setError("Select a timetable entry with a class group first.");
            return;
        }

        try {
            setIsSubmitting(true);
            setError(null);
            setMessage(null);

            const response = await fetch("/api/v1/attendance/sessions", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    school_id: 0,
                    class_group_id: selectedEntry.class_group_id,
                    session_date: getTodayIsoDate(),
                    session_type: "am",
                    timetable_entry_id: selectedEntry.id,
                    timetable_period_id: selectedEntry.timetable_period_id,
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to create attendance session.");
            }

            const data = (await response.json()) as AttendanceSession;

            setSession(data);
            setMessage("Attendance session created.");
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

    async function submitAttendanceRecord() {
        if (!session) {
            setError("Create an attendance session first.");
            return;
        }

        const parsedStudentId = Number(studentId);

        if (!Number.isInteger(parsedStudentId) || parsedStudentId <= 0) {
            setError("Enter a valid student ID.");
            return;
        }

        try {
            setIsSubmitting(true);
            setError(null);
            setMessage(null);

            const response = await fetch("/api/v1/attendance/records", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    attendance_session_id: session.id,
                    student_id: parsedStudentId,
                    status,
                    notes: notes.trim() || null,
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to submit attendance record.");
            }

            setStudentId("");
            setStatus("present");
            setNotes("");
            setMessage("Attendance record submitted.");
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to submit attendance record.",
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
                    Select a timetable lesson, create a register session, and
                    mark pupil attendance.
                </p>
            </div>

            {isLoading ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    Loading timetable...
                </section>
            ) : error ? (
                <section className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-700">
                    {error}
                </section>
            ) : entries.length === 0 ? (
                <section className="rounded-2xl border bg-white p-6 text-slate-500">
                    No timetable lessons found.
                </section>
            ) : (
                <>
                    {message ? (
                        <section className="rounded-2xl border border-green-200 bg-green-50 p-4 font-semibold text-green-700">
                            {message}
                        </section>
                    ) : null}

                    <section className="rounded-2xl border bg-white p-6">
                        <h2 className="text-xl font-bold text-slate-950">
                            Select Lesson
                        </h2>

                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {entries.map((entry) => (
                                <button
                                    key={entry.id}
                                    type="button"
                                    onClick={() => {
                                        setSelectedEntryId(entry.id);
                                        setSession(null);
                                        setMessage(null);
                                    }}
                                    className={`rounded-xl border p-4 text-left transition ${selectedEntryId === entry.id
                                        ? "border-slate-950 bg-slate-950 text-white"
                                        : "bg-white text-slate-700 hover:bg-slate-50"
                                        }`}
                                >
                                    <div className="font-bold">
                                        {entry.title ?? "Untitled Lesson"}
                                    </div>

                                    <div className="mt-1 text-sm opacity-80">
                                        {entry.day_of_week} · Period{" "}
                                        {entry.timetable_period_id} · Room{" "}
                                        {entry.room ?? "TBC"}
                                    </div>
                                </button>
                            ))}
                        </div>

                        <button
                            type="button"
                            disabled={isSubmitting || !selectedEntry}
                            onClick={createAttendanceSession}
                            className="mt-5 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {session
                                ? `Session Created #${session.id}`
                                : "Create Register Session"}
                        </button>
                    </section>

                    <section className="rounded-2xl border bg-white p-6">
                        <h2 className="text-xl font-bold text-slate-950">
                            Mark Attendance
                        </h2>

                        <div className="mt-4 grid gap-4 md:grid-cols-3">
                            <input
                                value={studentId}
                                onChange={(event) =>
                                    setStudentId(event.target.value)
                                }
                                placeholder="Student ID"
                                inputMode="numeric"
                                className="rounded-xl border px-4 py-3"
                            />

                            <select
                                value={status}
                                onChange={(event) =>
                                    setStatus(
                                        event.target.value as AttendanceStatus,
                                    )
                                }
                                className="rounded-xl border bg-white px-4 py-3"
                            >
                                {STATUS_OPTIONS.map((option) => (
                                    <option key={option} value={option}>
                                        {formatStatus(option)}
                                    </option>
                                ))}
                            </select>

                            <input
                                value={notes}
                                onChange={(event) =>
                                    setNotes(event.target.value)
                                }
                                placeholder="Notes optional"
                                className="rounded-xl border px-4 py-3"
                            />
                        </div>

                        <button
                            type="button"
                            disabled={isSubmitting || !session}
                            onClick={submitAttendanceRecord}
                            className="mt-5 rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            Submit Attendance Record
                        </button>
                    </section>
                </>
            )}
        </main>
    );
}