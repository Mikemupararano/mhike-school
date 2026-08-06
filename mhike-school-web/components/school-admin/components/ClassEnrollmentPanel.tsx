"use client";

import { useMemo, useState } from "react";

import type { User } from "@/types/user";

type ClassEnrollmentPanelProps = {
    students: User[];
    allStudents: User[];
    onEnroll: (studentId: number) => Promise<void>;
    onRemove: (studentId: number) => Promise<void>;
};

function getUserDisplayName(user: User): string {
    const fullName = user.full_name?.trim();

    if (fullName) {
        return fullName;
    }

    return user.email;
}

export default function ClassEnrollmentPanel({
    students,
    allStudents,
    onEnroll,
    onRemove,
}: ClassEnrollmentPanelProps) {
    const [selectedStudentId, setSelectedStudentId] =
        useState<number | "">("");

    const [loadingId, setLoadingId] =
        useState<number | null>(null);

    const [error, setError] =
        useState<string | null>(null);

    const availableStudents = useMemo(() => {
        const enrolledStudentIds = new Set(
            students.map((student) => student.id),
        );

        return allStudents.filter(
            (student) => !enrolledStudentIds.has(student.id),
        );
    }, [allStudents, students]);

    async function handleEnroll(): Promise<void> {
        if (selectedStudentId === "") {
            return;
        }

        const studentId = selectedStudentId;

        try {
            setError(null);
            setLoadingId(studentId);

            await onEnroll(studentId);

            setSelectedStudentId("");
        } catch (err) {
            console.error(err);

            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to enrol student.",
            );
        } finally {
            setLoadingId(null);
        }
    }

    async function handleRemove(
        studentId: number,
    ): Promise<void> {
        try {
            setError(null);
            setLoadingId(studentId);

            await onRemove(studentId);
        } catch (err) {
            console.error(err);

            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to remove student.",
            );
        } finally {
            setLoadingId(null);
        }
    }

    const enrolling =
        selectedStudentId !== "" &&
        loadingId === selectedStudentId;

    return (
        <section className="space-y-4 rounded-lg border bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-800">
                Class Enrolment
            </h3>

            {error ? (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {error}
                </div>
            ) : null}

            <div className="flex gap-2">
                <select
                    value={selectedStudentId}
                    onChange={(event) => {
                        setSelectedStudentId(
                            event.target.value
                                ? Number(event.target.value)
                                : "",
                        );
                    }}
                    disabled={loadingId !== null}
                    className="flex-1 rounded-md border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                >
                    <option value="">Select student</option>

                    {availableStudents.map((student) => (
                        <option
                            key={student.id}
                            value={student.id}
                        >
                            {getUserDisplayName(student)} ({student.email})
                        </option>
                    ))}
                </select>

                <button
                    type="button"
                    onClick={() => void handleEnroll()}
                    disabled={
                        selectedStudentId === "" ||
                        loadingId !== null
                    }
                    className="rounded-md bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {enrolling ? "Enrolling..." : "Enrol"}
                </button>
            </div>

            <div>
                <h4 className="mb-2 text-xs font-medium text-gray-500">
                    Enrolled students
                </h4>

                {students.length === 0 ? (
                    <div className="text-sm text-gray-500">
                        No students enrolled yet.
                    </div>
                ) : (
                    <ul className="space-y-2">
                        {students.map((student) => (
                            <li
                                key={student.id}
                                className="flex items-center justify-between gap-4 rounded-md border px-3 py-2 text-sm"
                            >
                                <div className="min-w-0">
                                    <div className="truncate font-medium text-slate-900">
                                        {getUserDisplayName(student)}
                                    </div>

                                    <div className="truncate text-xs text-slate-500">
                                        {student.email}
                                    </div>
                                </div>

                                <button
                                    type="button"
                                    onClick={() => {
                                        void handleRemove(student.id);
                                    }}
                                    disabled={loadingId !== null}
                                    className="shrink-0 text-xs text-red-600 hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {loadingId === student.id
                                        ? "Removing..."
                                        : "Remove"}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </section>
    );
}