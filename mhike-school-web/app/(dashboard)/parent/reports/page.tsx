"use client";

import { useEffect, useMemo, useState } from "react";

import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

import {
    getParentReports,
    type StudentReport,
} from "@/lib/services/parentReports";

function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

export default function ParentReportsPage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading: childrenLoading,
        error: childrenError,
    } = useParentChildren();

    const [reports, setReports] = useState<StudentReport[]>([]);
    const [reportsLoading, setReportsLoading] = useState(true);
    const [reportsError, setReportsError] = useState<string | null>(null);

    useEffect(() => {
        async function loadReports() {
            try {
                setReportsLoading(true);
                setReportsError(null);

                const data = await getParentReports();

                setReports(data);
            } catch (err) {
                setReportsError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load reports.",
                );
            } finally {
                setReportsLoading(false);
            }
        }

        void loadReports();
    }, []);

    const selectedReports = useMemo(() => {
        if (!selectedStudentId) {
            return [];
        }

        return [...reports]
            .filter((report) => report.student_id === selectedStudentId)
            .sort(
                (first, second) =>
                    new Date(second.created_at).getTime() -
                    new Date(first.created_at).getTime(),
            );
    }, [reports, selectedStudentId]);

    const isLoading = childrenLoading || reportsLoading;
    const pageError = childrenError || reportsError;

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Child Reports
                </h1>

                <p className="mt-2 text-slate-500">
                    View published academic reports, progress summaries and
                    teacher feedback for your child.
                </p>
            </div>

            <ParentPageState
                loading={isLoading}
                error={pageError}
                isEmpty={profiles.length === 0 || !selectedProfile}
                loadingMessage="Loading reports..."
            >
                {selectedProfile && (
                    <>
                        <ChildSelector
                            profiles={profiles}
                            selectedStudentId={selectedStudentId}
                            onSelectStudent={setSelectedStudentId}
                            title="Linked Students"
                            description="Select a child to view their published reports."
                        />

                        <section className="rounded-2xl border bg-white p-6">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Published Reports
                                </h2>

                                <p className="mt-2 text-slate-500">
                                    Reports for{" "}
                                    <span className="font-semibold text-slate-900">
                                        {selectedProfile.student_name ??
                                            `Student ${selectedProfile.student_id}`}
                                    </span>
                                    .
                                </p>
                            </div>

                            {selectedReports.length === 0 ? (
                                <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                                    No published reports are currently
                                    available.
                                </div>
                            ) : (
                                <div className="mt-6 grid gap-4">
                                    {selectedReports.map((report) => (
                                        <article
                                            key={report.id}
                                            className="rounded-2xl border bg-slate-50 p-5"
                                        >
                                            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                                <div>
                                                    <h3 className="text-lg font-bold text-slate-950">
                                                        {report.title}
                                                    </h3>

                                                    <p className="mt-1 text-sm text-slate-500">
                                                        {report.academic_year}
                                                        {report.term
                                                            ? ` · ${report.term}`
                                                            : ""}
                                                    </p>

                                                    <p className="mt-1 text-xs text-slate-400">
                                                        Published report ·{" "}
                                                        {formatDate(
                                                            report.created_at,
                                                        )}
                                                    </p>
                                                </div>

                                                {report.grade && (
                                                    <span className="w-fit rounded-full bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">
                                                        {report.grade}
                                                    </span>
                                                )}
                                            </div>

                                            <p className="mt-4 whitespace-pre-line rounded-xl bg-white p-4 text-sm leading-6 text-slate-700">
                                                {report.report_text}
                                            </p>
                                        </article>
                                    ))}
                                </div>
                            )}
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}