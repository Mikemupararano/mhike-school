"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";

type UserItem = {
    id: number;
    full_name?: string | null;
    email: string;
    role: string;
    roles: string[];
    school_id?: number | null;
    school_name?: string | null;
    is_active: boolean;
    status: string;
};

type UsersResponse = {
    items: UserItem[];
    total: number;
    skip: number;
    limit: number;
};

export default function AdminUsersPage() {
    const [users, setUsers] = useState<UserItem[]>([]);
    const [loading, setLoading] = useState(true);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    async function loadUsers() {
        try {
            setLoading(true);

            const data = await apiGet<UsersResponse>(
                "/admin/users",
            );

            setUsers(data.items);
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to load users");
            }
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadUsers();
    }, []);

    async function toggleActive(user: UserItem) {
        setError("");
        setSuccess("");

        try {
            const updated = await apiPost<UserItem>(
                `/admin/users/${user.id}/active`,
                {
                    is_active: !user.is_active,
                },
            );

            setUsers((prev) =>
                prev.map((u) =>
                    u.id === updated.id ? updated : u,
                ),
            );

            setSuccess(
                updated.is_active
                    ? "User activated"
                    : "User deactivated",
            );
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to update user");
            }
        }
    }

    if (loading) {
        return (
            <div className="p-8">
                Loading users...
            </div>
        );
    }

    return (
        <div className="p-8 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold">
                        Platform Users
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Manage all users across schools.
                    </p>
                </div>

                <Link
                    href="/admin/users/create"
                    className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-3 rounded-xl font-semibold"
                >
                    Create User
                </Link>
            </div>

            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3">
                    {error}
                </div>
            )}

            {success && (
                <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl px-4 py-3">
                    {success}
                </div>
            )}

            <div className="bg-white border rounded-2xl overflow-hidden">
                <table className="w-full">
                    <thead className="bg-slate-50">
                        <tr className="text-left">
                            <th className="px-6 py-4 font-semibold">
                                Name
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                Email
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                Role
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                School
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                Status
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                Actions
                            </th>
                        </tr>
                    </thead>

                    <tbody>
                        {users.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={6}
                                    className="px-6 py-10 text-center text-slate-500"
                                >
                                    No users found.
                                </td>
                            </tr>
                        ) : (
                            users.map((user) => (
                                <tr
                                    key={user.id}
                                    className="border-t"
                                >
                                    <td className="px-6 py-4 font-medium">
                                        {user.full_name || "Unnamed User"}
                                    </td>

                                    <td className="px-6 py-4">
                                        {user.email}
                                    </td>

                                    <td className="px-6 py-4">
                                        <span className="bg-slate-100 px-3 py-1 rounded-full text-sm">
                                            {user.role}
                                        </span>
                                    </td>

                                    <td className="px-6 py-4">
                                        {user.school_name || "-"}
                                    </td>

                                    <td className="px-6 py-4">
                                        <span
                                            className={
                                                user.is_active
                                                    ? "text-green-600 font-semibold"
                                                    : "text-red-600 font-semibold"
                                            }
                                        >
                                            {user.is_active
                                                ? "Active"
                                                : "Inactive"}
                                        </span>
                                    </td>

                                    <td className="px-6 py-4">
                                        <div className="flex gap-3">
                                            <button
                                                onClick={() =>
                                                    toggleActive(user)
                                                }
                                                className={
                                                    user.is_active
                                                        ? "bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm"
                                                        : "bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm"
                                                }
                                            >
                                                {user.is_active
                                                    ? "Deactivate"
                                                    : "Activate"}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}