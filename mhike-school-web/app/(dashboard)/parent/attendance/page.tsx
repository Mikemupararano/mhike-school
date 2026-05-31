"use client";

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

    return (
        <main className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-950">
                    Child Attendance
                </h1>

                <p className="mt-2 text-slate-500">
                    Review attendance records, attendance percentages, and
                    absence history for your child.
                </p>
            </div>

            <ParentPageState
                loading={loading}
                error={error}
                isEmpty={profiles.length === 0 || !selectedProfile}
                loadingMessage="Loading attendance data..."
            >
                {selectedProfile && (
                    <>
                        <ChildSelector
                            profiles={profiles}
                            selectedStudentId={selectedStudentId}
                            onSelectStudent={setSelectedStudentId}
                            title="Linked Students"
                            description="Select a child to view their attendance history."
                        />

                        <AttendanceSummaryCards profile={selectedProfile} />

                        <section className="rounded-2xl border bg-white p-6">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Full Attendance History
                                </h2>

                                <p className="mt-1 text-sm text-slate-500">
                                    Complete attendance record for the selected
                                    student.
                                </p>
                            </div>

                            <AttendanceHistoryTable
                                records={selectedProfile.history}
                                emptyMessage="No attendance history found for this student."
                            />
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}