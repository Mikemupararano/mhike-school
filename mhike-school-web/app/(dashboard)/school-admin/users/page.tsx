"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole, UserStatus, type User } from "@/types/user";
import { useSchoolUsers } from "@/hooks/useSchoolUsers";

export default function SchoolAdminUsersPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <SchoolAdminUsersContent />
        </RoleGate>
    );
}

function SchoolAdminUsersContent() {
    const {
        users,
        isLoading,
        error,
        actionLoadingId,
        deactivateUser,
    } = useSchoolUsers();

    const [search, setSearch] = useState("");

    const filteredUsers = useMemo(() => {
        const query = search.trim().toLowerCase();
        if (!query) return users;

        return users.filter((user) => {
            const roles = user.roles?.length ? user.roles : user.role ? [user.role] : [];
            const fullName = getDisplayName(user);

            return (
                fullName.toLowerCase().includes(query) ||
                user.email?.toLowerCase().includes(query) ||
                user.school_name?.toLowerCase().includes(query) ||
                roles.some((role) => role.toLowerCase().includes(query)) ||
                user.status?.toLowerCase().includes(query)
            );
        });
    }, [users, search]);

    async function handleDeactivate(user: User) {
        const confirmed = confirm(
            `Are you sure you want to deactivate ${getDisplayName(user)}?`,
        );

        if (!confirmed) return;

        try {
            await deactivateUser(user.id);
        } catch (err) {
            alert(err instanceof Error ? err.message : "Failed to deactivate user");
        }
    }

    return (
        <div className="p-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight text-slate-950">
                        School Users
                    </h1>
                    <p className="mt-2 text-base font-medium text-slate-700">
                        Manage school admins, teachers, and students.
                    </p>
                </div>

                <Link
                    href="/school-admin/users/create"
                    className="rounded-xl bg-slate-950 px-5 py-3 text-base font-bold text-white hover:bg-slate-800"
                >
                    Create user
                </Link>
            </div>

            <div className="mt-7">
                <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search by name, email, school, role, or status..."
                    className="w-full rounded-2xl border border-slate-300 bg-white px-5 py-4 text-base font-medium text-slate-900 outline-none placeholder:text-slate-500 focus:border-slate-500"
                />
            </div>

            {isLoading && (
                <p className="mt-7 text-base font-semibold text-slate-700">
                    Loading users...
                </p>
            )}

            {error && (
                <div className="mt-7 rounded-2xl border border-red-200 bg-red-50 p-5 text-base font-semibold text-red-700">
                    {error}
                </div>
            )}

            {!isLoading && !error && (
                <div className="mt-7 space-y-4">
                    {filteredUsers.length === 0 ? (
                        <div className="rounded-2xl border border-slate-200 bg-white p-7 text-base font-semibold text-slate-700">
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

function getInitials(name?: string | null) {
    if (!name?.trim()) return "U";

    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0][0].toUpperCase();

    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function formatRole(role: string) {
    return role.replaceAll("_", " ").toLowerCase();
}

function isUserActive(user: User) {
    if (typeof user.is_active === "boolean") return user.is_active;
    return user.status === UserStatus.ACTIVE;
}

function getDisplayName(user: User) {
    return (
        user.full_name ||
        `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim() ||
        user.email ||
        "Unnamed user"
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
    const displayName = getDisplayName(user);
    const active = isUserActive(user);
    const statusLabel = user.status
        ? user.status.replaceAll("_", " ")
        : active
            ? "active"
            : "inactive";

    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-5">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-400 text-xl font-black tracking-wide text-white shadow-md">
                        {getInitials(displayName)}
                    </div>

                    <div>
                        <div className="text-xl font-extrabold text-slate-950">
                            {displayName}
                        </div>

                        <div className="mt-1 text-base font-semibold text-slate-700">
                            {user.email || "No email"}
                        </div>

                        <div className="mt-1 text-sm font-medium text-slate-500">
                            {user.school_name || "School not assigned"}
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2">
                            {roles.map((role) => (
                                <span
                                    key={role}
                                    className="rounded-full bg-blue-50 px-3 py-1.5 text-sm font-bold capitalize text-blue-800"
                                >
                                    {formatRole(role)}
                                </span>
                            ))}

                            <span
                                className={`rounded-full px-3 py-1.5 text-sm font-bold capitalize ${active
                                    ? "bg-green-100 text-green-800"
                                    : "bg-slate-200 text-slate-800"
                                    }`}
                            >
                                {statusLabel}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex gap-3">
                    <Link
                        href={`/school-admin/users/${user.id}`}
                        className="rounded-xl border border-slate-300 px-4 py-2.5 text-base font-bold text-slate-900 hover:bg-slate-50"
                    >
                        View
                    </Link>

                    {active && (
                        <button
                            type="button"
                            onClick={() => onDeactivate(user)}
                            disabled={isActionLoading}
                            className="rounded-xl bg-red-500 px-4 py-2.5 text-base font-bold text-white hover:bg-red-600 disabled:opacity-50"
                        >
                            {isActionLoading ? "Processing..." : "Deactivate"}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}