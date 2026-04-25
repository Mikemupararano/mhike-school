"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";

export default function TeacherCourseManagePage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherCourseManageContent />
        </RoleGate>
    );
}

function TeacherCourseManageContent() {
    const params = useParams();
    const courseId = String(params.courseId);

    return (
        <div className="p-6">
            <Link
                href="/teacher/courses"
                className="text-sm font-semibold text-blue-600 hover:underline"
            >
                ← Back to courses
            </Link>

            <h1 className="mt-4 text-3xl font-extrabold">Manage Course</h1>
            <p className="mt-2 text-slate-500">
                Course ID: <span className="font-semibold">{courseId}</span>
            </p>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <Link
                    href={`/teacher/classes`}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50"
                >
                    <h2 className="text-xl font-bold">Students</h2>
                    <p className="mt-2 text-sm text-slate-500">
                        View enrolled students and class groups.
                    </p>
                </Link>

                <Link
                    href={`/teacher/assignments`}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50"
                >
                    <h2 className="text-xl font-bold">Assignments</h2>
                    <p className="mt-2 text-sm text-slate-500">
                        Create, publish, and grade assignments.
                    </p>
                </Link>
            </div>
        </div>
    );
}