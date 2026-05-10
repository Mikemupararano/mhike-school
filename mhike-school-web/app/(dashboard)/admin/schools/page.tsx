"use client";

import { useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";

type School = {
    id: number;
    name: string;
    created_at: string;
};

export default function AdminSchoolsPage() {
    const [schools, setSchools] = useState<School[]>([]);
    const [name, setName] = useState("");

    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    async function loadSchools() {
        try {
            setLoading(true);
            setError("");

            const data = await apiGet<School[]>("/admin/schools");

            setSchools(data);
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to load schools");
            }
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadSchools();
    }, []);

    async function handleCreate(
        e: React.FormEvent<HTMLFormElement>,
    ) {
        e.preventDefault();

        setError("");
        setSuccess("");

        if (!name.trim()) {
            setError("School name is required");
            return;
        }

        try {
            setSaving(true);

            const created = await apiPost<School>(
                "/admin/schools",
                {
                    name: name.trim(),
                },
            );

            setSchools((prev) => [...prev, created]);

            setName("");

            setSuccess("School created successfully");
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to create school");
            }
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="p-8 space-y-8">
            <div>
                <h1 className="text-3xl font-extrabold">
                    Schools
                </h1>

                <p className="mt-2 text-slate-500">
                    Create and manage schools.
                </p>
            </div>

            <form
                onSubmit={handleCreate}
                className="max-w-xl space-y-4 rounded-2xl border bg-white p-6"
            >
                <div>
                    <label className="mb-2 block text-sm font-semibold">
                        School Name
                    </label>

                    <input
                        type="text"
                        value={name}
                        onChange={(e) =>
                            setName(e.target.value)
                        }
                        placeholder="Enter school name"
                        className="w-full rounded-xl border px-4 py-3 outline-none focus:border-blue-500"
                    />
                </div>

                {error && (
                    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-green-700">
                        {success}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={saving}
                    className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {saving
                        ? "Creating..."
                        : "Create School"}
                </button>
            </form>

            <div className="rounded-2xl border bg-white p-6">
                <h2 className="mb-4 text-xl font-bold">
                    Existing Schools
                </h2>

                {loading ? (
                    <p className="text-slate-500">
                        Loading schools...
                    </p>
                ) : schools.length === 0 ? (
                    <p className="text-slate-500">
                        No schools found.
                    </p>
                ) : (
                    <div className="space-y-3">
                        {schools.map((school) => (
                            <div
                                key={school.id}
                                className="rounded-xl border p-4"
                            >
                                <div className="font-semibold">
                                    {school.name}
                                </div>

                                <div className="text-sm text-slate-500">
                                    ID: {school.id}
                                </div>

                                <div className="text-sm text-slate-400">
                                    Created:{" "}
                                    {new Date(
                                        school.created_at,
                                    ).toLocaleString()}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}