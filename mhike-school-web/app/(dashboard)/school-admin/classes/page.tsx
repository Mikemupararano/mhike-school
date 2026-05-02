"use client";

import Link from "next/link";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";
import { useClasses } from "@/hooks/useClasses";

export default function SchoolAdminClassesPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <ClassesContent />
        </RoleGate>
    );
}

function ClassesContent() {
    const { classes, isLoading, error } = useClasses();

    return (
        <div className="p-6 sm:p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                        Classes
                    </h1>
                    <p className="mt-2 text-base text-slate-600 sm:text-lg">
                        Manage classes, assign teachers, and enrol students.
                    </p>
                </div>

                <Link
                    href="/school-admin/classes/create"
                    className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
                >
                    Add class
                </Link>
            </div>

            {isLoading && <p className="mt-8 text-slate-600">Loading classes...</p>}

            {error && <p className="mt-8 text-red-500">{error}</p>}

            {!isLoading && !error && (
                <div className="mt-8">
                    {classes.length === 0 ? (
                        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
                            <h2 className="text-lg font-semibold text-slate-900">
                                No classes yet
                            </h2>
                            <p className="mt-2 text-sm text-slate-500">
                                Get started by creating your first class.
                            </p>
                        </div>
                    ) : (
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                            {classes.map((cls) => (
                                <Link
                                    key={cls.id}
                                    href={`/school-admin/classes/${cls.id}`}
                                    className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md"
                                >
                                    <div className="text-lg font-semibold text-slate-900">
                                        {cls.name}
                                    </div>

                                    <div className="mt-2 text-sm text-slate-500">
                                        Teacher ID: {cls.teacher_id ?? "Not assigned"}
                                    </div>

                                    <div className="mt-2 text-sm text-slate-500">
                                        Created: {new Date(cls.created_at).toLocaleDateString()}
                                    </div>

                                    <div className="mt-3 text-xs text-slate-400">
                                        View class →
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}