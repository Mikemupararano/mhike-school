"use client";

import {
    useCallback,
    useEffect,
    useState,
} from "react";
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

    const courseId =
        typeof params.id === "string"
            ? params.id
            : Array.isArray(params.id)
                ? params.id[0]
                : "";

    const [course, setCourse] =
        useState<Course | null>(null);

    const [loading, setLoading] =
        useState(true);

    const [saving, setSaving] =
        useState(false);

    const [error, setError] =
        useState("");

    const [success, setSuccess] =
        useState("");

    const loadCourse = useCallback(
        async () => {
            try {
                setLoading(true);
                setError("");

                const data =
                    await apiGet<{
                        items: Course[];
                    }>(
                        "/admin/courses",
                    );

                const found =
                    data.items.find(
                        (course) =>
                            String(
                                course.id,
                            ) ===
                            String(
                                courseId,
                            ),
                    );

                if (!found) {
                    setError(
                        "Course not found",
                    );
                    setCourse(
                        null,
                    );

                    return;
                }

                setCourse(
                    found,
                );
            } catch (err) {
                console.error(
                    err,
                );

                setError(
                    "Failed to load course",
                );
            } finally {
                setLoading(
                    false,
                );
            }
        },
        [courseId],
    );

    useEffect(() => {
        void loadCourse();
    }, [loadCourse]);

    const handlePublishToggle =
        useCallback(
            async () => {
                if (!course) {
                    return;
                }

                setError("");
                setSuccess("");

                try {
                    setSaving(
                        true,
                    );

                    const updated =
                        await apiPost<Course>(
                            `/admin/courses/${course.id}/publish`,
                            {
                                published:
                                    !course.published,
                            },
                        );

                    setCourse(
                        updated,
                    );

                    setSuccess(
                        updated.published
                            ? "Course published"
                            : "Course unpublished",
                    );
                } catch (err) {
                    console.error(
                        err,
                    );

                    if (
                        err instanceof
                        Error
                    ) {
                        setError(
                            err.message,
                        );
                    } else {
                        setError(
                            "Failed to update course",
                        );
                    }
                } finally {
                    setSaving(
                        false,
                    );
                }
            },
            [course],
        );

    const handleDelete =
        useCallback(
            async () => {
                if (!course) {
                    return;
                }

                const confirmed =
                    window.confirm(
                        `Delete "${course.title}"?`,
                    );

                if (
                    !confirmed
                ) {
                    return;
                }

                try {
                    setSaving(
                        true,
                    );

                    await apiPost(
                        `/admin/courses/${course.id}/delete`,
                    );

                    setSuccess(
                        "Course deleted",
                    );

                    setTimeout(
                        () => {
                            window.location.href =
                                "/admin/courses";
                        },
                        1200,
                    );
                } catch (err) {
                    console.error(
                        err,
                    );

                    if (
                        err instanceof
                        Error
                    ) {
                        setError(
                            err.message,
                        );
                    } else {
                        setError(
                            "Failed to delete course",
                        );
                    }
                } finally {
                    setSaving(
                        false,
                    );
                }
            },
            [course],
        );

    if (loading) {
        return (
            <div className="p-8">
                Loading
                course...
            </div>
        );
    }

    if (!course) {
        return (
            <div className="p-8 text-red-600">
                Course not
                found.
            </div>
        );
    }

    return (
        <div className="space-y-6 p-8">
            <div>
                <h1 className="text-3xl font-extrabold">
                    {
                        course.title
                    }
                </h1>

                <p className="mt-2 text-slate-500">
                    Platform
                    admin
                    course
                    management.
                </p>
            </div>

            <div className="space-y-4 rounded-2xl border bg-white p-6">
                <div>
                    <div className="text-sm text-slate-500">
                        Course
                        ID
                    </div>

                    <div className="font-semibold">
                        {
                            course.id
                        }
                    </div>
                </div>

                <div>
                    <div className="text-sm text-slate-500">
                        Description
                    </div>

                    <div>
                        {course.description ??
                            "No description"}
                    </div>
                </div>

                <div>
                    <div className="text-sm text-slate-500">
                        Teacher
                    </div>

                    <div>
                        {course.teacher_name ??
                            "Not assigned"}
                    </div>
                </div>

                <div>
                    <div className="text-sm text-slate-500">
                        Published
                    </div>

                    <div
                        className={
                            course.published
                                ? "font-semibold text-green-600"
                                : "text-slate-500"
                        }
                    >
                        {course.published
                            ? "Yes"
                            : "No"}
                    </div>
                </div>
            </div>

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                    {error}
                </div>
            )}

            {success && (
                <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-green-700">
                    {success}
                </div>
            )}

            <div className="flex gap-4">
                <button
                    type="button"
                    onClick={
                        handlePublishToggle
                    }
                    disabled={
                        saving
                    }
                    className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {saving
                        ? "Saving..."
                        : course.published
                            ? "Unpublish Course"
                            : "Publish Course"}
                </button>

                <button
                    type="button"
                    onClick={
                        handleDelete
                    }
                    disabled={
                        saving
                    }
                    className="rounded-xl bg-red-600 px-6 py-3 font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    Delete
                    Course
                </button>
            </div>
        </div>
    );
}