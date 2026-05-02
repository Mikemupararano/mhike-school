"use client";

import { useState } from "react";
import type { User } from "@/types/user";

type AssignTeacherPanelProps = {
    teachers: User[];
    currentTeacherId?: number | null;
    onAssign: (teacherId: number) => Promise<void>;
};

export default function AssignTeacherPanel({
    teachers,
    currentTeacherId,
    onAssign,
}: AssignTeacherPanelProps) {
    const [selectedTeacherId, setSelectedTeacherId] = useState<
        number | ""
    >(currentTeacherId ?? "");
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function handleAssign() {
        if (!selectedTeacherId) return;

        setIsSubmitting(true);
        await onAssign(Number(selectedTeacherId));
        setIsSubmitting(false);
    }

    return (
        <div className="space-y-4 rounded-lg border bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-800">
                Assign Teacher
            </h3>

            <div className="flex gap-2">
                <select
                    value={selectedTeacherId}
                    onChange={(e) =>
                        setSelectedTeacherId(
                            e.target.value ? Number(e.target.value) : "",
                        )
                    }
                    className="flex-1 rounded-md border px-3 py-2 text-sm"
                >
                    <option value="">Select teacher</option>
                    {teachers.map((teacher) => (
                        <option key={teacher.id} value={teacher.id}>
                            {teacher.first_name} {teacher.last_name} ({teacher.email})
                        </option>
                    ))}
                </select>

                <button
                    type="button"
                    onClick={handleAssign}
                    disabled={!selectedTeacherId || isSubmitting}
                    className="rounded-md bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                    {isSubmitting ? "Saving..." : "Assign"}
                </button>
            </div>

            {currentTeacherId && (
                <div className="text-xs text-gray-500">
                    Current teacher assigned
                </div>
            )}
        </div>
    );
}