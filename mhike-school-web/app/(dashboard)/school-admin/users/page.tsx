"use client";

import Link from "next/link";

export default function SchoolAdminUsersPage() {
    return (
        <div className="p-8 space-y-8">
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

            <div className="rounded-2xl border bg-white">
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
                        <tr>
                            <td
                                colSpan={4}
                                className="px-6 py-10 text-center text-slate-500"
                            >
                                No users found yet.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
}