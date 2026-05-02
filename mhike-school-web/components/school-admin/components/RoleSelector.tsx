"use client";

import { UserRole } from "@/types/user";

export type Role = UserRole;

const ALL_ROLES: Role[] = [
    UserRole.STUDENT,
    UserRole.TEACHER,
    UserRole.SCHOOL_ADMIN,
];

type RoleSelectorProps = {
    value: Role[];
    onChange: (roles: Role[]) => void;
};

function formatRole(role: Role) {
    return role.replaceAll("_", " ");
}

export default function RoleSelector({
    value,
    onChange,
}: RoleSelectorProps) {
    function toggleRole(role: Role) {
        if (value.includes(role)) {
            onChange(value.filter((r) => r !== role));
        } else {
            onChange([...value, role]);
        }
    }

    return (
        <div className="flex flex-wrap gap-2">
            {ALL_ROLES.map((role) => {
                const active = value.includes(role);

                return (
                    <button
                        key={role}
                        type="button"
                        onClick={() => toggleRole(role)}
                        className={`rounded-full border px-3 py-1 text-xs capitalize transition ${active
                            ? "bg-blue-600 text-white border-blue-600"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                            }`}
                    >
                        {formatRole(role)}
                    </button>
                );
            })}
        </div>
    );
}