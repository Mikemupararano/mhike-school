"use client";

import { User } from "@/types/user";
import UserStatusBadge from "./UserStatusBadge";

type SchoolUserTableProps = {
    users: User[];
    onEdit?: (user: User) => void;
    onDeactivate?: (user: User) => void;
    onRequestErasure?: (user: User) => void;
};

export default function SchoolUserTable({
    users,
    onEdit,
    onDeactivate,
    onRequestErasure,
}: SchoolUserTableProps) {
    if (!users.length) {
        return (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-gray-500">
                No users found.
            </div>
        );
    }

    return (
        <div className="overflow-hidden rounded-lg border bg-white">
            <table className="w-full text-left text-sm">
                <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                        <th className="px-4 py-3">Name</th>
                        <th className="px-4 py-3">Email</th>
                        <th className="px-4 py-3">Roles</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                </thead>

                <tbody className="divide-y">
                    {users.map((user) => (
                        <tr key={user.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium text-gray-900">
                                {user.first_name} {user.last_name}
                            </td>

                            <td className="px-4 py-3 text-gray-600">{user.email}</td>

                            <td className="px-4 py-3">
                                <div className="flex flex-wrap gap-1">
                                    {(user.roles || [user.role]).filter(Boolean).map((role) => (
                                        <span
                                            key={role}
                                            className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700"
                                        >
                                            {role}
                                        </span>
                                    ))}
                                </div>
                            </td>

                            <td className="px-4 py-3">
                                <UserStatusBadge user={user} />
                            </td>

                            <td className="px-4 py-3">
                                <div className="flex justify-end gap-2">
                                    {onEdit && (
                                        <button
                                            type="button"
                                            onClick={() => onEdit(user)}
                                            className="rounded-md border px-3 py-1 text-xs hover:bg-gray-50"
                                        >
                                            Edit
                                        </button>
                                    )}

                                    {onDeactivate && user.is_active && (
                                        <button
                                            type="button"
                                            onClick={() => onDeactivate(user)}
                                            className="rounded-md border border-amber-300 px-3 py-1 text-xs text-amber-700 hover:bg-amber-50"
                                        >
                                            Deactivate
                                        </button>
                                    )}

                                    {onRequestErasure && (
                                        <button
                                            type="button"
                                            onClick={() => onRequestErasure(user)}
                                            className="rounded-md border border-red-300 px-3 py-1 text-xs text-red-700 hover:bg-red-50"
                                        >
                                            Erasure
                                        </button>
                                    )}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}