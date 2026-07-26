"use client";

import { useMemo } from "react";

import AttendanceHistoryTable from "@/components/parent/AttendanceHistoryTable";
import AttendanceSummaryCards from "@/components/parent/AttendanceSummaryCards";
import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

export default function ParentAttendancePage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading,
        error,
    } = useParentChildren();

    const selectedStudentName = useMemo(() => {
        if (!selectedProfile) {
            return "Selected student";
        }

        return (
            selectedProfile.student_name ??
            `Student ${selectedProfile.student_id}`
        );
    }, [selectedProfile]);

    const attendanceRecordCount =
        selectedProfile?.history.length ?? 0;

    function handlePrint(): void {
        window.print();
    }

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Child Attendance
                    </h1>

                    <p className="mt-2 max-w-3xl text-base text-slate-600">
                        Review attendance records, attendance percentages
                        and absence history for your linked children.
                    </p>
                </div>

                <button
                    type="button"
                    data-custom-button="true"
                    onClick={handlePrint}
                    disabled={!selectedProfile}
                    className="w-fit rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 print:hidden"
                >
                    Print attendance
                </button>
            </header>

            <ParentPageState
                loading={loading}
                error={error}
                isEmpty={
                    profiles.length === 0 ||
                    !selectedProfile
                }
                loadingMessage="Loading attendance data..."
            >
                {selectedProfile && (
                    <>
                        <div className="print:hidden">
                            <ChildSelector
                                profiles={profiles}
                                selectedStudentId={selectedStudentId}
                                onSelectStudent={setSelectedStudentId}
                                title="Linked Students"
                                description="Select a child to view their attendance history."
                            />
                        </div>

                        <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5 sm:p-6">
                            <p className="text-sm font-bold uppercase tracking-wide text-blue-700">
                                Attendance overview
                            </p>

                            <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                                <div>
                                    <h2 className="text-2xl font-extrabold text-slate-950">
                                        {selectedStudentName}
                                    </h2>

                                    <p className="mt-1 text-base text-slate-600">
                                        Summary and complete attendance history
                                        for the selected student.
                                    </p>
                                </div>

                                <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
                                    <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                        Attendance records
                                    </p>

                                    <p className="mt-1 text-2xl font-extrabold text-slate-950">
                                        {attendanceRecordCount}
                                    </p>
                                </div>
                            </div>
                        </section>

                        <AttendanceSummaryCards
                            profile={selectedProfile}
                        />

                        <section className="rounded-2xl border bg-white p-4 sm:p-6">
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        Full Attendance History
                                    </h2>

                                    <p className="mt-1 text-base text-slate-600">
                                        Complete attendance record for{" "}
                                        <span className="font-semibold text-slate-900">
                                            {selectedStudentName}
                                        </span>
                                        .
                                    </p>
                                </div>

                                <p className="text-sm font-semibold text-slate-500">
                                    {attendanceRecordCount}{" "}
                                    {attendanceRecordCount === 1
                                        ? "record"
                                        : "records"}
                                </p>
                            </div>

                            <div className="mt-4">
                                <AttendanceHistoryTable
                                    records={selectedProfile.history}
                                    emptyMessage="No attendance history found for this student."
                                />
                            </div>
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}
