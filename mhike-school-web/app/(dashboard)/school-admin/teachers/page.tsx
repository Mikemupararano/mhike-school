"use client";

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
        <div className="p-8">
            <h1 className="text-3xl font-extrabold">Teachers</h1>
            <p className="mt-2 text-slate-500">
                Manage teachers in your school.
            </p>

            {isLoading ? (
                <p className="mt-6">Loading...</p>
            ) : (
                <div className="mt-6">
                    <SchoolUserTable
                        users={teachers}
                        actionLoadingId={actionLoadingId}
                        onDeactivate={handleDeactivate}
                    />
                </div>
            )}
        </div>
    );
}