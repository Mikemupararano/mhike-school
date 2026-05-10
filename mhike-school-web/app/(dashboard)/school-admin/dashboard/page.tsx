"use client";

export default function SchoolAdminDashboardPage() {
    return (
        <div className="p-8 space-y-8">
            <div>
                <h1 className="text-3xl font-extrabold">
                    School Admin Dashboard
                </h1>

                <p className="mt-2 text-slate-500">
                    Manage your school users, teachers, students, and courses.
                </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
                <div className="rounded-2xl border bg-white p-6">
                    <div className="text-sm text-slate-500">
                        Total Teachers
                    </div>

                    <div className="mt-2 text-3xl font-extrabold">
                        0
                    </div>
                </div>

                <div className="rounded-2xl border bg-white p-6">
                    <div className="text-sm text-slate-500">
                        Total Students
                    </div>

                    <div className="mt-2 text-3xl font-extrabold">
                        0
                    </div>
                </div>

                <div className="rounded-2xl border bg-white p-6">
                    <div className="text-sm text-slate-500">
                        Total Courses
                    </div>

                    <div className="mt-2 text-3xl font-extrabold">
                        0
                    </div>
                </div>

                <div className="rounded-2xl border bg-white p-6">
                    <div className="text-sm text-slate-500">
                        Active Users
                    </div>

                    <div className="mt-2 text-3xl font-extrabold">
                        0
                    </div>
                </div>
            </div>

            <div className="rounded-2xl border bg-white p-6">
                <h2 className="text-xl font-bold">
                    Recent Activity
                </h2>

                <div className="mt-4 text-slate-500">
                    No recent activity yet.
                </div>
            </div>
        </div>
    );
}