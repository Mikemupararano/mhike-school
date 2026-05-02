"use client";

import Link from "next/link";

import RoleGate from "@/components/auth/RoleGate";
import { useTeacherAssignments } from "@/hooks/useTeacherAssignments";
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
    const { assignments, isLoading, error } = useTeacherAssignments();

    return (
        <div className="p-6 sm:p-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                        Assignments
                    </h1>
                    <p className="mt-2 text-slate-500">
                        Manage, publish, and grade student work.
                    </p>
                </div>

                <Link
                    href="/teacher/assignments/create"
                    className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700"
                >
                    Create assignment
                </Link>
            </div>

            {isLoading && (
                <p className="mt-6 text-sm text-slate-600">Loading assignments...</p>
            )}

            {error && (
                <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
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
                                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                                    <div>
                                        <h2 className="text-xl font-bold text-slate-900">
                                            {assignment.title}
                                        </h2>

                                        <p className="mt-2 text-sm text-slate-500">
                                            Max score: {assignment.max_score ?? "N/A"} •{" "}
                                            {assignment.is_published ? "Published" : "Draft"}
                                        </p>

                                        {assignment.due_date && (
                                            <p className="mt-1 text-sm text-slate-500">
                                                Due:{" "}
                                                {new Date(assignment.due_date).toLocaleDateString()}
                                            </p>
                                        )}
                                    </div>

                                    <Link
                                        href={`/teacher/assignments/${assignment.id}`}
                                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                                    >
                                        View / Grade
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