"use client"

import { useEffect, useState } from "react"

import RoleGate from "@/components/auth/RoleGate"
import { UserRole, type User } from "@/types/user"
import {
    getSchoolUsers,
    deactivateUser,
} from "@/lib/services/school-admin"

/* =========================
   Page Wrapper (RBAC)
========================= */
export default function SchoolAdminUsersPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <SchoolAdminUsersContent />
        </RoleGate>
    )
}

/* =========================
   Page Content
========================= */
function SchoolAdminUsersContent() {
    const [users, setUsers] = useState<User[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [actionLoadingId, setActionLoadingId] = useState<number | null>(null)

    async function loadUsers() {
        try {
            const data = await getSchoolUsers()
            setUsers(data)
        } catch (err: any) {
            setError(err.message || "Failed to load users")
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        loadUsers()
    }, [])

    /* =========================
       Actions
    ========================= */
    async function handleDeactivate(userId: number) {
        if (!confirm("Are you sure you want to deactivate this user?")) return

        try {
            setActionLoadingId(userId)
            await deactivateUser(userId)
            await loadUsers() // refresh list
        } catch (err: any) {
            alert(err.message || "Failed to deactivate user")
        } finally {
            setActionLoadingId(null)
        }
    }

    return (
        <div className="p-6">
            {/* Header */}
            <h1 className="text-3xl font-extrabold">School Admin Users</h1>
            <p className="mt-2 text-slate-500">
                Manage students and teachers in your school.
            </p>

            {/* Loading */}
            {isLoading && <p className="mt-6">Loading users...</p>}

            {/* Error */}
            {error && <p className="mt-6 text-red-500">{error}</p>}

            {/* Users */}
            {!isLoading && !error && (
                <div className="mt-6 space-y-3">
                    {users.length === 0 ? (
                        <p>No users found.</p>
                    ) : (
                        users.map((user) => (
                            <div
                                key={user.id}
                                className="rounded-xl border border-slate-200 p-4 shadow-sm"
                            >
                                <div className="flex items-center justify-between">
                                    {/* Left */}
                                    <div>
                                        <div className="font-semibold">
                                            {user.full_name || "No Name"}
                                        </div>

                                        <div className="text-sm text-slate-500">
                                            {user.email}
                                        </div>

                                        <div className="mt-1 text-xs">
                                            Role:{" "}
                                            <span className="font-medium">{user.role}</span> | Status:{" "}
                                            <span className="font-medium">{user.status}</span>
                                        </div>
                                    </div>

                                    {/* Right (Actions) */}
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
                        ))
                    )}
                </div>
            )}
        </div>
    )
}