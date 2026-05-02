"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import RoleGate from "@/components/auth/RoleGate";
import SchoolUserTable from "@/components/school-admin/components/SchoolUserTable";
import { useSchoolUsers } from "@/hooks/useSchoolUsers";
import { UserRole, type User } from "@/types/user";

export default function SchoolAdminStudentsPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <StudentsContent />
        </RoleGate>
    );
}

function StudentsContent() {
    const {
        users,
        isLoading,
        actionLoadingId,
        deactivateUser,
    } = useSchoolUsers();

    const [query, setQuery] = useState("");

    const students = useMemo(() => {
        const search = query.trim().toLowerCase();

        return users.filter((user) => {
            const roles = user.roles?.length ? user.roles : user.role ? [user.role] : [];
            const isStudent = roles.includes(UserRole.STUDENT);

            const fullName =
                user.full_name ||
                `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim();

            const matchesSearch =
                !search ||
                fullName.toLowerCase().includes(search) ||
                user.email?.toLowerCase().includes(search);

            return isStudent && matchesSearch;
        });
    }, [users, query]);

    async function handleDeactivate(user: User) {
        await deactivateUser(user.id);
    }

    return (
        <div className="p-6 sm:p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                        Students
                    </h1>
                    <p className="mt-2 text-base text-slate-600 sm:text-lg">
                        Manage student records, enrolment status, and class placement.
                    </p>
                </div>

                <Link
                    href="/school-admin/users/create"
                    className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
                >
                    Add student
                </Link>
            </div>

            <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
                <input
                    type="text"
                    placeholder="Search by name or email"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />

                <div className="mt-5 text-sm text-slate-600">
                    <span className="rounded-full bg-slate-100 px-3 py-1.5 font-medium text-slate-700">
                        {students.length} student{students.length === 1 ? "" : "s"}
                    </span>
                </div>
            </div>

            <div className="mt-6">
                {isLoading ? (
                    <p className="text-sm text-slate-600">Loading students...</p>
                ) : (
                    <SchoolUserTable
                        users={students}
                        actionLoadingId={actionLoadingId}
                        onDeactivate={handleDeactivate}
                    />
                )}
            </div>
        </div>
    );
}