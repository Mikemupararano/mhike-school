"use client";

import { useState } from "react";
import type { User } from "@/types/user";

type ClassEnrollmentPanelProps = {
    students: User[];
    allStudents: User[];
    onEnroll: (studentId: number) => Promise<void>;
    onRemove: (studentId: number) => Promise<void>;
};

export default function ClassEnrollmentPanel({
    students,
    allStudents,
    onEnroll,
    onRemove,
}: ClassEnrollmentPanelProps) {
    const [selectedStudentId, setSelectedStudentId] = useState<number | "">("");
    const [loadingId, setLoadingId] = useState<number | null>(null);

    const availableStudents = allStudents.filter(
        (s) => !students.some((enrolled) => enrolled.id === s.id),
    );

    async function handleEnroll() {
        if (!selectedStudentId) return;

        setLoadingId(selectedStudentId);
        await onEnroll(Number(selectedStudentId));
        setSelectedStudentId("");
        setLoadingId(null);
    }

    async function handleRemove(studentId: number) {
        setLoadingId(studentId);
        await onRemove(studentId);
        setLoadingId(null);
    }

    return (
        <div className="space-y-4 rounded-lg border bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-800">
                Class Enrollment
            </h3>

            {/* Enroll new student */}
            <div className="flex gap-2">
                <select
                    value={selectedStudentId}
                    onChange={(e) =>
                        setSelectedStudentId(
                            e.target.value ? Number(e.target.value) : "",
                        )
                    }
                    className="flex-1 rounded-md border px-3 py-2 text-sm"
                >
                    <option value="">Select student</option>
                    {availableStudents.map((student) => (
                        <option key={student.id} value={student.id}>
                            {student.first_name} {student.last_name} ({student.email})
                        </option>
                    ))}
                </select>

                <button
                    type="button"
                    onClick={handleEnroll}
                    disabled={!selectedStudentId}
                    className="rounded-md bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                    Enroll
                </button>
            </div>

            {/* Current students */}
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
                                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                            >
                                <span>
                                    {student.first_name} {student.last_name}
                                </span>

                                <button
                                    type="button"
                                    onClick={() => handleRemove(student.id)}
                                    disabled={loadingId === student.id}
                                    className="text-xs text-red-600 hover:underline disabled:opacity-50"
                                >
                                    {loadingId === student.id ? "Removing..." : "Remove"}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}