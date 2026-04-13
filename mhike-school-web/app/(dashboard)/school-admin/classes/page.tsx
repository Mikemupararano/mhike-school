"use client";

import Link from "next/link";

export default function SchoolAdminClassesPage() {
    return (
        <div className="p-6 sm:p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                        Classes
                    </h1>
                    <p className="mt-2 text-base text-slate-600 sm:text-lg">
                        Manage classes, assign students, and organise year groups.
                    </p>
                </div>

                <Link
                    href="/school-admin/classes/new"
                    className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
                >
                    Add class
                </Link>
            </div>

            <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="text-center">
                    <h2 className="text-lg font-semibold text-slate-900">
                        No classes yet
                    </h2>
                    <p className="mt-2 text-sm text-slate-500">
                        Get started by creating your first class.
                    </p>
                </div>
            </div>
        </div>
    );
}