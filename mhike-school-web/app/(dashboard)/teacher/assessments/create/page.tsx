"use client";

import {
    FormEvent,
    useState,
} from "react";
import {
    useRouter,
} from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";
import { useTeacherCourses } from "@/hooks/useTeacherCourses";
import {
    createAssessment,
} from "@/lib/services/assessments";
import { UserRole } from "@/types/user";


function getDefaultAcademicYear(): string {
    const today =
        new Date();

    const year =
        today.getFullYear();

    const month =
        today.getMonth();

    const startYear =
        month >= 7
            ? year
            : year - 1;

    const endYear =
        String(
            (startYear + 1) % 100,
        ).padStart(
            2,
            "0",
        );

    return `${startYear}/${endYear}`;
}


export default function CreateTeacherAssessmentPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <CreateAssessmentContent />
        </RoleGate>
    );
}


function toIsoDateTime(
    value: string,
): string | null {
    if (!value) {
        return null;
    }

    const parsed =
        new Date(
            value,
        );

    if (Number.isNaN(parsed.getTime())) {
        return null;
    }

    return parsed.toISOString();
}


function CreateAssessmentContent() {
    const router =
        useRouter();

    const {
        courses,
        isLoading: coursesLoading,
        error: coursesError,
    } = useTeacherCourses();

    const [title, setTitle] =
        useState("");

    const [description, setDescription] =
        useState("");

    const [courseId, setCourseId] =
        useState("");

    const [assessmentType, setAssessmentType] =
        useState("");

    const [academicYear, setAcademicYear] =
        useState(
            getDefaultAcademicYear,
        );

    const [term, setTerm] =
        useState("");

    const [scheduledAt, setScheduledAt] =
        useState("");

    const [closesAt, setClosesAt] =
        useState("");

    const [anonymousMarking, setAnonymousMarking] =
        useState(false);

    const [isSubmitting, setIsSubmitting] =
        useState(false);

    const [error, setError] =
        useState("");


    const hasValidDateWindow =
        !scheduledAt
        || !closesAt
        || new Date(closesAt).getTime()
        > new Date(scheduledAt).getTime();


    const canSubmit =
        title.trim().length > 0
        && Boolean(courseId)
        && academicYear.trim().length > 0
        && hasValidDateWindow
        && !isSubmitting
        && !coursesLoading;


    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        setError("");

        if (!academicYear.trim()) {
            setError(
                "Academic year is required.",
            );
            return;
        }

        if (!hasValidDateWindow) {
            setError(
                "Assessment closing time must be later than its scheduled time.",
            );
            return;
        }

        try {
            setIsSubmitting(true);

            const assessment =
                await createAssessment({
                    course_id:
                        Number(courseId),

                    title:
                        title.trim(),

                    description:
                        description.trim()
                        || null,

                    assessment_type:
                        assessmentType.trim()
                        || null,

                    academic_year:
                        academicYear.trim(),

                    term:
                        term.trim()
                        || null,

                    anonymous_marking:
                        anonymousMarking,

                    scheduled_at:
                        toIsoDateTime(
                            scheduledAt,
                        ),

                    closes_at:
                        toIsoDateTime(
                            closesAt,
                        ),
                });

            router.push(
                `/teacher/assessments/${assessment.id}`,
            );

            router.refresh();
        } catch (err: unknown) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to create assessment.",
            );
        } finally {
            setIsSubmitting(false);
        }
    }


    return (
        <main className="max-w-3xl p-6 sm:p-8">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
                Create Assessment
            </h1>

            <p className="mt-2 text-slate-500">
                Create a draft assessment for one of your courses.
                Questions, candidates, grading and publication can be
                configured after creation.
            </p>

            <form
                onSubmit={handleSubmit}
                className="mt-6 space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
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
                        onChange={(event) =>
                            setTitle(
                                event.target.value,
                            )
                        }
                        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        placeholder="Mechanics Test 1"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Description
                    </label>

                    <textarea
                        value={description}
                        onChange={(event) =>
                            setDescription(
                                event.target.value,
                            )
                        }
                        className="mt-1 min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        placeholder="Assessment purpose, instructions or notes..."
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Course
                    </label>

                    <select
                        value={courseId}
                        onChange={(event) =>
                            setCourseId(
                                event.target.value,
                            )
                        }
                        disabled={coursesLoading}
                        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50"
                    >
                        <option value="">
                            {coursesLoading
                                ? "Loading courses..."
                                : "Select a course"}
                        </option>

                        {courses.map(
                            (course) => (
                                <option
                                    key={course.id}
                                    value={course.id}
                                >
                                    {course.title}
                                </option>
                            ),
                        )}
                    </select>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Assessment type
                        </label>

                        <input
                            value={assessmentType}
                            onChange={(event) =>
                                setAssessmentType(
                                    event.target.value,
                                )
                            }
                            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="Mock, test, practical..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Academic year
                        </label>

                        <input
                            value={academicYear}
                            onChange={(event) =>
                                setAcademicYear(
                                    event.target.value,
                                )
                            }
                            required
                            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            placeholder="2026/27"
                        />

                        <p className="mt-1 text-xs text-slate-500">
                            Defaults to the current school academic year.
                        </p>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700">
                        Term
                    </label>

                    <input
                        value={term}
                        onChange={(event) =>
                            setTerm(
                                event.target.value,
                            )
                        }
                        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        placeholder="Autumn Term"
                    />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Scheduled start
                        </label>

                        <input
                            type="datetime-local"
                            value={scheduledAt}
                            onChange={(event) =>
                                setScheduledAt(
                                    event.target.value,
                                )
                            }
                            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Closing time
                        </label>

                        <input
                            type="datetime-local"
                            value={closesAt}
                            onChange={(event) =>
                                setClosesAt(
                                    event.target.value,
                                )
                            }
                            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                    </div>
                </div>

                {!hasValidDateWindow && (
                    <p className="text-sm font-medium text-red-600">
                        Closing time must be later than the scheduled start.
                    </p>
                )}

                <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                    <input
                        type="checkbox"
                        checked={anonymousMarking}
                        onChange={(event) =>
                            setAnonymousMarking(
                                event.target.checked,
                            )
                        }
                        className="mt-1"
                    />

                    <span>
                        <span className="block font-semibold text-slate-900">
                            Anonymous marking
                        </span>

                        <span className="mt-1 block text-slate-500">
                            Hide normal student identity from markers where
                            supported by the marking workflow.
                        </span>
                    </span>
                </label>

                <div className="flex flex-wrap gap-3">
                    <button
                        type="submit"
                        disabled={!canSubmit}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isSubmitting
                            ? "Creating..."
                            : "Create assessment"}
                    </button>

                    <button
                        type="button"
                        onClick={() =>
                            router.push(
                                "/teacher/assessments",
                            )
                        }
                        className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </main>
    );
}