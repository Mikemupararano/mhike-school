"use client";

import Link from "next/link";
import {
    Search,
    RefreshCw,
    UserPlus,
    Users,
    GraduationCap,
    School,
    ShieldCheck,
    CircleUserRound,
} from "lucide-react";
import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";

import { apiGet } from "@/lib/api";

type SchoolUser = {
    id: number;
    full_name: string | null;
    email: string;
    role: string;
    school_id: number | null;
    is_active?: boolean;
};

type RoleFilter =
    | "all"
    | "teacher"
    | "student"
    | "school_admin"
    | "platform_admin";

type StatusFilter = "all" | "active" | "inactive";

const ROLE_OPTIONS: Array<{
    value: RoleFilter;
    label: string;
}> = [
        { value: "all", label: "All roles" },
        { value: "teacher", label: "Teachers" },
        { value: "student", label: "Students" },
        { value: "school_admin", label: "School admins" },
        { value: "platform_admin", label: "Platform admins" },
    ];

const STATUS_OPTIONS: Array<{
    value: StatusFilter;
    label: string;
}> = [
        { value: "all", label: "All statuses" },
        { value: "active", label: "Active" },
        { value: "inactive", label: "Inactive" },
    ];

function formatRole(role: string): string {
    return role
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) =>
            character.toUpperCase(),
        );
}

function formatUpdatedTime(value: Date | null): string | null {
    if (!value) {
        return null;
    }

    return value.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

function isUserActive(user: SchoolUser): boolean {
    return user.is_active !== false;
}

export default function SchoolAdminUsersPage() {
    const [users, setUsers] = useState<SchoolUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] =
        useState<Date | null>(null);

    const [searchQuery, setSearchQuery] = useState("");
    const [roleFilter, setRoleFilter] =
        useState<RoleFilter>("all");
    const [statusFilter, setStatusFilter] =
        useState<StatusFilter>("all");

    const requestInProgressRef = useRef(false);

    const loadUsers = useCallback(
        async (showInitialLoader = false) => {
            if (requestInProgressRef.current) {
                return;
            }

            try {
                requestInProgressRef.current = true;
                setError(null);

                if (showInitialLoader) {
                    setLoading(true);
                } else {
                    setRefreshing(true);
                }

                const data = await apiGet<SchoolUser[]>(
                    "/school-users/",
                );

                setUsers(data);
                setLastUpdated(new Date());
            } catch (err) {
                console.error(err);

                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load school users.",
                );
            } finally {
                requestInProgressRef.current = false;
                setLoading(false);
                setRefreshing(false);
            }
        },
        [],
    );

    useEffect(() => {
        void loadUsers(true);
    }, [loadUsers]);

    const filteredUsers = useMemo(() => {
        const normalizedQuery = searchQuery
            .trim()
            .toLowerCase();

        return users.filter((user) => {
            const matchesSearch =
                normalizedQuery.length === 0 ||
                (user.full_name ?? "")
                    .toLowerCase()
                    .includes(normalizedQuery) ||
                user.email
                    .toLowerCase()
                    .includes(normalizedQuery) ||
                formatRole(user.role)
                    .toLowerCase()
                    .includes(normalizedQuery);

            const matchesRole =
                roleFilter === "all" ||
                user.role === roleFilter;

            const active = isUserActive(user);

            const matchesStatus =
                statusFilter === "all" ||
                (statusFilter === "active" && active) ||
                (statusFilter === "inactive" && !active);

            return (
                matchesSearch &&
                matchesRole &&
                matchesStatus
            );
        });
    }, [
        users,
        searchQuery,
        roleFilter,
        statusFilter,
    ]);

    const summary = useMemo(
        () => ({
            total: users.length,
            teachers: users.filter(
                (user) => user.role === "teacher",
            ).length,
            students: users.filter(
                (user) => user.role === "student",
            ).length,
            active: users.filter(isUserActive).length,
        }),
        [users],
    );

    const hasActiveFilters =
        searchQuery.trim().length > 0 ||
        roleFilter !== "all" ||
        statusFilter !== "all";

    const updatedTime =
        formatUpdatedTime(lastUpdated);

    function clearFilters() {
        setSearchQuery("");
        setRoleFilter("all");
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
                            School Users
                        </h1>

                        <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
                            Search, review and manage the
                            teachers, students and
                            administrators registered at your
                            school.
                        </p>

                        {updatedTime && (
                            <p className="mt-2 text-sm text-slate-400">
                                Last updated at{" "}
                                {updatedTime}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-3">
                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadUsers(false);
                            }}
                            disabled={
                                loading || refreshing
                            }
                            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                aria-hidden="true"
                                className={`h-4 w-4 ${refreshing
                                    ? "animate-spin"
                                    : ""
                                    }`}
                            />
                            {refreshing
                                ? "Refreshing..."
                                : "Refresh"}
                        </button>

                        <Link
                            href="/school-admin/users/create"
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                        >
                            <UserPlus
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            Create User
                        </Link>
                    </div>
                </header>

                <div
                    aria-live="polite"
                    className="sr-only"
                >
                    {loading
                        ? "Loading school users."
                        : refreshing
                            ? "Refreshing school users."
                            : error
                                ? error
                                : `${filteredUsers.length} users displayed.`}
                </div>

                {error && (
                    <section
                        role="alert"
                        className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5"
                    >
                        <h2 className="text-base font-extrabold text-red-900">
                            Unable to load users
                        </h2>

                        <p className="mt-2 text-sm leading-6 text-red-700">
                            {error}
                        </p>

                        <button
                            type="button"
                            data-custom-button="true"
                            onClick={() => {
                                void loadUsers(
                                    users.length === 0,
                                );
                            }}
                            disabled={
                                loading || refreshing
                            }
                            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-red-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            Try again
                        </button>
                    </section>
                )}

                {loading ? (
                    <UsersPageSkeleton />
                ) : (
                    <>
                        <section
                            aria-labelledby="user-summary-heading"
                            className="mt-8"
                        >
                            <h2
                                id="user-summary-heading"
                                className="sr-only"
                            >
                                User summary
                            </h2>

                            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                                <SummaryCard
                                    title="Total Users"
                                    value={summary.total}
                                    icon={Users}
                                />
                                <SummaryCard
                                    title="Teachers"
                                    value={summary.teachers}
                                    icon={GraduationCap}
                                />
                                <SummaryCard
                                    title="Students"
                                    value={summary.students}
                                    icon={School}
                                />
                                <SummaryCard
                                    title="Active Users"
                                    value={summary.active}
                                    icon={ShieldCheck}
                                />
                            </div>
                        </section>

                        <section
                            aria-labelledby="user-directory-heading"
                            className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
                        >
                            <div className="border-b border-slate-200 p-5 sm:p-6">
                                <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                                    <div>
                                        <h2
                                            id="user-directory-heading"
                                            className="text-xl font-extrabold text-slate-950"
                                        >
                                            User directory
                                        </h2>

                                        <p className="mt-1 text-sm text-slate-500">
                                            Showing{" "}
                                            {
                                                filteredUsers.length
                                            }{" "}
                                            of {users.length}{" "}
                                            users.
                                        </p>
                                    </div>

                                    <div className="grid w-full gap-3 sm:grid-cols-2 xl:w-auto xl:grid-cols-[minmax(260px,1fr)_180px_180px]">
                                        <label className="relative block sm:col-span-2 xl:col-span-1">
                                            <span className="sr-only">
                                                Search users
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
                                                placeholder="Search name, email or role"
                                                className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                            />
                                        </label>

                                        <label>
                                            <span className="sr-only">
                                                Filter by role
                                            </span>

                                            <select
                                                value={
                                                    roleFilter
                                                }
                                                onChange={(
                                                    event,
                                                ) =>
                                                    setRoleFilter(
                                                        event
                                                            .target
                                                            .value as RoleFilter,
                                                    )
                                                }
                                                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                            >
                                                {ROLE_OPTIONS.map(
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

                                        <label>
                                            <span className="sr-only">
                                                Filter by
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

                            {filteredUsers.length === 0 ? (
                                <EmptyUsersState
                                    hasActiveFilters={
                                        hasActiveFilters
                                    }
                                    onClearFilters={
                                        clearFilters
                                    }
                                />
                            ) : (
                                <>
                                    <div className="hidden overflow-x-auto md:block">
                                        <table className="min-w-full divide-y divide-slate-200">
                                            <caption className="sr-only">
                                                School user
                                                directory including
                                                name, email, role and
                                                account status.
                                            </caption>

                                            <thead className="bg-slate-50">
                                                <tr>
                                                    <th
                                                        scope="col"
                                                        className="px-6 py-4 text-left text-xs font-extrabold uppercase tracking-wider text-slate-500"
                                                    >
                                                        Name
                                                    </th>
                                                    <th
                                                        scope="col"
                                                        className="px-6 py-4 text-left text-xs font-extrabold uppercase tracking-wider text-slate-500"
                                                    >
                                                        Email
                                                    </th>
                                                    <th
                                                        scope="col"
                                                        className="px-6 py-4 text-left text-xs font-extrabold uppercase tracking-wider text-slate-500"
                                                    >
                                                        Role
                                                    </th>
                                                    <th
                                                        scope="col"
                                                        className="px-6 py-4 text-left text-xs font-extrabold uppercase tracking-wider text-slate-500"
                                                    >
                                                        Status
                                                    </th>
                                                </tr>
                                            </thead>

                                            <tbody className="divide-y divide-slate-100 bg-white">
                                                {filteredUsers.map(
                                                    (
                                                        user,
                                                    ) => (
                                                        <UserTableRow
                                                            key={
                                                                user.id
                                                            }
                                                            user={
                                                                user
                                                            }
                                                        />
                                                    ),
                                                )}
                                            </tbody>
                                        </table>
                                    </div>

                                    <div className="divide-y divide-slate-100 md:hidden">
                                        {filteredUsers.map(
                                            (user) => (
                                                <UserMobileCard
                                                    key={
                                                        user.id
                                                    }
                                                    user={
                                                        user
                                                    }
                                                />
                                            ),
                                        )}
                                    </div>
                                </>
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

function UserTableRow({
    user,
}: {
    user: SchoolUser;
}) {
    const active = isUserActive(user);

    return (
        <tr className="transition hover:bg-slate-50">
            <td className="px-6 py-4">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-600">
                        <CircleUserRound
                            aria-hidden="true"
                            className="h-5 w-5"
                        />
                    </div>

                    <div className="min-w-0">
                        <p className="truncate font-bold text-slate-900">
                            {user.full_name ||
                                "Unnamed user"}
                        </p>

                        <p className="mt-0.5 text-xs text-slate-400">
                            User #{user.id}
                        </p>
                    </div>
                </div>
            </td>

            <td className="px-6 py-4 text-sm text-slate-600">
                <span className="break-all">
                    {user.email}
                </span>
            </td>

            <td className="px-6 py-4">
                <RoleBadge role={user.role} />
            </td>

            <td className="px-6 py-4">
                <StatusBadge active={active} />
            </td>
        </tr>
    );
}

function UserMobileCard({
    user,
}: {
    user: SchoolUser;
}) {
    const active = isUserActive(user);

    return (
        <article className="p-5">
            <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-600">
                    <CircleUserRound
                        aria-hidden="true"
                        className="h-6 w-6"
                    />
                </div>

                <div className="min-w-0 flex-1">
                    <h3 className="truncate font-extrabold text-slate-900">
                        {user.full_name ||
                            "Unnamed user"}
                    </h3>

                    <p className="mt-1 break-all text-sm text-slate-500">
                        {user.email}
                    </p>

                    <div className="mt-3 flex flex-wrap gap-2">
                        <RoleBadge role={user.role} />
                        <StatusBadge active={active} />
                    </div>
                </div>
            </div>
        </article>
    );
}

function RoleBadge({ role }: { role: string }) {
    const className =
        role === "teacher"
            ? "bg-blue-50 text-blue-700"
            : role === "student"
                ? "bg-emerald-50 text-emerald-700"
                : role === "school_admin"
                    ? "bg-violet-50 text-violet-700"
                    : role === "platform_admin"
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 text-slate-700";

    return (
        <span
            className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${className}`}
        >
            {formatRole(role)}
        </span>
    );
}

function StatusBadge({ active }: { active: boolean }) {
    return (
        <span
            className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${active
                ? "bg-emerald-50 text-emerald-700"
                : "bg-slate-100 text-slate-600"
                }`}
        >
            {active ? "Active" : "Inactive"}
        </span>
    );
}

function EmptyUsersState({
    hasActiveFilters,
    onClearFilters,
}: {
    hasActiveFilters: boolean;
    onClearFilters: () => void;
}) {
    return (
        <div className="px-6 py-14 text-center">
            <Users
                aria-hidden="true"
                className="mx-auto h-10 w-10 text-slate-400"
            />

            <h3 className="mt-4 text-lg font-extrabold text-slate-900">
                {hasActiveFilters
                    ? "No matching users"
                    : "No users found"}
            </h3>

            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                {hasActiveFilters
                    ? "Try changing the search term or filters to find the user you need."
                    : "Create the first school user to begin building your directory."}
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
                        Create User
                    </Link>
                )}
            </div>
        </div>
    );
}

function UsersPageSkeleton() {
    return (
        <section
            aria-label="Loading school users"
            className="mt-8"
        >
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map(
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
                    <div className="h-6 w-40 animate-pulse rounded bg-slate-200" />
                    <div className="mt-2 h-4 w-64 max-w-full animate-pulse rounded bg-slate-100" />
                    <div className="mt-5 grid gap-3 sm:grid-cols-3">
                        {Array.from({ length: 3 }).map(
                            (_, index) => (
                                <div
                                    key={index}
                                    className="h-11 animate-pulse rounded-xl bg-slate-100"
                                />
                            ),
                        )}
                    </div>
                </div>

                <div className="divide-y divide-slate-100">
                    {Array.from({ length: 6 }).map(
                        (_, index) => (
                            <div
                                key={index}
                                className="flex items-center gap-4 p-6"
                            >
                                <div className="h-10 w-10 animate-pulse rounded-full bg-slate-100" />
                                <div className="flex-1">
                                    <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
                                    <div className="mt-2 h-3 w-56 max-w-full animate-pulse rounded bg-slate-100" />
                                </div>
                            </div>
                        ),
                    )}
                </div>
            </div>
        </section>
    );
}
