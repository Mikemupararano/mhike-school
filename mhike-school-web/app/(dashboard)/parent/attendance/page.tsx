"use client";

import { useMemo } from "react";

import AttendanceHistoryTable from "@/components/parent/AttendanceHistoryTable";
import AttendanceSummaryCards from "@/components/parent/AttendanceSummaryCards";
import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

function PrintIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-5 w-5"
            stroke="currentColor"
            strokeWidth="1.8"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7.5 8.25V3.75h9v4.5M7.5 16.5v3.75h9V16.5"
            />
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 8.25h12A2.25 2.25 0 0 1 20.25 10.5v4.5H16.5v-2.25h-9V15H3.75v-4.5A2.25 2.25 0 0 1 6 8.25Z"
            />
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.25 11.25h.008v.008h-.008z"
            />
        </svg>
    );
}

function AttendanceIcon() {
    return (
        <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            className="h-7 w-7"
            stroke="currentColor"
            strokeWidth="1.8"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6.75 3.75v2.5M17.25 3.75v2.5M4.5 8.25h15M6 5.25h12A1.5 1.5 0 0 1 19.5 6.75v11.5A1.5 1.5 0 0 1 18 19.75H6a1.5 1.5 0 0 1-1.5-1.5V6.75A1.5 1.5 0 0 1 6 5.25Z"
            />
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m8.25 13 2.25 2.25 5.25-5.25"
            />
        </svg>
    );
}

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

    const attendanceRecordLabel =
        attendanceRecordCount === 1 ? "record" : "records";

    function handlePrint(): void {
        window.print();
    }

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <header className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 print:border-0 print:p-0 print:shadow-none">
                <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                    <div className="flex min-w-0 items-start gap-4">
                        <div className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-white sm:flex print:hidden">
                            <AttendanceIcon />
                        </div>

                        <div className="min-w-0">
                            <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700 print:hidden">
                                Parent portal
                            </p>

                            <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950">
                                Child Attendance
                            </h1>

                            <p className="mt-2 max-w-3xl text-base leading-7 text-slate-600">
                                Review attendance records, attendance
                                percentages and absence history for your linked
                                children.
                            </p>
                        </div>
                    </div>

                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={handlePrint}
                        disabled={!selectedProfile}
                        className="inline-flex w-fit items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-base font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 print:hidden"
                    >
                        <PrintIcon />
                        Print attendance
                    </button>
                </div>
            </header>

            <ParentPageState
                loading={loading}
                error={error}
                isEmpty={profiles.length === 0 || !selectedProfile}
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
                                description="Select one of your linked children to review their complete attendance record."
                            />
                        </div>

                        <section
                            aria-labelledby="attendance-overview-heading"
                            className="rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-5 shadow-sm sm:p-6 print:border-slate-300 print:bg-white print:shadow-none"
                        >
                            <p className="text-sm font-bold uppercase tracking-[0.14em] text-blue-700">
                                Attendance overview
                            </p>

                            <div className="mt-2 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                                <div>
                                    <h2
                                        id="attendance-overview-heading"
                                        className="text-2xl font-extrabold tracking-tight text-slate-950"
                                    >
                                        {selectedStudentName}
                                    </h2>

                                    <p className="mt-1 max-w-2xl text-base leading-7 text-slate-600">
                                        Summary and complete attendance history
                                        for the selected student.
                                    </p>
                                </div>

                                <div
                                    aria-label={`${attendanceRecordCount} attendance ${attendanceRecordLabel}`}
                                    className="w-fit rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm print:shadow-none"
                                >
                                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                                        Attendance records
                                    </p>

                                    <p className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950">
                                        {attendanceRecordCount}
                                    </p>
                                </div>
                            </div>
                        </section>

                        <AttendanceSummaryCards profile={selectedProfile} />

                        <section
                            aria-labelledby="full-attendance-history-heading"
                            className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6 print:border-slate-300 print:shadow-none"
                        >
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <h2
                                        id="full-attendance-history-heading"
                                        className="text-xl font-bold text-slate-950"
                                    >
                                        Full Attendance History
                                    </h2>

                                    <p className="mt-1 text-base leading-7 text-slate-600">
                                        Complete attendance record for{" "}
                                        <span className="font-semibold text-slate-900">
                                            {selectedStudentName}
                                        </span>
                                        .
                                    </p>
                                </div>

                                <p className="shrink-0 rounded-full bg-slate-100 px-3 py-1.5 text-sm font-semibold text-slate-600 print:bg-white print:px-0">
                                    {attendanceRecordCount}{" "}
                                    {attendanceRecordLabel}
                                </p>
                            </div>

                            <div className="mt-4 overflow-x-auto">
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
