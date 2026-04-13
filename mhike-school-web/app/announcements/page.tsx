"use client";

import { useRouter } from "next/navigation";

export default function AnnouncementsPage() {
    const router = useRouter();

    return (
        <main className="mx-auto max-w-4xl p-6 sm:p-8">
            <button
                onClick={() => router.push("/dashboard")}
                className="mb-4 inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
                ← Back to Dashboard
            </button>

            <h1 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">
                Announcements
            </h1>

            <div className="mt-6 space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-lg font-bold text-slate-900">
                        Live Q&amp;A session tomorrow at 3 PM
                    </div>
                    <p className="mt-2 text-sm text-slate-500">
                        Don&apos;t miss it.
                    </p>
                </div>
            </div>
        </main>
    );
}