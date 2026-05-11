"use client";

import Link from "next/link";
import { useMemo } from "react";

import RoleGate from "@/components/auth/RoleGate";
import SchoolUserTable from "@/components/school-admin/components/SchoolUserTable";
import { useSchoolUsers } from "@/hooks/useSchoolUsers";
import { UserRole, type User } from "@/types/user";

export default function SchoolAdminTeachersPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <TeachersContent />
        </RoleGate>
    );
}

function TeachersContent() {
    const {
        users,
        isLoading,
        actionLoadingId,
        deactivateUser,
    } = useSchoolUsers();

    const teachers = useMemo(() => {
        return users.filter((user) => {
            const roles = user.roles?.length
                ? user.roles
                : user.role
                    ? [user.role]
                    : [];

            return roles.includes(UserRole.TEACHER);
        });
    }, [users]);

    async function handleDeactivate(user: User) {
        await deactivateUser(user.id);
    }

    return (
        <div className="p-8 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold">Teachers</h1>
                    <p className="mt-2 text-slate-500">
                        Manage teachers in your school.
                    </p>
                </div>

                <Link
                    href="/school-admin/users/create"
                    className="rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700"
                >
                    Create Teacher
                </Link>
            </div>

            {isLoading ? (
                <p className="text-slate-500">Loading teachers...</p>
            ) : teachers.length === 0 ? (
                <div className="rounded-2xl border bg-white p-8 text-center">
                    <h2 className="text-lg font-bold text-slate-900">
                        No teachers yet
                    </h2>
                    <p className="mt-2 text-slate-500">
                        Create a teacher account to assign them to classes.
                    </p>
                </div>
            ) : (
                <SchoolUserTable
                    users={teachers}
                    actionLoadingId={actionLoadingId}
                    onDeactivate={handleDeactivate}
                />
            )}
        </div>
    );
}