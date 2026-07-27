"use client";

import Link from "next/link";
import {
    GraduationCap,
    Search,
    ShieldCheck,
    UserPlus,
    Users,
} from "lucide-react";
import { useMemo, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import SchoolUserTable from "@/components/school-admin/components/SchoolUserTable";
import { useSchoolUsers } from "@/hooks/useSchoolUsers";
import { UserRole, type User } from "@/types/user";

type StatusFilter = "all" | "active" | "inactive";

const STATUS_OPTIONS: Array<{
    value: StatusFilter;
    label: string;
}> = [
        { value: "all", label: "All statuses" },
        { value: "active", label: "Active" },
        { value: "inactive", label: "Inactive" },
    ];

function getUserRoles(user: User): UserRole[] {
    if (user.roles?.length) {
        return user.roles;
    }

    return user.role ? [user.role] : [];
}

function getUserDisplayName(user: User): string {
    return user.full_name?.trim() || "Unnamed student";
}

function isUserActive(user: User): boolean {
    return user.is_active !== false;
}

export default function SchoolAdminStudentsPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <StudentsContent />
        </RoleGate>
    );
}

function StudentsContent() {
    const {
        users,
        isLoading,
        actionLoadingId,
        deactivateUser,
    } = useSchoolUsers();

    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] =
        useState<StatusFilter>("all");

    const allStudents = useMemo(
        () =>
            users.filter((user) =>
                getUserRoles(user).includes(
                    UserRole.STUDENT,
                ),
            ),
        [users],
    );

    const filteredStudents = useMemo(() => {
        const normalizedQuery = searchQuery
            .trim()
            .toLowerCase();

        return allStudents.filter((student) => {
            const matchesSearch =
                normalizedQuery.length === 0 ||
                getUserDisplayName(student)
                    .toLowerCase()
                    .includes(normalizedQuery) ||
                student.email
                    .toLowerCase()
                    .includes(normalizedQuery);

            const active = isUserActive(student);

            const matchesStatus =
                statusFilter === "all" ||
                (statusFilter === "active" && active) ||
                (statusFilter === "inactive" && !active);

            return matchesSearch && matchesStatus;
        });
    }, [
        allStudents,
        searchQuery,
        statusFilter,
    ]);

    const summary = useMemo(
        () => ({
            total: allStudents.length,
            active: allStudents.filter(isUserActive).length,
            inactive: allStudents.filter(
                (student) => !isUserActive(student),
            ).length,
        }),
        [allStudents],
    );

    const hasActiveFilters =
        searchQuery.trim().length > 0 ||
        statusFilter !== "all";

    async function handleDeactivate(user: User) {
        await deactivateUser(user.id);
    }

    function clearFilters() {
        setSearchQuery("");
        setStatusFilter("all");
    }

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto w-full max-w-7xl">
                <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-700">
                            School administration
                        </p>

                        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                            Students
                        </h1>

                        <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
                            Search student accounts, review
                            enrolment access and manage account
                            status.
                        </p>
                    </div>

                    <Link
                        href="/school-admin/users/create"
                        className="inline-flex items-center justify-center gap-2 self-start rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                    >
                        <UserPlus
                            aria-hidden="true"
                            className="h-4 w-4"
                        />
                        Add Student
                    </Link>
                </header>

                <div
                    aria-live="polite"
                    className="sr-only"
                >
                    {isLoading
                        ? "Loading students."
                        : `${filteredStudents.length} students displayed.`}
                </div>

                {isLoading ? (
                    <StudentsPageSkeleton />
                ) : (
                    <>
                        <section
                            aria-labelledby="student-summary-heading"
                            className="mt-8"
                        >
                            <h2
                                id="student-summary-heading"
                                className="sr-only"
                            >
                                Student summary
                            </h2>

                            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                                <SummaryCard
                                    title="Total Students"
                                    value={summary.total}
                                    icon={GraduationCap}
                                />

                                <SummaryCard
                                    title="Active Students"
                                    value={summary.active}
                                    icon={ShieldCheck}
                                />

                                <SummaryCard
                                    title="Inactive Students"
                                    value={summary.inactive}
                                    icon={Users}
                                />
                            </div>
                        </section>

                        <section
                            aria-labelledby="student-directory-heading"
                            className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
                        >
                            <div className="border-b border-slate-200 p-5 sm:p-6">
                                <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                                    <div>
                                        <h2
                                            id="student-directory-heading"
                                            className="text-xl font-extrabold text-slate-950"
                                        >
                                            Student directory
                                        </h2>

                                        <p className="mt-1 text-sm text-slate-500">
                                            Showing{" "}
                                            {
                                                filteredStudents.length
                                            }{" "}
                                            of{" "}
                                            {
                                                allStudents.length
                                            }{" "}
                                            students.
                                        </p>
                                    </div>

                                    <div className="grid w-full gap-3 sm:grid-cols-[minmax(260px,1fr)_180px] xl:w-auto">
                                        <label className="relative block">
                                            <span className="sr-only">
                                                Search students
                                            </span>

                                            <Search
                                                aria-hidden="true"
                                                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                                            />

                                            <input
                                                type="search"
                                                value={
                                                    searchQuery
                                                }
                                                onChange={(
                                                    event,
                                                ) =>
                                                    setSearchQuery(
                                                        event
                                                            .target
                                                            .value,
                                                    )
                                                }
                                                placeholder="Search name or email"
                                                className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                            />
                                        </label>

                                        <label>
                                            <span className="sr-only">
                                                Filter by account
                                                status
                                            </span>

                                            <select
                                                value={
                                                    statusFilter
                                                }
                                                onChange={(
                                                    event,
                                                ) =>
                                                    setStatusFilter(
                                                        event
                                                            .target
                                                            .value as StatusFilter,
                                                    )
                                                }
                                                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                            >
                                                {STATUS_OPTIONS.map(
                                                    (
                                                        option,
                                                    ) => (
                                                        <option
                                                            key={
                                                                option.value
                                                            }
                                                            value={
                                                                option.value
                                                            }
                                                        >
                                                            {
                                                                option.label
                                                            }
                                                        </option>
                                                    ),
                                                )}
                                            </select>
                                        </label>
                                    </div>
                                </div>
                            </div>

                            {filteredStudents.length ===
                                0 ? (
                                <EmptyStudentsState
                                    hasActiveFilters={
                                        hasActiveFilters
                                    }
                                    onClearFilters={
                                        clearFilters
                                    }
                                />
                            ) : (
                                <div className="overflow-x-auto p-4 sm:p-6">
                                    <SchoolUserTable
                                        users={
                                            filteredStudents
                                        }
                                        actionLoadingId={
                                            actionLoadingId
                                        }
                                        onDeactivate={
                                            handleDeactivate
                                        }
                                    />
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
    icon: Icon,
}: {
    title: string;
    value: number;
    icon: typeof Users;
}) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm font-bold text-slate-500">
                        {title}
                    </p>

                    <p className="mt-3 text-3xl font-extrabold tracking-tight text-slate-950">
                        {value.toLocaleString("en-GB")}
                    </p>
                </div>

                <div className="rounded-2xl bg-blue-50 p-3 text-blue-700">
                    <Icon
                        aria-hidden="true"
                        className="h-6 w-6"
                    />
                </div>
            </div>
        </article>
    );
}

function EmptyStudentsState({
    hasActiveFilters,
    onClearFilters,
}: {
    hasActiveFilters: boolean;
    onClearFilters: () => void;
}) {
    return (
        <div className="px-6 py-14 text-center">
            <GraduationCap
                aria-hidden="true"
                className="mx-auto h-10 w-10 text-slate-400"
            />

            <h3 className="mt-4 text-lg font-extrabold text-slate-900">
                {hasActiveFilters
                    ? "No matching students"
                    : "No students yet"}
            </h3>

            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                {hasActiveFilters
                    ? "Try changing the search term or status filter."
                    : "Create student accounts so pupils can access learning content and school services."}
            </p>

            <div className="mt-5 flex flex-wrap justify-center gap-3">
                {hasActiveFilters ? (
                    <button
                        type="button"
                        data-custom-button="true"
                        onClick={onClearFilters}
                        className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-100"
                    >
                        Clear filters
                    </button>
                ) : (
                    <Link
                        href="/school-admin/users/create"
                        className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-blue-800"
                    >
                        <UserPlus
                            aria-hidden="true"
                            className="h-4 w-4"
                        />
                        Add Student
                    </Link>
                )}
            </div>
        </div>
    );
}

function StudentsPageSkeleton() {
    return (
        <section
            aria-label="Loading students"
            className="mt-8"
        >
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 3 }).map(
                    (_, index) => (
                        <div
                            key={index}
                            className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white"
                        />
                    ),
                )}
            </div>

            <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <div className="border-b border-slate-200 p-6">
                    <div className="h-6 w-44 animate-pulse rounded bg-slate-200" />
                    <div className="mt-2 h-4 w-64 max-w-full animate-pulse rounded bg-slate-100" />

                    <div className="mt-5 grid gap-3 sm:grid-cols-2">
                        <div className="h-11 animate-pulse rounded-xl bg-slate-100" />
                        <div className="h-11 animate-pulse rounded-xl bg-slate-100" />
                    </div>
                </div>

                <div className="space-y-3 p-6">
                    {Array.from({ length: 6 }).map(
                        (_, index) => (
                            <div
                                key={index}
                                className="h-16 animate-pulse rounded-xl bg-slate-100"
                            />
                        ),
                    )}
                </div>
            </div>
        </section>
    );
}
