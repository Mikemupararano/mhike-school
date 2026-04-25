"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import {
    getTeacherAssignments,
    type TeacherAssignment,
} from "@/lib/services/teacher";
import { UserRole } from "@/types/user";

export default function TeacherAssignmentsPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <AssignmentsContent />
        </RoleGate>
    );
}

function AssignmentsContent() {
    const [assignments, setAssignments] = useState<TeacherAssignment[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadAssignments() {
            try {
                setError(null);
                const data = await getTeacherAssignments();
                setAssignments(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load assignments",
                );
            } finally {
                setIsLoading(false);
            }
        }

        void loadAssignments();
    }, []);

    return (
        <div className="p-6">
            <h1 className="text-3xl font-extrabold">Assignments</h1>
            <p className="mt-2 text-slate-500">Manage and grade student work.</p>

            {isLoading && <p className="mt-6">Loading assignments...</p>}

            {error && (
                <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                    {error}
                </div>
            )}

            {!isLoading && !error && (
                <div className="mt-6 space-y-4">
                    {assignments.length === 0 ? (
                        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">
                            No assignments found.
                        </div>
                    ) : (
                        assignments.map((assignment) => (
                            <div
                                key={assignment.id}
                                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                            >
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <h2 className="text-xl font-bold">
                                            {assignment.title}
                                        </h2>

                                        <p className="mt-2 text-sm text-slate-500">
                                            Max score: {assignment.max_score} •{" "}
                                            {assignment.is_published
                                                ? "Published"
                                                : "Draft"}
                                        </p>

                                        {assignment.due_date && (
                                            <p className="mt-1 text-sm text-slate-500">
                                                Due:{" "}
                                                {new Date(
                                                    assignment.due_date,
                                                ).toLocaleDateString()}
                                            </p>
                                        )}
                                    </div>

                                    <Link
                                        href={`/teacher/assignments/${assignment.id}`}
                                        className="rounded-lg bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
                                    >
                                        Grade
                                    </Link>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}