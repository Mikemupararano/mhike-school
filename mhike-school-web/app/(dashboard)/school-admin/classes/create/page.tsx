"use client";

import {
    FormEvent,
    useEffect,
    useState,
} from "react";

import { useRouter } from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";

import { apiGet } from "@/lib/api";

import { useClasses } from "@/hooks/useClasses";

import { UserRole } from "@/types/user";

type Teacher = {
    id: number;
    full_name: string | null;
    email: string;
    role: string;
};

export default function CreateClassPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <CreateClassContent />
        </RoleGate>
    );
}

function CreateClassContent() {
    const router = useRouter();

    const { createNewClass } =
        useClasses();

    const [teachers, setTeachers] =
        useState<Teacher[]>([]);

    const [name, setName] =
        useState("");

    const [teacherId, setTeacherId] =
        useState("");

    const [loadingTeachers, setLoadingTeachers] =
        useState(false);

    const [isSubmitting, setIsSubmitting] =
        useState(false);

    const [error, setError] =
        useState("");

    useEffect(() => {
        async function loadTeachers() {
            try {
                setLoadingTeachers(true);

                const users =
                    await apiGet<Teacher[]>(
                        "/school-admin/users",
                    );

                const filtered =
                    users.filter(
                        (user) =>
                            user.role ===
                            "teacher",
                    );

                setTeachers(filtered);
            } catch (err) {
                console.error(err);

                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load teachers.",
                );
            } finally {
                setLoadingTeachers(false);
            }
        }

        loadTeachers();
    }, []);

    const canSubmit =
        name.trim().length > 1 &&
        !isSubmitting;

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        setError("");

        try {
            setIsSubmitting(true);

            await createNewClass(
                name.trim(),
                teacherId
                    ? Number(teacherId)
                    : null,
            );

            router.push(
                "/school-admin/classes",
            );

            router.refresh();
        } catch (err) {
            console.error(err);

            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to create class.",
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="max-w-2xl p-6">
            <h1 className="text-3xl font-extrabold">
                Create Class
            </h1>

            <p className="mt-2 text-slate-500">
                Add a new class to your
                school.
            </p>

            <form
                onSubmit={handleSubmit}
                className="mt-6 space-y-5 rounded-2xl border bg-white p-6"
            >
                {error ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
                        {error}
                    </div>
                ) : null}

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Class Name
                    </label>

                    <input
                        value={name}
                        onChange={(event) =>
                            setName(
                                event.target.value,
                            )
                        }
                        placeholder="Year 10 Chemistry"
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Assign Teacher
                    </label>

                    <select
                        value={teacherId}
                        onChange={(event) =>
                            setTeacherId(
                                event.target.value,
                            )
                        }
                        disabled={
                            loadingTeachers
                        }
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                    >
                        <option value="">
                            {loadingTeachers
                                ? "Loading teachers..."
                                : "No teacher assigned"}
                        </option>

                        {teachers.map(
                            (teacher) => (
                                <option
                                    key={
                                        teacher.id
                                    }
                                    value={
                                        teacher.id
                                    }
                                >
                                    {teacher.full_name ||
                                        teacher.email}
                                </option>
                            ),
                        )}
                    </select>
                </div>

                <div className="flex gap-3">
                    <button
                        type="submit"
                        disabled={
                            !canSubmit
                        }
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isSubmitting
                            ? "Creating..."
                            : "Create Class"}
                    </button>

                    <button
                        type="button"
                        onClick={() =>
                            router.push(
                                "/school-admin/classes",
                            )
                        }
                        className="rounded-lg border px-4 py-2 text-sm font-semibold"
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}