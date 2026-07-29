"use client";

import Link from "next/link";

export default function StudentAssignmentDetailPage() {
    return (
        <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-800 via-blue-700 to-sky-500 p-6 text-white shadow-[0_20px_45px_rgba(30,64,175,0.24)] sm:p-8">
                <div className="relative z-10">
                    <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-100">
                        Student Portal
                    </p>

                    <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
                        Assignment Details
                    </h1>

                    <p className="mt-4 max-w-2xl text-base leading-7 text-blue-50">
                        View assignment instructions, submission status,
                        teacher feedback and attached resources.
                    </p>
                </div>

                <div
                    aria-hidden="true"
                    className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-white/10 blur-3xl"
                />
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex-1">
                        <p className="text-sm font-bold uppercase tracking-wide text-blue-700">
                            Assignment
                        </p>

                        <h2 className="mt-2 text-2xl font-black text-slate-950">
                            Assignment information
                        </h2>

                        <p className="mt-4 text-base leading-7 text-slate-600">
                            This page has been created and is ready for the
                            assignment detail API. Once connected it will
                            display:
                        </p>

                        <ul className="mt-5 list-disc space-y-2 pl-5 text-slate-700">
                            <li>Assignment title</li>
                            <li>Description and instructions</li>
                            <li>Due date</li>
                            <li>Maximum marks</li>
                            <li>Attached files</li>
                            <li>Your submission</li>
                            <li>Teacher feedback</li>
                            <li>Marks awarded</li>
                            <li>Submission history</li>
                        </ul>
                    </div>

                    <aside className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-5 lg:w-80">
                        <h3 className="text-lg font-bold text-slate-950">
                            Status
                        </h3>

                        <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-white p-4">
                            <p className="text-sm font-semibold text-slate-500">
                                Assignment Status
                            </p>

                            <p className="mt-2 text-lg font-bold text-slate-700">
                                Waiting for integration
                            </p>
                        </div>

                        <Link
                            href="/student/student/assignments"
                            className="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-blue-700 px-4 py-3 text-sm font-bold text-white transition hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                            data-custom-button="true"
                        >
                            Back to Assignments
                        </Link>
                    </aside>
                </div>
            </section>

            <section className="rounded-3xl border border-amber-200 bg-amber-50 p-6">
                <h3 className="text-lg font-bold text-amber-900">
                    Ready for backend integration
                </h3>

                <p className="mt-3 leading-7 text-amber-800">
                    No backend endpoint currently exists for retrieving a
                    single assignment. This page intentionally avoids
                    inventing API calls and is ready to be connected once the
                    endpoint is implemented.
                </p>
            </section>
        </main>
    );
}