// Production-grade replacement for app/(dashboard)/school-admin/classes/page.tsx
"use client";

import Link from "next/link";
import { Building2, Calendar, Plus, Search, Users } from "lucide-react";
import { useMemo, useState } from "react";
import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";
import { useClasses } from "@/hooks/useClasses";

export default function SchoolAdminClassesPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <ClassesContent />
        </RoleGate>
    );
}

function ClassesContent() {
    const { classes, isLoading, error } = useClasses();
    const [query, setQuery] = useState("");

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return classes;
        return classes.filter(c =>
            c.name.toLowerCase().includes(q) ||
            String(c.teacher_id ?? "").includes(q)
        );
    }, [classes, query]);

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
                <header className="flex flex-col gap-4 sm:flex-row sm:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-700">School administration</p>
                        <h1 className="mt-2 text-4xl font-extrabold">Classes</h1>
                        <p className="mt-2 text-slate-600">Manage classes, assign teachers and enrol students.</p>
                    </div>
                    <Link href="/school-admin/classes/create"
                        className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 font-bold text-white hover:bg-blue-800">
                        <Plus className="h-4 w-4" />Add Class
                    </Link>
                </header>

                {isLoading ? (
                    <div className="mt-8 space-y-3">
                        {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-2xl bg-white border" />)}
                    </div>
                ) : error ? (
                    <div className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6 text-red-700">{error}</div>
                ) : (
                    <>
                        <div className="mt-8 grid gap-4 sm:grid-cols-3">
                            <Summary title="Classes" value={classes.length} icon={<Building2 className="h-6 w-6" />} />
                            <Summary title="Assigned" value={classes.filter(c => c.teacher_id).length} icon={<Users className="h-6 w-6" />} />
                            <Summary title="Unassigned" value={classes.filter(c => !c.teacher_id).length} icon={<Calendar className="h-6 w-6" />} />
                        </div>

                        <div className="mt-8 rounded-2xl border bg-white p-5">
                            <div className="relative max-w-md">
                                <Search className="absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
                                <input
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    placeholder="Search classes..."
                                    className="w-full rounded-xl border py-2.5 pl-10 pr-3" />
                            </div>

                            {filtered.length === 0 ? (
                                <div className="py-12 text-center">
                                    <Building2 className="mx-auto h-10 w-10 text-slate-400" />
                                    <h2 className="mt-4 text-lg font-bold">No classes found</h2>
                                    <p className="mt-2 text-slate-500">Create a class or adjust your search.</p>
                                </div>
                            ) : (
                                <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                                    {filtered.map(cls => (
                                        <Link key={cls.id}
                                            href={`/school-admin/classes/${cls.id}`}
                                            className="rounded-2xl border bg-white p-5 shadow-sm transition hover:shadow-md">
                                            <h3 className="text-lg font-bold">{cls.name}</h3>
                                            <p className="mt-2 text-sm text-slate-500">Teacher: {cls.teacher_id ?? "Not assigned"}</p>
                                            <p className="mt-1 text-sm text-slate-500">Created: {new Date(cls.created_at).toLocaleDateString()}</p>
                                            <p className="mt-4 text-sm font-semibold text-blue-700">View class →</p>
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>
        </main>
    );
}

function Summary({ title, value, icon }: { title: string; value: number; icon: React.ReactNode }) {
    return <div className="rounded-2xl border bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between">
            <div><p className="text-sm font-bold text-slate-500">{title}</p><p className="mt-3 text-3xl font-extrabold">{value}</p></div>
            <div className="rounded-xl bg-blue-50 p-3 text-blue-700">{icon}</div>
        </div>
    </div>
}
