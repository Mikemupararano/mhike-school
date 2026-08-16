"use client";

import Link from "next/link";

import RoleGate from "@/components/auth/RoleGate";
import { useAssessments } from "@/hooks/useAssessments";
import {
    type Assessment,
    type AssessmentStatus,
} from "@/lib/services/assessments";
import { UserRole } from "@/types/user";


function formatDateTime(
    value: string | null,
): string {
    if (!value) {
        return "Not set";
    }

    return new Date(
        value,
    ).toLocaleString(
        "en-GB",
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        },
    );
}


function statusLabel(
    status: AssessmentStatus,
): string {
    if (status === "draft") {
        return "Draft";
    }

    if (status === "published") {
        return "Published";
    }

    if (status === "closed") {
        return "Closed";
    }

    return "Archived";
}


function assessmentSummary(
    assessment: Assessment,
): string {
    const parts = [
        assessment.assessment_type,
        assessment.academic_year,
        assessment.term,
    ].filter(
        (value): value is string =>
            Boolean(
                value,
            ),
    );

    return parts.length > 0
        ? parts.join(" • ")
        : `Course ${assessment.course_id}`;
}


export default function TeacherAssessmentsPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <AssessmentsContent />
        </RoleGate>
    );
}


function AssessmentsContent() {
    const {
        assessments,
        isLoading,
        error,
        refresh,
    } = useAssessments();


    return (
        <main className="space-y-6 p-6 sm:p-8">
            <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                        Assessments
                    </h1>

                    <p className="mt-2 max-w-3xl text-slate-500">
                        Create, schedule, publish, mark and manage formal
                        assessments for your courses.
                    </p>
                </div>

                <div className="flex flex-wrap gap-3">
                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={() =>
                            void refresh()
                        }
                        disabled={isLoading}
                        className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isLoading
                            ? "Refreshing..."
                            : "Refresh"}
                    </button>

                    <Link
                        href="/teacher/assessments/create"
                        className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
                    >
                        Create assessment
                    </Link>
                </div>
            </header>

            {isLoading && (
                <p className="text-sm text-slate-600">
                    Loading assessments...
                </p>
            )}

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                    {error}
                </div>
            )}

            {!isLoading && !error && (
                <section className="space-y-4">
                    {assessments.length === 0 ? (
                        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">
                            No assessments found.
                        </div>
                    ) : (
                        assessments.map(
                            (assessment) => (
                                <article
                                    key={assessment.id}
                                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                                >
                                    <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-3">
                                                <h2 className="text-xl font-bold text-slate-900">
                                                    {assessment.title}
                                                </h2>

                                                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
                                                    {statusLabel(
                                                        assessment.status,
                                                    )}
                                                </span>

                                                {assessment.anonymous_marking && (
                                                    <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
                                                        Anonymous marking
                                                    </span>
                                                )}
                                            </div>

                                            <p className="mt-2 text-sm text-slate-500">
                                                {assessmentSummary(
                                                    assessment,
                                                )}
                                            </p>

                                            {assessment.description && (
                                                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                                                    {assessment.description}
                                                </p>
                                            )}

                                            <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2 xl:grid-cols-4">
                                                <div>
                                                    <span className="font-semibold text-slate-800">
                                                        Course:
                                                    </span>{" "}
                                                    {assessment.course_id}
                                                </div>

                                                <div>
                                                    <span className="font-semibold text-slate-800">
                                                        Questions:
                                                    </span>{" "}
                                                    {assessment.questions.length}
                                                </div>

                                                <div>
                                                    <span className="font-semibold text-slate-800">
                                                        Scheduled:
                                                    </span>{" "}
                                                    {formatDateTime(
                                                        assessment.scheduled_at,
                                                    )}
                                                </div>

                                                <div>
                                                    <span className="font-semibold text-slate-800">
                                                        Closes:
                                                    </span>{" "}
                                                    {formatDateTime(
                                                        assessment.closes_at,
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        <Link
                                            href={`/teacher/assessments/${assessment.id}`}
                                            className="inline-flex shrink-0 items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
                                        >
                                            Manage assessment
                                        </Link>
                                    </div>
                                </article>
                            ),
                        )
                    )}
                </section>
            )}
        </main>
    );
}