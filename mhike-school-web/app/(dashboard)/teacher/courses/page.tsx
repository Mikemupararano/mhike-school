"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import {
    getTeacherCourses,
    type TeacherCourse,
} from "@/lib/services/teacher";
import { UserRole } from "@/types/user";

export default function TeacherCoursesPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherCoursesContent />
        </RoleGate>
    );
}

function TeacherCoursesContent() {
    const [courses, setCourses] = useState<TeacherCourse[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadCourses() {
            try {
                setError(null);
                const data = await getTeacherCourses();
                setCourses(data);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load courses",
                );
            } finally {
                setIsLoading(false);
            }
        }

        void loadCourses();
    }, []);

    return (
        <div className="p-6">
            <h1 className="text-3xl font-extrabold">My Courses</h1>
            <p className="mt-2 text-slate-500">
                Manage your courses, students, and assignments.
            </p>

            {isLoading && <p className="mt-6">Loading courses...</p>}

            {error && (
                <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                    {error}
                </div>
            )}

            {!isLoading && !error && (
                <div className="mt-6 space-y-4">
                    {courses.length === 0 ? (
                        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">
                            No courses found.
                        </div>
                    ) : (
                        courses.map((course) => (
                            <div
                                key={course.id}
                                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                            >
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <h2 className="text-xl font-bold">
                                            {course.title}
                                        </h2>

                                        <div className="mt-2 text-sm text-slate-500">
                                            {course.students} students •{" "}
                                            {course.assignments} assignments
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <Link
                                            href={`/courses/${course.id}`}
                                            className="rounded-lg border px-3 py-1 text-sm hover:bg-slate-50"
                                        >
                                            View
                                        </Link>

                                        <Link
                                            href={`/teacher/courses/${course.id}`}
                                            className="rounded-lg bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
                                        >
                                            Manage
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}