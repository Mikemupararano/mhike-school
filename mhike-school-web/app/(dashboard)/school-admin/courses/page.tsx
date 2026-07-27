"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
    BookOpen,
    CheckCircle2,
    FileEdit,
    RefreshCw,
    Search,
    UserRound,
} from "lucide-react";

import RoleGate from "@/components/auth/RoleGate";
import { apiGet } from "@/lib/api";
import { UserRole } from "@/types/user";

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

type PublicationFilter = "all" | "published" | "draft";
type AssignmentFilter = "all" | "assigned" | "unassigned";

export default function SchoolAdminCoursesPage() {
    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <CoursesContent />
        </RoleGate>
    );
}

function CoursesContent() {
    const [courses, setCourses] = useState<Course[]>([]);
    const [totalCourses, setTotalCourses] = useState(0);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [publicationFilter, setPublicationFilter] =
        useState<PublicationFilter>("all");
    const [assignmentFilter, setAssignmentFilter] =
        useState<AssignmentFilter>("all");

    const loadCourses = useCallback(async (refresh = false) => {
        try {
            if (refresh) setRefreshing(true);
            else setLoading(true);

            setError(null);

            const data = await apiGet<CoursesResponse>("/school-admin/courses");
            setCourses(data.items);
            setTotalCourses(data.total);
        } catch (err) {
            console.error(err);
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load courses.",
            );
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        void loadCourses();
    }, [loadCourses]);

    const summary = useMemo(() => {
        const published = courses.filter((course) => course.published).length;
        const assigned = courses.filter(
            (course) =>
                Boolean(course.teacher_id) ||
                Boolean(course.teacher_name?.trim()),
        ).length;

        return {
            published,
            drafts: courses.length - published,
            assigned,
            unassigned: courses.length - assigned,
        };
    }, [courses]);

    const filteredCourses = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();

        return courses.filter((course) => {
            const matchesSearch =
                !query ||
                course.title.toLowerCase().includes(query) ||
                (course.description ?? "").toLowerCase().includes(query) ||
                (course.teacher_name ?? "").toLowerCase().includes(query);

            const matchesPublication =
                publicationFilter === "all" ||
                (publicationFilter === "published"
                    ? course.published
                    : !course.published);

            const assigned =
                Boolean(course.teacher_id) ||
                Boolean(course.teacher_name?.trim());

            const matchesAssignment =
                assignmentFilter === "all" ||
                (assignmentFilter === "assigned" ? assigned : !assigned);

            return matchesSearch && matchesPublication && matchesAssignment;
        });
    }, [assignmentFilter, courses, publicationFilter, searchQuery]);

    const hasFilters =
        Boolean(searchQuery.trim()) ||
        publicationFilter !== "all" ||
        assignmentFilter !== "all";

    function clearFilters() {
        setSearchQuery("");
        setPublicationFilter("all");
        setAssignmentFilter("all");
    }

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
                <header className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-700">
                            School administration
                        </p>
                        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                            Courses
                        </h1>
                        <p className="mt-2 max-w-2xl text-base text-slate-600 sm:text-lg">
                            Review school courses, publication status and teacher
                            assignments.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-3">
                        <button
                            type="button"
                            onClick={() => void loadCourses(true)}
                            disabled={loading || refreshing}
                            data-custom-button="true"
                            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                aria-hidden="true"
                                className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
                            />
                            {refreshing ? "Refreshing..." : "Refresh"}
                        </button>

                        <Link
                            href="/teacher/courses"
                            className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-800"
                        >
                            <BookOpen className="h-4 w-4" aria-hidden="true" />
                            View Teacher Courses
                        </Link>
                    </div>
                </header>

                <div className="sr-only" role="status" aria-live="polite">
                    {loading
                        ? "Loading courses."
                        : `${filteredCourses.length} courses displayed.`}
                </div>

                {error && (
                    <div
                        role="alert"
                        className="mt-6 flex flex-col gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:flex-row sm:items-center sm:justify-between"
                    >
                        <span className="font-medium">{error}</span>
                        <button
                            type="button"
                            onClick={() => void loadCourses()}
                            disabled={loading}
                            data-custom-button="true"
                            className="w-fit rounded-xl border border-red-300 bg-white px-4 py-2 font-bold text-red-700 transition hover:bg-red-100 disabled:opacity-60"
                        >
                            Retry
                        </button>
                    </div>
                )}

                {loading ? (
                    <LoadingState />
                ) : (
                    <>
                        <section
                            aria-label="Course summary"
                            className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
                        >
                            <SummaryCard
                                title="Total courses"
                                value={totalCourses || courses.length}
                                note={`${courses.length} loaded`}
                                icon={<BookOpen className="h-6 w-6" />}
                            />
                            <SummaryCard
                                title="Published"
                                value={summary.published}
                                note="Visible to learners"
                                icon={<CheckCircle2 className="h-6 w-6" />}
                            />
                            <SummaryCard
                                title="Drafts"
                                value={summary.drafts}
                                note="Not yet published"
                                icon={<FileEdit className="h-6 w-6" />}
                            />
                            <SummaryCard
                                title="Unassigned"
                                value={summary.unassigned}
                                note={`${summary.assigned} assigned`}
                                icon={<UserRound className="h-6 w-6" />}
                            />
                        </section>

                        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        School courses
                                    </h2>
                                    <p className="mt-1 text-sm text-slate-500">
                                        Search courses and filter by publication
                                        or teacher assignment.
                                    </p>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(240px,1fr)_180px_180px]">
                                    <label className="grid gap-1.5 sm:col-span-2 xl:col-span-1">
                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                            Search
                                        </span>
                                        <span className="relative">
                                            <Search
                                                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                                                aria-hidden="true"
                                            />
                                            <input
                                                type="search"
                                                value={searchQuery}
                                                onChange={(event) =>
                                                    setSearchQuery(event.target.value)
                                                }
                                                placeholder="Course or teacher..."
                                                className="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                            />
                                        </span>
                                    </label>

                                    <label className="grid gap-1.5">
                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                            Publication
                                        </span>
                                        <select
                                            value={publicationFilter}
                                            onChange={(event) =>
                                                setPublicationFilter(
                                                    event.target.value as PublicationFilter,
                                                )
                                            }
                                            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                        >
                                            <option value="all">All statuses</option>
                                            <option value="published">Published</option>
                                            <option value="draft">Draft</option>
                                        </select>
                                    </label>

                                    <label className="grid gap-1.5">
                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                            Teacher
                                        </span>
                                        <select
                                            value={assignmentFilter}
                                            onChange={(event) =>
                                                setAssignmentFilter(
                                                    event.target.value as AssignmentFilter,
                                                )
                                            }
                                            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                        >
                                            <option value="all">All assignments</option>
                                            <option value="assigned">Assigned</option>
                                            <option value="unassigned">Unassigned</option>
                                        </select>
                                    </label>
                                </div>
                            </div>

                            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
                                <p className="text-sm font-medium text-slate-600">
                                    Showing{" "}
                                    <span className="font-extrabold text-slate-950">
                                        {filteredCourses.length}
                                    </span>{" "}
                                    of{" "}
                                    <span className="font-extrabold text-slate-950">
                                        {courses.length}
                                    </span>{" "}
                                    loaded courses
                                </p>

                                {hasFilters && (
                                    <button
                                        type="button"
                                        onClick={clearFilters}
                                        data-custom-button="true"
                                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                                    >
                                        Clear filters
                                    </button>
                                )}
                            </div>

                            {filteredCourses.length === 0 ? (
                                <EmptyState
                                    filtered={hasFilters}
                                    onClear={clearFilters}
                                />
                            ) : (
                                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                                    {filteredCourses.map((course) => (
                                        <CourseCard key={course.id} course={course} />
                                    ))}
                                </div>
                            )}
                        </section>
                    </>
                )}
            </div>
        </main>
    );
}

function SummaryCard({
    title,
    value,
    note,
    icon,
}: {
    title: string;
    value: number;
    note: string;
    icon: React.ReactNode;
}) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm font-bold text-slate-500">{title}</p>
                    <p className="mt-3 text-3xl font-extrabold text-slate-950">
                        {value}
                    </p>
                    <p className="mt-1 text-xs font-medium text-slate-500">
                        {note}
                    </p>
                </div>
                <div
                    className="rounded-xl bg-blue-50 p-3 text-blue-700"
                    aria-hidden="true"
                >
                    {icon}
                </div>
            </div>
        </article>
    );
}

function CourseCard({ course }: { course: Course }) {
    const teacherName = course.teacher_name?.trim() || "Not assigned";
    const description =
        course.description?.trim() || "No description provided.";

    return (
        <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-blue-200 hover:bg-white hover:shadow-md">
            <div className="flex items-start justify-between gap-3">
                <h3 className="min-w-0 break-words text-lg font-bold text-slate-950">
                    {course.title}
                </h3>
                <span
                    className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${course.published
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-800"
                        }`}
                >
                    {course.published ? "Published" : "Draft"}
                </span>
            </div>

            <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">
                {description}
            </p>

            <div className="mt-auto pt-5">
                <div className="flex items-center gap-2 border-t border-slate-200 pt-4 text-sm text-slate-600">
                    <UserRound
                        className="h-4 w-4 shrink-0 text-slate-400"
                        aria-hidden="true"
                    />
                    <span className="truncate">
                        Teacher:{" "}
                        <span
                            className={
                                teacherName === "Not assigned"
                                    ? "font-bold text-amber-700"
                                    : "font-bold text-slate-900"
                            }
                        >
                            {teacherName}
                        </span>
                    </span>
                </div>
            </div>
        </article>
    );
}

function EmptyState({
    filtered,
    onClear,
}: {
    filtered: boolean;
    onClear: () => void;
}) {
    return (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
            <BookOpen
                className="mx-auto h-10 w-10 text-slate-400"
                aria-hidden="true"
            />
            <h3 className="mt-4 text-lg font-bold text-slate-950">
                {filtered ? "No matching courses" : "No courses found"}
            </h3>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                {filtered
                    ? "No courses match the current search and filters."
                    : "There are currently no courses assigned to this school."}
            </p>
            {filtered && (
                <button
                    type="button"
                    onClick={onClear}
                    data-custom-button="true"
                    className="mt-5 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-100"
                >
                    Clear filters
                </button>
            )}
        </div>
    );
}

function LoadingState() {
    return (
        <div className="mt-8 space-y-8" aria-hidden="true">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map((_, index) => (
                    <div
                        key={index}
                        className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white"
                    />
                ))}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6">
                <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
                <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, index) => (
                        <div
                            key={index}
                            className="h-48 animate-pulse rounded-2xl border border-slate-200 bg-slate-50"
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
