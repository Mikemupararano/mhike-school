"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole, UserStatus, type User } from "@/types/user";
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
    const [search, setSearch] = useState("");

    async function loadUsers() {
        try {
            setError(null);
            setIsLoading(true);
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

    const filteredUsers = useMemo(() => {
        const query = search.trim().toLowerCase();

        if (!query) return users;

        return users.filter((user) => {
            return (
                user.full_name?.toLowerCase().includes(query) ||
                user.email.toLowerCase().includes(query) ||
                user.roles.some((role) => role.toLowerCase().includes(query)) ||
                user.status.toLowerCase().includes(query)
            );
        });
    }, [users, search]);

    async function handleDeactivate(user: User) {
        const confirmed = confirm(
            `Are you sure you want to deactivate ${user.full_name || user.email}?`,
        );

        if (!confirmed) return;

        try {
            setActionLoadingId(user.id);
            await deactivateUser(user.id);
            await loadUsers();
        } catch (err) {
            alert(err instanceof Error ? err.message : "Failed to deactivate user");
        } finally {
            setActionLoadingId(null);
        }
    }

    return (
        <div className="p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold">School Users</h1>
                    <p className="mt-2 text-slate-500">
                        Manage school admins, teachers, and students.
                    </p>
                </div>

                <Link
                    href="/school-admin/users/create"
                    className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                >
                    Create user
                </Link>
            </div>

            <div className="mt-6">
                <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search by name, email, role, or status..."
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-slate-400"
                />
            </div>

            {isLoading && <p className="mt-6">Loading users...</p>}

            {error && (
                <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                    {error}
                </div>
            )}

            {!isLoading && !error && (
                <div className="mt-6 space-y-3">
                    {filteredUsers.length === 0 ? (
                        <div className="rounded-xl border border-slate-200 p-6 text-slate-500">
                            No users found.
                        </div>
                    ) : (
                        filteredUsers.map((user) => (
                            <UserCard
                                key={user.id}
                                user={user}
                                isActionLoading={actionLoadingId === user.id}
                                onDeactivate={handleDeactivate}
                            />
                        ))
                    )}
                </div>
            )}
        </div>
    );
}

function UserCard({
    user,
    isActionLoading,
    onDeactivate,
}: {
    user: User;
    isActionLoading: boolean;
    onDeactivate: (user: User) => void;
}) {
    const roles = user.roles?.length ? user.roles : user.role ? [user.role] : [];

    return (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <div className="font-semibold">{user.full_name || "No name"}</div>
                    <div className="text-sm text-slate-500">{user.email}</div>
                    <div className="text-sm text-slate-500">
                        {user.school_name || "School not assigned"}
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                        {roles.map((role) => (
                            <span
                                key={role}
                                className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700"
                            >
                                {role.replace("_", " ")}
                            </span>
                        ))}

                        <span
                            className={`rounded-full px-3 py-1 text-xs font-semibold ${user.status === UserStatus.ACTIVE
                                ? "bg-green-100 text-green-700"
                                : "bg-slate-100 text-slate-700"
                                }`}
                        >
                            {user.status.replace("_", " ")}
                        </span>
                    </div>
                </div>

                <div className="flex gap-2">
                    <Link
                        href={`/school-admin/users/${user.id}`}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold hover:bg-slate-50"
                    >
                        View
                    </Link>

                    {user.status === UserStatus.ACTIVE && (
                        <button
                            onClick={() => onDeactivate(user)}
                            disabled={isActionLoading}
                            className="rounded-lg bg-red-500 px-3 py-2 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-50"
                        >
                            {isActionLoading ? "Processing..." : "Deactivate"}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}