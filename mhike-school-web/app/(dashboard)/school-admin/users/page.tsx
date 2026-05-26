"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { apiGet } from "@/lib/api";

type SchoolUser = {
    id: number;
    full_name: string | null;
    email: string;
    role: string;
    school_id: number | null;
    is_active?: boolean;
};

export default function SchoolAdminUsersPage() {
    const [users, setUsers] = useState<SchoolUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    async function loadUsers() {
        try {
            setLoading(true);
            setError("");

            const data = await apiGet<SchoolUser[]>("/school-users/");
            setUsers(data);
        } catch (err) {
            console.error(err);
            setError("Failed to load school users.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        void loadUsers();
    }, []);

    return (
        <div className="space-y-8 p-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold">
                        School Users
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Manage teachers and students in your school.
                    </p>
                </div>

                <Link
                    href="/school-admin/users/create"
                    className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
                >
                    Create User
                </Link>
            </div>

            {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                </div>
            ) : null}

            <div className="overflow-hidden rounded-2xl border bg-white">
                <table className="min-w-full">
                    <thead className="border-b bg-slate-50">
                        <tr>
                            <th className="px-6 py-4 text-left text-sm font-bold">
                                Name
                            </th>
                            <th className="px-6 py-4 text-left text-sm font-bold">
                                Email
                            </th>
                            <th className="px-6 py-4 text-left text-sm font-bold">
                                Role
                            </th>
                            <th className="px-6 py-4 text-left text-sm font-bold">
                                Status
                            </th>
                        </tr>
                    </thead>

                    <tbody>
                        {loading ? (
                            <tr>
                                <td
                                    colSpan={4}
                                    className="px-6 py-10 text-center text-slate-500"
                                >
                                    Loading users...
                                </td>
                            </tr>
                        ) : users.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={4}
                                    className="px-6 py-10 text-center text-slate-500"
                                >
                                    No users found yet.
                                </td>
                            </tr>
                        ) : (
                            users.map((user) => (
                                <tr
                                    key={user.id}
                                    className="border-b last:border-b-0"
                                >
                                    <td className="px-6 py-4 font-medium">
                                        {user.full_name || "Unnamed user"}
                                    </td>

                                    <td className="px-6 py-4 text-slate-600">
                                        {user.email}
                                    </td>

                                    <td className="px-6 py-4 capitalize text-slate-600">
                                        {user.role.replace("_", " ")}
                                    </td>

                                    <td className="px-6 py-4">
                                        <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                                            {user.is_active === false
                                                ? "Inactive"
                                                : "Active"}
                                        </span>
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