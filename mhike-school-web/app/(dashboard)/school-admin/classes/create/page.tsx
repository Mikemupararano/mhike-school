"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";
import { useClasses } from "@/hooks/useClasses";

export default function CreateClassPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <CreateClassContent />
        </RoleGate>
    );
}

function CreateClassContent() {
    const router = useRouter();
    const { createNewClass } = useClasses();

    const [name, setName] = useState("");
    const [teacherId, setTeacherId] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState("");

    const canSubmit = name.trim().length > 1 && !isSubmitting;

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");

        try {
            setIsSubmitting(true);

            await createNewClass(
                name.trim(),
                teacherId ? Number(teacherId) : null,
            );

            router.push("/school-admin/classes");
            router.refresh();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create class.");
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="max-w-xl p-6">
            <h1 className="text-3xl font-extrabold">Create Class</h1>
            <p className="mt-2 text-slate-500">Add a new class to your school.</p>

            <form
                onSubmit={handleSubmit}
                className="mt-6 space-y-5 rounded-2xl border bg-white p-6"
            >
                {error && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
                        {error}
                    </div>
                )}

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Class name
                    </label>
                    <input
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Year 10 Chemistry"
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Teacher ID optional
                    </label>
                    <input
                        type="number"
                        value={teacherId}
                        onChange={(event) => setTeacherId(event.target.value)}
                        placeholder="Leave blank if not assigned yet"
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                    />
                </div>

                <div className="flex gap-3">
                    <button
                        type="submit"
                        disabled={!canSubmit}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isSubmitting ? "Creating..." : "Create class"}
                    </button>

                    <button
                        type="button"
                        onClick={() => router.push("/school-admin/classes")}
                        className="rounded-lg border px-4 py-2 text-sm font-semibold"
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}