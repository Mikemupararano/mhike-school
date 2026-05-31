"use client";

import type { StudentAttendanceProfile } from "@/lib/parent";

type AttendanceSummaryCardsProps = {
    profile: StudentAttendanceProfile;
};

function getAttendanceHealth(profile: StudentAttendanceProfile) {
    if (profile.attendance_percentage >= 95) {
        return {
            label: "Excellent",
            className: "bg-green-100 text-green-700",
        };
    }

    if (profile.attendance_percentage >= 90) {
        return {
            label: "Good",
            className: "bg-blue-100 text-blue-700",
        };
    }

    if (profile.attendance_percentage >= 80) {
        return {
            label: "Concern",
            className: "bg-yellow-100 text-yellow-700",
        };
    }

    return {
        label: "Persistent absence risk",
        className: "bg-red-100 text-red-700",
    };
}

export default function AttendanceSummaryCards({
    profile,
}: AttendanceSummaryCardsProps) {
    const attendanceHealth = getAttendanceHealth(profile);

    return (
        <>
            <section className="grid gap-4 md:grid-cols-4">
                <article className="rounded-2xl border bg-white p-5">
                    <div className="text-sm font-semibold text-slate-500">
                        Student
                    </div>

                    <div className="mt-2 text-2xl font-extrabold text-slate-950">
                        {profile.student_name ?? `Student ${profile.student_id}`}
                    </div>
                </article>

                <article className="rounded-2xl border bg-green-50 p-5">
                    <div className="text-sm font-semibold text-green-700">
                        Attendance
                    </div>

                    <div className="mt-2 text-3xl font-extrabold text-green-900">
                        {profile.attendance_percentage}%
                    </div>
                </article>

                <article className="rounded-2xl border bg-blue-50 p-5">
                    <div className="text-sm font-semibold text-blue-700">
                        Total Records
                    </div>

                    <div className="mt-2 text-3xl font-extrabold text-blue-900">
                        {profile.total_records}
                    </div>
                </article>

                <article className="rounded-2xl border bg-white p-5">
                    <div className="text-sm font-semibold text-slate-500">
                        Attendance Health
                    </div>

                    <div className="mt-4">
                        <span
                            className={`rounded-full px-3 py-2 text-sm font-bold ${attendanceHealth.className}`}
                        >
                            {attendanceHealth.label}
                        </span>
                    </div>
                </article>
            </section>

            <section className="grid gap-4 md:grid-cols-4">
                <article className="rounded-2xl border bg-green-50 p-5">
                    <div className="text-sm font-semibold text-green-700">
                        Present
                    </div>

                    <div className="mt-2 text-3xl font-extrabold text-green-900">
                        {profile.present}
                    </div>
                </article>

                <article className="rounded-2xl border bg-yellow-50 p-5">
                    <div className="text-sm font-semibold text-yellow-700">
                        Late
                    </div>

                    <div className="mt-2 text-3xl font-extrabold text-yellow-900">
                        {profile.late}
                    </div>
                </article>

                <article className="rounded-2xl border bg-blue-50 p-5">
                    <div className="text-sm font-semibold text-blue-700">
                        Authorised
                    </div>

                    <div className="mt-2 text-3xl font-extrabold text-blue-900">
                        {profile.authorised_absence}
                    </div>
                </article>

                <article className="rounded-2xl border bg-red-50 p-5">
                    <div className="text-sm font-semibold text-red-700">
                        Unauthorised
                    </div>

                    <div className="mt-2 text-3xl font-extrabold text-red-900">
                        {profile.unauthorised_absence}
                    </div>
                </article>
            </section>
        </>
    );
}