"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

import {
    getParentGrades,
    type ParentGrade,
} from "@/lib/services/parentGrades";

function formatDate(value: string | null): string {
    if (!value) {
        return "Not graded yet";
    }

    return new Date(value).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function calculatePercentage(
    score: number | null,
    maxScore: number,
): number | null {
    if (score === null || maxScore <= 0) {
        return null;
    }

    return Math.round((score / maxScore) * 100);
}

export default function ParentGradesPage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading: childrenLoading,
        error: childrenError,
    } = useParentChildren();

    const [grades, setGrades] = useState<ParentGrade[]>([]);
    const [gradesLoading, setGradesLoading] = useState(false);
    const [gradesError, setGradesError] = useState<string | null>(null);
    const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);

    const loadGrades = useCallback(async () => {
        try {
            setGradesLoading(true);
            setGradesError(null);

            const data = await getParentGrades();

            setGrades(data);
            setLastUpdatedAt(new Date());
        } catch (err) {
            setGradesError(
                err instanceof Error
                    ? err.message
                    : "Failed to load grades.",
            );
        } finally {
            setGradesLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadGrades();
    }, [loadGrades]);

    const selectedGrades = useMemo(() => {
        if (!selectedStudentId) {
            return [];
        }

        return grades.filter(
            (grade) => grade.student_id === selectedStudentId,
        );
    }, [grades, selectedStudentId]);

    const averagePercentage = useMemo(() => {
        const percentages = selectedGrades
            .map((grade) =>
                calculatePercentage(
                    grade.score,
                    grade.max_score,
                ),
            )
            .filter(
                (value): value is number =>
                    value !== null,
            );

        if (percentages.length === 0) {
            return null;
        }

        const total = percentages.reduce(
            (sum, value) => sum + value,
            0,
        );

        return Math.round(total / percentages.length);
    }, [selectedGrades]);

    const isLoading = childrenLoading || gradesLoading;
    const pageError = childrenError || gradesError;

    const selectedStudentName =
        selectedProfile?.student_name ??
        (selectedProfile
            ? `Student ${selectedProfile.student_id}`
            : "Selected student");

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Child Grades
                    </h1>

                    <p className="mt-2 max-w-3xl text-base text-slate-600">
                        Review assignment scores, teacher feedback and
                        assessment progress for your child.
                    </p>

                    {lastUpdatedAt && (
                        <p aria-live="polite" className="mt-2 text-sm text-slate-500">
                            Last refreshed{" "}
                            {lastUpdatedAt.toLocaleTimeString(
                                "en-GB",
                                {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                },
                            )}
                            .
                        </p>
                    )}
                </div>

                <button
                    type="button"
                    data-custom-button="true"
                    onClick={() => void loadGrades()}
                    disabled={gradesLoading}
                    className="inline-flex w-fit items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {gradesLoading
                        ? "Refreshing..."
                        : "Refresh"}
                </button>
            </header>

            <ParentPageState
                loading={isLoading}
                error={pageError}
                isEmpty={
                    profiles.length === 0 ||
                    !selectedProfile
                }
                loadingMessage="Loading grades..."
            >
                {selectedProfile && (
                    <>
                        <ChildSelector
                            profiles={profiles}
                            selectedStudentId={selectedStudentId}
                            onSelectStudent={setSelectedStudentId}
                            title="Linked Students"
                            description="Select a child to view their grades."
                        />

                        <section
                            aria-label="Grade summary"
                            className="grid gap-4 md:grid-cols-3"
                        >
                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Assignments
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {selectedGrades.length}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Available assessment records.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Average
                                </p>

                                <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                    {averagePercentage === null
                                        ? "N/A"
                                        : `${averagePercentage}%`}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Average across graded assignments.
                                </p>
                            </div>

                            <div className="rounded-2xl border bg-white p-5">
                                <p className="text-sm font-semibold text-slate-500">
                                    Student
                                </p>

                                <p className="mt-2 text-xl font-extrabold text-slate-950">
                                    {selectedStudentName}
                                </p>

                                <p className="mt-1 text-sm text-slate-500">
                                    Currently selected profile.
                                </p>
                            </div>
                        </section>

                        <section className="rounded-2xl border bg-white p-4 sm:p-6">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Assessment Results
                                </h2>

                                <p className="mt-2 text-base text-slate-600">
                                    Grades and feedback for{" "}
                                    <span className="font-semibold text-slate-900">
                                        {selectedStudentName}
                                    </span>
                                    .
                                </p>
                            </div>

                            {selectedGrades.length === 0 ? (
                                <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                                    No graded assignments are available yet.
                                </div>
                            ) : (
                                <div className="mt-6 grid gap-4">
                                    {selectedGrades.map(
                                        (grade) => {
                                            const percentage =
                                                calculatePercentage(
                                                    grade.score,
                                                    grade.max_score,
                                                );

                                            return (
                                                <article
                                                    key={
                                                        grade.submission_id
                                                    }
                                                    className="rounded-2xl border bg-slate-50 p-5"
                                                >
                                                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                                        <div>
                                                            <h3 className="text-lg font-bold text-slate-950">
                                                                {
                                                                    grade.assignment_title
                                                                }
                                                            </h3>

                                                            <p className="mt-1 text-sm text-slate-500">
                                                                Submitted{" "}
                                                                {formatDate(
                                                                    grade.submitted_at,
                                                                )}
                                                            </p>
                                                        </div>

                                                        <div className="rounded-2xl bg-blue-50 px-4 py-3 text-right">
                                                            <p className="text-sm font-semibold text-blue-700">
                                                                {grade.score ??
                                                                    "Pending"}{" "}
                                                                /{" "}
                                                                {
                                                                    grade.max_score
                                                                }
                                                            </p>

                                                            {percentage !==
                                                                null && (
                                                                    <p className="mt-1 text-xs font-bold text-blue-600">
                                                                        {
                                                                            percentage
                                                                        }
                                                                        %
                                                                    </p>
                                                                )}
                                                        </div>
                                                    </div>

                                                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                                                        <div>
                                                            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                                                Status
                                                            </p>

                                                            <p className="mt-1 text-sm font-semibold capitalize text-slate-700">
                                                                {
                                                                    grade.status
                                                                }
                                                            </p>
                                                        </div>

                                                        <div>
                                                            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                                                Graded
                                                            </p>

                                                            <p className="mt-1 text-sm font-semibold text-slate-700">
                                                                {formatDate(
                                                                    grade.graded_at,
                                                                )}
                                                            </p>
                                                        </div>
                                                    </div>

                                                    {grade.feedback && (
                                                        <div className="mt-4 rounded-xl bg-white p-4 text-sm leading-6 text-slate-700">
                                                            {
                                                                grade.feedback
                                                            }
                                                        </div>
                                                    )}
                                                </article>
                                            );
                                        },
                                    )}
                                </div>
                            )}
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}
