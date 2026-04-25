"use client";

import { useEffect, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole, type User } from "@/types/user";
import { getSchoolUsers, deactivateUser } from "@/lib/services/school-admin";

export default function SchoolAdminUsersPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <SchoolAdminUsersContent />
        </RoleGate>
    );
}

function SchoolAdminUsersContent() {
    const [users, setUsers] = useState<User[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

    async function loadUsers() {
        try {
            setError(null);
            const data = await getSchoolUsers();
            setUsers(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load users");
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadUsers();
    }, []);

    async function handleDeactivate(userId: number) {
        if (!confirm("Are you sure you want to deactivate this user?")) return;

        try {
            setActionLoadingId(userId);
            await deactivateUser(userId);
            await loadUsers();
        } catch (err) {
            alert(err instanceof Error ? err.message : "Failed to deactivate user");
        } finally {
            setActionLoadingId(null);
        }
    }

    return (
        <div className="p-6">
            <h1 className="text-3xl font-extrabold">School Admin Users</h1>
            <p className="mt-2 text-slate-500">
                Manage students and teachers in your school.
            </p>

            {isLoading && <p className="mt-6">Loading users...</p>}

            {error && <p className="mt-6 text-red-500">{error}</p>}

            {!isLoading && !error && (
                <div className="mt-6 space-y-3">
                    {users.length === 0 ? (
                        <p>No users found.</p>
                    ) : (
                        users.map((user) => {
                            const roles =
                                Array.isArray(user.roles) && user.roles.length > 0
                                    ? user.roles.join(", ")
                                    : user.role;

                            return (
                                <div
                                    key={user.id}
                                    className="rounded-xl border border-slate-200 p-4 shadow-sm"
                                >
                                    <div className="flex items-center justify-between">
                                        {/* LEFT */}
                                        <div>
                                            <div className="font-semibold">
                                                {user.full_name || "No Name"}
                                            </div>

                                            {/* ✅ SCHOOL NAME (NOT EMAIL) */}
                                            <div className="text-sm text-slate-500">
                                                {user.school_name || "School not assigned"}
                                            </div>

                                            <div className="mt-1 text-xs">
                                                Roles:{" "}
                                                <span className="font-medium">{roles}</span> | Status:{" "}
                                                <span className="font-medium">{user.status}</span>
                                            </div>
                                        </div>

                                        {/* RIGHT */}
                                        <div className="flex gap-2">
                                            {user.status === "active" && (
                                                <button
                                                    onClick={() => handleDeactivate(user.id)}
                                                    disabled={actionLoadingId === user.id}
                                                    className="rounded-lg bg-red-500 px-3 py-1 text-sm text-white hover:bg-red-600 disabled:opacity-50"
                                                >
                                                    {actionLoadingId === user.id
                                                        ? "Processing..."
                                                        : "Deactivate"}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            )}
        </div>
    );
}