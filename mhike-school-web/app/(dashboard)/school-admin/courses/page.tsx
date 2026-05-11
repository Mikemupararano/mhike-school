"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type Course = {
    id: number;
    title: string;
    description?: string | null;
    teacher_id?: number | null;
    teacher_name?: string | null;
    school_id: number;
    published: boolean;
};

type CoursesResponse = {
    items: Course[];
    total: number;
    skip: number;
    limit: number;
};

export default function SchoolAdminCoursesPage() {
    const [courses, setCourses] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        async function loadCourses() {
            try {
                setLoading(true);
                setError("");

                const data = await apiGet<CoursesResponse>("/school-admin/courses");
                setCourses(data.items);
            } catch (err) {
                console.error(err);
                setError(err instanceof Error ? err.message : "Failed to load courses.");
            } finally {
                setLoading(false);
            }
        }

        loadCourses();
    }, []);

    return (
        <div className="p-8 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold">Courses</h1>
                    <p className="mt-2 text-slate-500">
                        Manage courses assigned to your school.
                    </p>
                </div>

                <Link
                    href="/teacher/courses"
                    className="rounded-xl border px-5 py-3 font-semibold hover:bg-slate-50"
                >
                    View Teacher Courses
                </Link>
            </div>

            {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                    {error}
                </div>
            ) : null}

            <div className="rounded-2xl border bg-white p-6">
                {loading ? (
                    <p className="text-slate-500">Loading courses...</p>
                ) : courses.length === 0 ? (
                    <p className="text-slate-500">No courses found for this school.</p>
                ) : (
                    <div className="space-y-3">
                        {courses.map((course) => (
                            <div key={course.id} className="rounded-xl border p-4">
                                <div className="font-semibold">{course.title}</div>
                                <div className="text-sm text-slate-500">
                                    {course.description || "No description"}
                                </div>
                                <div className="mt-2 text-sm text-slate-500">
                                    Teacher: {course.teacher_name || "Not assigned"}
                                </div>
                                <div className="text-sm text-slate-500">
                                    Status: {course.published ? "Published" : "Draft"}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}