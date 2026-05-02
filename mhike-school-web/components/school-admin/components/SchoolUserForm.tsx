"use client";

import { useState } from "react";
import RoleSelector, { type Role } from "./RoleSelector";
import { UserRole, type CreateUserInput, type User } from "@/types/user";

type SchoolUserFormProps = {
    initialUser?: User;
    onSubmit: (data: CreateUserInput) => Promise<void>;
    submitLabel?: string;
};

export default function SchoolUserForm({
    initialUser,
    onSubmit,
    submitLabel = "Create user",
}: SchoolUserFormProps) {
    const [firstName, setFirstName] = useState(initialUser?.first_name ?? "");
    const [lastName, setLastName] = useState(initialUser?.last_name ?? "");
    const [email, setEmail] = useState(initialUser?.email ?? "");

    const [roles, setRoles] = useState<Role[]>(
        initialUser?.roles?.length
            ? initialUser.roles
            : initialUser?.role
                ? [initialUser.role]
                : [UserRole.STUDENT],
    );

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState("");

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");

        if (!firstName.trim() || !lastName.trim() || !email.trim()) {
            setError("First name, last name, and email are required.");
            return;
        }

        if (!roles.length) {
            setError("Select at least one role.");
            return;
        }

        setIsSubmitting(true);

        try {
            await onSubmit({
                first_name: firstName.trim(),
                last_name: lastName.trim(),
                email: email.trim(),
                role: roles[0],
                roles,
            });

            if (!initialUser) {
                setFirstName("");
                setLastName("");
                setEmail("");
                setRoles([UserRole.STUDENT]);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to save user.");
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="space-y-5 rounded-lg border bg-white p-6"
        >
            {error && (
                <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
                <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                        First name
                    </label>
                    <input
                        value={firstName}
                        onChange={(event) => setFirstName(event.target.value)}
                        className="w-full rounded-md border px-3 py-2 text-sm"
                        placeholder="Jane"
                    />
                </div>

                <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                        Last name
                    </label>
                    <input
                        value={lastName}
                        onChange={(event) => setLastName(event.target.value)}
                        className="w-full rounded-md border px-3 py-2 text-sm"
                        placeholder="Smith"
                    />
                </div>
            </div>

            <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                    Email
                </label>
                <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-md border px-3 py-2 text-sm"
                    placeholder="jane.smith@school.com"
                />
            </div>

            <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                    Roles
                </label>
                <RoleSelector value={roles} onChange={setRoles} />
            </div>

            <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
                {isSubmitting ? "Saving..." : submitLabel}
            </button>
        </form>
    );
}