"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getCurrentUser, type CurrentUser } from "@/lib/authApi";

type DashboardState =
    | { status: "loading"; user: null; error: null }
    | { status: "ready"; user: CurrentUser; error: null }
    | { status: "error"; user: null; error: string };

type QuickAction = {
    title: string;
    description: string;
    href: string;
    label: string;
};

const QUICK_ACTIONS: QuickAction[] = [
    {
        title: "Assignments",
        description:
            "View your current assignments, deadlines and submission details.",
        href: "/student/student/assignments",
        label: "View assignments",
    },
    {
        title: "Timetable",
        description:
            "Check your lesson order and weekly school timetable.",
        href: "/student/timetable",
        label: "View timetable",
    },
    {
        title: "Quiz attempts",
        description:
            "Continue available quiz attempts and review your progress.",
        href: "/student/student/quizzes/attempts",
        label: "View quiz attempts",
    },
];

function getFirstName(fullName: string | null): string {
    const trimmedName = fullName?.trim();

    if (!trimmedName) {
        return "Student";
    }

    return trimmedName.split(/\s+/)[0] ?? "Student";
}

function formatToday(): string {
    return new Intl.DateTimeFormat("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
    }).format(new Date());
}

function formatAcademicYear(): string {
    const today = new Date();
    const year = today.getFullYear();
    const startYear = today.getMonth() >= 8 ? year : year - 1;

    return `${startYear}/${String(startYear + 1).slice(-2)}`;
}

function ArrowIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-5 w-5"
            stroke="currentColor"
            strokeWidth="2"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 12h14M13 6l6 6-6 6"
            />
        </svg>
    );
}

function LoadingState() {
    return (
        <div
            aria-label="Loading student dashboard"
            className="space-y-6"
        >
            <div className="h-64 animate-pulse rounded-3xl bg-slate-200" />

            <div className="grid gap-4 lg:grid-cols-3">
                {Array.from({ length: 3 }).map((_, index) => (
                    <div
                        key={index}
                        className="h-56 animate-pulse rounded-2xl bg-slate-200"
                    />
                ))}
            </div>

            <div className="h-52 animate-pulse rounded-2xl bg-slate-200" />
        </div>
    );
}

export default function StudentPage() {
    const [state, setState] = useState<DashboardState>({
        status: "loading",
        user: null,
        error: null,
    });

    async function loadCurrentUser(): Promise<void> {
        setState({
            status: "loading",
            user: null,
            error: null,
        });

        try {
            const user = await getCurrentUser();

            setState({
                status: "ready",
                user,
                error: null,
            });
        } catch (error) {
            setState({
                status: "error",
                user: null,
                error:
                    error instanceof Error
                        ? error.message
                        : "Unable to load your dashboard.",
            });
        }
    }

    useEffect(() => {
        void loadCurrentUser();
    }, []);

    const today = useMemo(() => formatToday(), []);
    const academicYear = useMemo(
        () => formatAcademicYear(),
        [],
    );

    if (state.status === "loading") {
        return (
            <main className="p-4 sm:p-6 lg:p-8">
                <LoadingState />
            </main>
        );
    }

    if (state.status === "error") {
        return (
            <main className="p-4 sm:p-6 lg:p-8">
                <section
                    role="alert"
                    className="mx-auto max-w-3xl rounded-3xl border border-red-200 bg-red-50 p-6 text-center shadow-sm sm:p-8"
                >
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-red-700">
                        Dashboard unavailable
                    </p>

                    <h1 className="mt-2 text-2xl font-extrabold text-slate-950">
                        We could not load your student account
                    </h1>

                    <p className="mt-3 text-base leading-7 text-slate-700">
                        {state.error}
                    </p>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() => {
                            void loadCurrentUser();
                        }}
                        className="mt-6 inline-flex items-center justify-center rounded-xl bg-slate-950 px-5 py-2.5 text-base font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                    >
                        Try again
                    </button>
                </section>
            </main>
        );
    }

    const firstName = getFirstName(state.user.full_name);

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <section className="overflow-hidden rounded-3xl bg-slate-950 text-white shadow-xl">
                <div className="relative p-6 sm:p-8 lg:p-10">
                    <div
                        aria-hidden="true"
                        className="absolute -right-16 -top-20 h-56 w-56 rounded-full bg-blue-500/20 blur-3xl"
                    />

                    <div className="relative flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
                        <div className="max-w-3xl">
                            <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-300">
                                Student dashboard
                            </p>

                            <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
                                Welcome back, {firstName}
                            </h1>

                            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
                                Access your assignments, lesson timetable and
                                quiz attempts from one place.
                            </p>
                        </div>

                        <dl className="grid shrink-0 gap-3 sm:grid-cols-2 lg:min-w-[21rem]">
                            <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur">
                                <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                                    Today
                                </dt>
                                <dd className="mt-1 text-sm font-semibold text-white">
                                    {today}
                                </dd>
                            </div>

                            <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur">
                                <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
                                    Academic year
                                </dt>
                                <dd className="mt-1 text-sm font-semibold text-white">
                                    {academicYear}
                                </dd>
                            </div>
                        </dl>
                    </div>
                </div>
            </section>

            <section aria-labelledby="student-quick-actions-heading">
                <div>
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                        Quick access
                    </p>

                    <h2
                        id="student-quick-actions-heading"
                        className="mt-1 text-2xl font-extrabold tracking-tight text-slate-950"
                    >
                        Your learning tools
                    </h2>

                    <p className="mt-2 text-sm leading-6 text-slate-500">
                        Choose an area below to continue with your schoolwork.
                    </p>
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-3">
                    {QUICK_ACTIONS.map((action, index) => (
                        <article
                            key={action.href}
                            className="group flex min-h-56 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md sm:p-6"
                        >
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-xl font-black text-blue-700">
                                {index + 1}
                            </div>

                            <h3 className="mt-5 text-xl font-bold text-slate-950">
                                {action.title}
                            </h3>

                            <p className="mt-2 flex-1 text-base leading-7 text-slate-600">
                                {action.description}
                            </p>

                            <Link
                                href={action.href}
                                data-custom-button="true"
                                className="mt-5 inline-flex w-fit items-center gap-2 rounded-xl text-base font-bold text-blue-700 transition hover:text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-4"
                            >
                                {action.label}
                                <ArrowIcon />
                            </Link>
                        </article>
                    ))}
                </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-indigo-700">
                        Getting started
                    </p>

                    <h2 className="mt-1 text-xl font-bold text-slate-950">
                        Plan your school day
                    </h2>

                    <div className="mt-5 grid gap-3">
                        {[
                            [
                                "Check your timetable",
                                "Review today's lesson order before the school day begins.",
                            ],
                            [
                                "Review your assignments",
                                "Open each assignment to check its instructions and submission requirements.",
                            ],
                            [
                                "Continue quiz attempts",
                                "Return to any available attempt and complete it before its deadline.",
                            ],
                        ].map(([title, description], index) => (
                            <div
                                key={title}
                                className="rounded-2xl bg-slate-50 p-4"
                            >
                                <p className="font-bold text-slate-900">
                                    {index + 1}. {title}
                                </p>
                                <p className="mt-1 text-sm leading-6 text-slate-600">
                                    {description}
                                </p>
                            </div>
                        ))}
                    </div>
                </article>

                <aside className="rounded-2xl border border-blue-100 bg-blue-50 p-5 shadow-sm sm:p-6">
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                        Your account
                    </p>

                    <h2 className="mt-1 text-xl font-bold text-slate-950">
                        Student details
                    </h2>

                    <dl className="mt-5 space-y-4">
                        <div>
                            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                Name
                            </dt>
                            <dd className="mt-1 break-words font-semibold text-slate-900">
                                {state.user.full_name ?? "Not provided"}
                            </dd>
                        </div>

                        <div>
                            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                School
                            </dt>
                            <dd className="mt-1 break-words font-semibold text-slate-900">
                                {state.user.school_name ?? "Not assigned"}
                            </dd>
                        </div>

                        <div>
                            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                Email
                            </dt>
                            <dd className="mt-1 break-all font-semibold text-slate-900">
                                {state.user.email}
                            </dd>
                        </div>
                    </dl>
                </aside>
            </section>
        </main>
    );
}
