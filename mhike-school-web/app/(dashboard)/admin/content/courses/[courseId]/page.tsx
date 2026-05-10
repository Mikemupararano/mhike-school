"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

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

export default function AdminCourseDetailPage() {
    const params = useParams();
    const courseId = params.id;

    const [course, setCourse] = useState<Course | null>(null);

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    async function loadCourse() {
        try {
            setLoading(true);

            const data = await apiGet<{ items: Course[] }>("/admin/courses");

            const found = data.items.find(
                (c) => String(c.id) === String(courseId),
            );

            if (!found) {
                setError("Course not found");
                return;
            }

            setCourse(found);
        } catch (err) {
            console.error(err);
            setError("Failed to load course");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadCourse();
    }, [courseId]);

    async function handlePublishToggle() {
        if (!course) return;

        setError("");
        setSuccess("");

        try {
            setSaving(true);

            const updated = await apiPost<Course>(
                `/admin/courses/${course.id}/publish`,
                {
                    published: !course.published,
                },
            );

            setCourse(updated);

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
            setSaving(false);
        }
    }

    async function handleDelete() {
        if (!course) return;

        const confirmed = confirm(
            `Delete "${course.title}"?`,
        );

        if (!confirmed) return;

        try {
            setSaving(true);

            await apiPost(
                `/admin/courses/${course.id}/delete`,
            );

            setSuccess("Course deleted");

            setTimeout(() => {
                window.location.href = "/admin/courses";
            }, 1200);
        } catch (err) {
            console.error(err);

            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Failed to delete course");
            }
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return (
            <div className="p-8">
                Loading course...
            </div>
        );
    }

    if (!course) {
        return (
            <div className="p-8 text-red-600">
                Course not found.
            </div>
        );
    }

    return (
        <div className="p-8 space-y-6">
            <div>
                <h1 className="text-3xl font-extrabold">
                    {course.title}
                </h1>

                <p className="mt-2 text-slate-500">
                    Platform admin course management.
                </p>
            </div>

            <div className="bg-white border rounded-2xl p-6 space-y-4">
                <div>
                    <div className="text-sm text-slate-500">
                        Course ID
                    </div>

                    <div className="font-semibold">
                        {course.id}
                    </div>
                </div>

                <div>
                    <div className="text-sm text-slate-500">
                        Description
                    </div>

                    <div>
                        {course.description || "No description"}
                    </div>
                </div>

                <div>
                    <div className="text-sm text-slate-500">
                        Teacher
                    </div>

                    <div>
                        {course.teacher_name || "Not assigned"}
                    </div>
                </div>

                <div>
                    <div className="text-sm text-slate-500">
                        Published
                    </div>

                    <div
                        className={
                            course.published
                                ? "text-green-600 font-semibold"
                                : "text-slate-500"
                        }
                    >
                        {course.published ? "Yes" : "No"}
                    </div>
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

            <div className="flex gap-4">
                <button
                    onClick={handlePublishToggle}
                    disabled={saving}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold"
                >
                    {saving
                        ? "Saving..."
                        : course.published
                            ? "Unpublish Course"
                            : "Publish Course"}
                </button>

                <button
                    onClick={handleDelete}
                    disabled={saving}
                    className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-xl font-semibold"
                >
                    Delete Course
                </button>
            </div>
        </div>
    );
}