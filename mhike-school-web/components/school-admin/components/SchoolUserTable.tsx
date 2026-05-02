"use client";

import Link from "next/link";
import type { User } from "@/types/user";
import UserStatusBadge from "./UserStatusBadge";

type SchoolUserTableProps = {
    users: User[];
    actionLoadingId?: number | null;
    onDeactivate?: (user: User) => void | Promise<void>;
    onRequestErasure?: (user: User) => void | Promise<void>;
};

function getDisplayName(user: User) {
    return (
        user.full_name ||
        `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim() ||
        user.email ||
        "Unnamed user"
    );
}

function formatRole(role: string) {
    return role.replaceAll("_", " ").toLowerCase();
}

export default function SchoolUserTable({
    users,
    actionLoadingId,
    onDeactivate,
    onRequestErasure,
}: SchoolUserTableProps) {
    if (!users.length) {
        return (
            <div className="rounded-2xl border border-slate-200 bg-white p-7 text-base font-semibold text-slate-700">
                No users found.
            </div>
        );
    }

    return (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                User
                            </th>
                            <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                Roles
                            </th>
                            <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                Status
                            </th>
                            <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                Actions
                            </th>
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-200">
                        {users.map((user) => {
                            const roles = user.roles?.length
                                ? user.roles
                                : user.role
                                    ? [user.role]
                                    : [];

                            const isActive =
                                typeof user.is_active === "boolean"
                                    ? user.is_active
                                    : user.status === "active";

                            return (
                                <tr key={user.id} className="hover:bg-slate-50/80">
                                    <td className="px-6 py-5">
                                        <div className="font-semibold text-slate-900">
                                            {getDisplayName(user)}
                                        </div>
                                        <div className="mt-1 text-sm text-slate-500">
                                            {user.email}
                                        </div>
                                        {user.school_name && (
                                            <div className="mt-1 text-xs text-slate-400">
                                                {user.school_name}
                                            </div>
                                        )}
                                    </td>

                                    <td className="px-6 py-5">
                                        <div className="flex flex-wrap gap-2">
                                            {roles.map((role) => (
                                                <span
                                                    key={role}
                                                    className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold capitalize text-blue-800"
                                                >
                                                    {formatRole(role)}
                                                </span>
                                            ))}
                                        </div>
                                    </td>

                                    <td className="px-6 py-5">
                                        <UserStatusBadge user={user} />
                                    </td>

                                    <td className="px-6 py-5 text-right">
                                        <div className="flex justify-end gap-2">
                                            <Link
                                                href={`/school-admin/users/${user.id}`}
                                                className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                                            >
                                                View
                                            </Link>

                                            {onDeactivate && isActive && (
                                                <button
                                                    type="button"
                                                    onClick={() => onDeactivate(user)}
                                                    disabled={actionLoadingId === user.id}
                                                    className="rounded-lg bg-red-500 px-3 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
                                                >
                                                    {actionLoadingId === user.id
                                                        ? "Processing..."
                                                        : "Deactivate"}
                                                </button>
                                            )}

                                            {onRequestErasure && (
                                                <button
                                                    type="button"
                                                    onClick={() => onRequestErasure(user)}
                                                    disabled={actionLoadingId === user.id}
                                                    className="rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                                                >
                                                    Erasure
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}