"use client";

import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

export default function ParentReportsPage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading,
        error,
    } = useParentChildren();

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Child Reports
                </h1>

                <p className="mt-2 text-slate-500">
                    View academic reports, progress summaries, and teacher
                    feedback for your child.
                </p>
            </div>

            <ParentPageState
                loading={loading}
                error={error}
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
                            description="Select a child to view their reports."
                        />

                        <section className="rounded-2xl border bg-white p-6">
                            <h2 className="text-xl font-bold text-slate-950">
                                Reports
                            </h2>

                            <p className="mt-2 text-slate-500">
                                Reports for{" "}
                                <span className="font-semibold text-slate-900">
                                    {selectedProfile.student_name ??
                                        `Student ${selectedProfile.student_id}`}
                                </span>{" "}
                                will appear here once report data is available.
                            </p>

                            <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-slate-500">
                                No reports have been published yet.
                            </div>
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}