"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

function formatAttemptReference(
    value: string | string[] | undefined,
): string {
    if (Array.isArray(value)) {
        return value[0] || "Unavailable";
    }

    return value || "Unavailable";
}

export default function StudentQuizAttemptPage() {
    const params = useParams<{
        attemptId?: string | string[];
    }>();

    const attemptReference =
        formatAttemptReference(params.attemptId);

    return (
        <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
            <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-800 via-blue-700 to-sky-500 p-6 text-white shadow-[0_20px_45px_rgba(30,64,175,0.24)] sm:p-8">
                <div className="relative z-10">
                    <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-100">
                        Student portal · Quiz attempt
                    </p>

                    <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
                        Quiz Attempt
                    </h1>

                    <p className="mt-4 max-w-2xl text-base leading-7 text-blue-50 sm:text-lg">
                        Complete quiz questions, review your progress,
                        and submit your answers when the quiz service is
                        connected.
                    </p>
                </div>

                <div
                    aria-hidden="true"
                    className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-white/10 blur-3xl"
                />

                <div
                    aria-hidden="true"
                    className="absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-sky-300/20 blur-3xl"
                />
            </section>

            <section
                aria-labelledby="quiz-attempt-heading"
                className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            >
                <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                            Assessment
                        </p>

                        <h2
                            id="quiz-attempt-heading"
                            className="mt-2 text-2xl font-black text-slate-950"
                        >
                            Quiz attempt information
                        </h2>

                        <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
                            This page is prepared for integration with
                            the quiz-attempt service. Once connected, it
                            can display the quiz questions, saved
                            answers, progress, remaining time and
                            submission controls.
                        </p>

                        <div className="mt-6 grid gap-4 sm:grid-cols-2">
                            <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Attempt reference
                                </p>

                                <p className="mt-2 break-all text-lg font-black text-slate-950">
                                    {attemptReference}
                                </p>
                            </article>

                            <article className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
                                <p className="text-sm font-semibold text-amber-700">
                                    Attempt status
                                </p>

                                <p className="mt-2 text-lg font-black text-amber-950">
                                    Awaiting integration
                                </p>
                            </article>
                        </div>

                        <section className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
                            <h3 className="text-lg font-bold text-slate-950">
                                Planned quiz features
                            </h3>

                            <ul className="mt-4 grid gap-3 text-sm leading-6 text-slate-700 sm:grid-cols-2">
                                <li className="rounded-xl border border-slate-200 bg-white p-3">
                                    Quiz title and instructions
                                </li>

                                <li className="rounded-xl border border-slate-200 bg-white p-3">
                                    Question-by-question navigation
                                </li>

                                <li className="rounded-xl border border-slate-200 bg-white p-3">
                                    Automatic answer saving
                                </li>

                                <li className="rounded-xl border border-slate-200 bg-white p-3">
                                    Attempt progress tracking
                                </li>

                                <li className="rounded-xl border border-slate-200 bg-white p-3">
                                    Time remaining, where applicable
                                </li>

                                <li className="rounded-xl border border-slate-200 bg-white p-3">
                                    Final review and submission
                                </li>
                            </ul>
                        </section>
                    </div>

                    <aside className="w-full rounded-2xl border border-blue-200 bg-blue-50 p-5 lg:w-80">
                        <h3 className="text-lg font-bold text-blue-950">
                            Quiz controls
                        </h3>

                        <p className="mt-3 text-sm leading-6 text-blue-800">
                            Quiz controls will become available when
                            this page is connected to the attempt API.
                        </p>

                        <Link
                            href="/student"
                            data-custom-button="true"
                            className="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-blue-700 px-4 py-3 text-sm font-bold text-white transition hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        >
                            Return to Student Dashboard
                        </Link>
                    </aside>
                </div>
            </section>

            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
                <h2 className="text-base font-bold text-amber-950">
                    Ready for backend integration
                </h2>

                <p className="mt-2 text-sm leading-6 text-amber-800">
                    No quiz-attempt endpoint or quiz data model was
                    provided with the existing page. The interface
                    therefore avoids creating unsupported API calls or
                    simulated quiz results.
                </p>
            </section>
        </main>
    );
}