"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";
import { useTeacherCourses } from "@/hooks/useTeacherCourses";
import { createAssignment } from "@/lib/services/assignment";
import { UserRole } from "@/types/user";

export default function CreateTeacherAssignmentPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <CreateAssignmentContent />
        </RoleGate>
    );
}

function CreateAssignmentContent() {
    const router = useRouter();
    const { courses, isLoading: coursesLoading, error: coursesError } =
        useTeacherCourses();

    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [courseId, setCourseId] = useState("");
    const [dueDate, setDueDate] = useState("");
    const [maxScore, setMaxScore] = useState("100");
    const [isPublished, setIsPublished] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState("");

    const canSubmit =
        title.trim().length > 1 &&
        courseId &&
        Number(maxScore) > 0 &&
        !isSubmitting &&
        !coursesLoading;

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");

        try {
            setIsSubmitting(true);

            await createAssignment({
                title: title.trim(),
                description: description.trim() || undefined,
                course_id: Number(courseId),
                due_date: dueDate || null,
                max_score: Number(maxScore),
                is_published: isPublished,
            });

            router.push("/teacher/assignments");
            router.refresh();
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to create assignment.",
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="max-w-2xl p-6 sm:p-8">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
                Create Assignment
            </h1>
            <p className="mt-2 text-slate-500">
                Create a new assignment for your students.
            </p>

            <form
                onSubmit={handleSubmit}
                className="mt-6 space-y-5 rounded-2xl border bg-white p-6 shadow-sm"
            >
                {(error || coursesError) && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
                        {error || coursesError}
                    </div>
                )}

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Title
                    </label>
                    <input
                        value={title}
                        onChange={(event) => setTitle(event.target.value)}
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                        placeholder="Rates of reaction homework"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Description
                    </label>
                    <textarea
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                        className="mt-1 min-h-28 w-full rounded-lg border px-3 py-2 text-sm"
                        placeholder="Instructions for students..."
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Course
                    </label>
                    <select
                        value={courseId}
                        onChange={(event) => setCourseId(event.target.value)}
                        disabled={coursesLoading}
                        className="mt-1 w-full rounded-lg border px-3 py-2 text-sm disabled:opacity-50"
                    >
                        <option value="">
                            {coursesLoading ? "Loading courses..." : "Select a course"}
                        </option>

                        {courses.map((course) => (
                            <option key={course.id} value={course.id}>
                                {course.title}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Due date
                        </label>
                        <input
                            type="date"
                            value={dueDate}
                            onChange={(event) => setDueDate(event.target.value)}
                            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Max score
                        </label>
                        <input
                            type="number"
                            min={1}
                            value={maxScore}
                            onChange={(event) => setMaxScore(event.target.value)}
                            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                        />
                    </div>
                </div>

                <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    <input
                        type="checkbox"
                        checked={isPublished}
                        onChange={(event) => setIsPublished(event.target.checked)}
                    />
                    Publish immediately
                </label>

                <div className="flex gap-3">
                    <button
                        type="submit"
                        disabled={!canSubmit}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isSubmitting ? "Creating..." : "Create assignment"}
                    </button>

                    <button
                        type="button"
                        onClick={() => router.push("/teacher/assignments")}
                        className="rounded-lg border px-4 py-2 text-sm font-semibold"
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}