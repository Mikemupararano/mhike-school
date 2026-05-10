"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiGet, apiPost } from "@/lib/api";

type Course = {
    id: number;
    title: string;
    description?: string | null;
    teacher_id?: number | null;
    teacher_name?: string | null;
    school_id?: number | null;
    published: boolean;
};

type CoursesResponse = {
    items: Course[];
    total: number;
    skip: number;
    limit: number;
};

export default function AdminContentPage() {
    const [courses, setCourses] = useState<Course[]>([]);

    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState<number | null>(null);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    async function loadCourses() {
        try {
            setLoading(true);

            const data = await apiGet<CoursesResponse>(
                "/admin/courses",
            );

            setCourses(data.items);
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to load courses");
            }
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadCourses();
    }, []);

    async function togglePublish(course: Course) {
        setError("");
        setSuccess("");

        try {
            setSavingId(course.id);

            const updated = await apiPost<Course>(
                `/admin/courses/${course.id}/publish`,
                {
                    published: !course.published,
                },
            );

            setCourses((prev) =>
                prev.map((c) =>
                    c.id === updated.id ? updated : c,
                ),
            );

            setSuccess(
                updated.published
                    ? "Course published"
                    : "Course unpublished",
            );
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to update course");
            }
        } finally {
            setSavingId(null);
        }
    }

    async function deleteCourse(course: Course) {
        const confirmed = confirm(
            `Delete "${course.title}"?`,
        );

        if (!confirmed) return;

        setError("");
        setSuccess("");

        try {
            setSavingId(course.id);

            await apiPost(
                `/admin/courses/${course.id}/delete`,
            );

            setCourses((prev) =>
                prev.filter((c) => c.id !== course.id),
            );

            setSuccess("Course deleted");
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to delete course");
            }
        } finally {
            setSavingId(null);
        }
    }

    if (loading) {
        return (
            <div className="p-8">
                Loading courses...
            </div>
        );
    }

    return (
        <div className="p-8 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold">
                        Content Admin
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Manage platform-wide courses and content.
                    </p>
                </div>
            </div>

            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3">
                    {error}
                </div>
            )}

            {success && (
                <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl px-4 py-3">
                    {success}
                </div>
            )}

            <div className="bg-white border rounded-2xl overflow-hidden">
                <table className="w-full">
                    <thead className="bg-slate-50">
                        <tr className="text-left">
                            <th className="px-6 py-4 font-semibold">
                                Course
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                Teacher
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                School ID
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                Published
                            </th>

                            <th className="px-6 py-4 font-semibold">
                                Actions
                            </th>
                        </tr>
                    </thead>

                    <tbody>
                        {courses.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={5}
                                    className="px-6 py-10 text-center text-slate-500"
                                >
                                    No courses found.
                                </td>
                            </tr>
                        ) : (
                            courses.map((course) => (
                                <tr
                                    key={course.id}
                                    className="border-t"
                                >
                                    <td className="px-6 py-4">
                                        <div className="font-semibold">
                                            {course.title}
                                        </div>

                                        <div className="text-sm text-slate-500">
                                            {course.description ||
                                                "No description"}
                                        </div>
                                    </td>

                                    <td className="px-6 py-4">
                                        {course.teacher_name ||
                                            "Not assigned"}
                                    </td>

                                    <td className="px-6 py-4">
                                        {course.school_id || "-"}
                                    </td>

                                    <td className="px-6 py-4">
                                        <span
                                            className={
                                                course.published
                                                    ? "text-green-600 font-semibold"
                                                    : "text-slate-500"
                                            }
                                        >
                                            {course.published
                                                ? "Published"
                                                : "Draft"}
                                        </span>
                                    </td>

                                    <td className="px-6 py-4">
                                        <div className="flex gap-3 flex-wrap">
                                            <Link
                                                href={`/admin/content/courses/${course.id}`}
                                                className="bg-slate-100 hover:bg-slate-200 px-4 py-2 rounded-lg text-sm font-medium"
                                            >
                                                View
                                            </Link>

                                            <button
                                                onClick={() =>
                                                    togglePublish(course)
                                                }
                                                disabled={
                                                    savingId === course.id
                                                }
                                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm"
                                            >
                                                {course.published
                                                    ? "Unpublish"
                                                    : "Publish"}
                                            </button>

                                            <button
                                                onClick={() =>
                                                    deleteCourse(course)
                                                }
                                                disabled={
                                                    savingId === course.id
                                                }
                                                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}