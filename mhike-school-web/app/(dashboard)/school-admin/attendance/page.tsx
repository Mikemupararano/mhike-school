"use client";

import Link from "next/link";
import {
    useCallback,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import {
    CalendarDays,
    CheckCircle2,
    Clock3,
    RefreshCw,
    Search,
    ShieldAlert,
    TrendingUp,
    UserRoundCheck,
    UsersRound,
} from "lucide-react";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";

type RegisterSummary = {
    session_id: number;
    class_group_id: number;
    class_name: string | null;
    session_date: string;
    session_type: string;
    is_submitted: boolean;
    total_records: number;
};

type ClassSummary = {
    class_group_id: number;
    class_name: string | null;
    total_records: number;
    present: number;
    late: number;
    authorised_absence: number;
    unauthorised_absence: number;
};

type AttendanceDashboardSummary = {
    school_id: number;
    summary_date: string;
    total_records: number;
    submitted_registers: number;
    unsubmitted_registers: number;
    present: number;
    late: number;
    authorised_absence: number;
    unauthorised_absence: number;
    registers: RegisterSummary[];
    classes: ClassSummary[];
};

type AttendanceTrendPoint = {
    trend_date: string;
    total_records: number;
    present: number;
    late: number;
    authorised_absence: number;
    unauthorised_absence: number;
    attendance_percentage: number;
};

type AttendanceTrendSummary = {
    school_id: number;
    start_date: string;
    end_date: string;
    points: AttendanceTrendPoint[];
};

type RegisterStatusFilter = "all" | "submitted" | "unsubmitted";
type ClassSort = "alphabetical" | "highest" | "lowest";

function getTodayIsoDate(): string {
    return new Date().toISOString().slice(0, 10);
}

function formatDisplayDate(value: string): string {
    const date = new Date(`${value}T00:00:00`);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
    });
}

function getPercentage(value: number, total: number): number {
    if (total <= 0) {
        return 0;
    }

    return Math.round((value / total) * 100);
}

function getAttendancePercentage(
    present: number,
    total: number,
): number {
    if (total <= 0) {
        return 0;
    }

    return Math.round((present / total) * 1000) / 10;
}

function getClassAttendancePercentage(
    classSummary: ClassSummary,
): number {
    return getAttendancePercentage(
        classSummary.present,
        classSummary.total_records,
    );
}

export default function SchoolAdminAttendanceDashboardPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <AttendanceDashboardContent />
        </RoleGate>
    );
}

function AttendanceDashboardContent() {
    const [summaryDate, setSummaryDate] = useState(getTodayIsoDate());
    const [summary, setSummary] =
        useState<AttendanceDashboardSummary | null>(null);
    const [trends, setTrends] =
        useState<AttendanceTrendSummary | null>(null);

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [registerSearch, setRegisterSearch] = useState("");
    const [registerStatusFilter, setRegisterStatusFilter] =
        useState<RegisterStatusFilter>("all");
    const [classSort, setClassSort] =
        useState<ClassSort>("alphabetical");

    const loadAttendance = useCallback(
        async (options?: { refresh?: boolean }) => {
            try {
                if (options?.refresh) {
                    setRefreshing(true);
                } else {
                    setLoading(true);
                }

                setError(null);

                const [summaryResponse, trendResponse] =
                    await Promise.all([
                        fetch(
                            `/api/v1/attendance-dashboard/summary?summary_date=${encodeURIComponent(
                                summaryDate,
                            )}`,
                            { credentials: "include" },
                        ),
                        fetch(
                            "/api/v1/attendance-trends/summary",
                            { credentials: "include" },
                        ),
                    ]);

                if (!summaryResponse.ok) {
                    throw new Error(
                        "Failed to load attendance dashboard.",
                    );
                }

                if (!trendResponse.ok) {
                    throw new Error(
                        "Failed to load attendance trends.",
                    );
                }

                const [
                    summaryData,
                    trendData,
                ] = (await Promise.all([
                    summaryResponse.json(),
                    trendResponse.json(),
                ])) as [
                        AttendanceDashboardSummary,
                        AttendanceTrendSummary,
                    ];

                setSummary(summaryData);
                setTrends(trendData);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load attendance dashboard.",
                );
            } finally {
                setLoading(false);
                setRefreshing(false);
            }
        },
        [summaryDate],
    );

    useEffect(() => {
        void loadAttendance();
    }, [loadAttendance]);

    const attendanceBreakdown = useMemo(() => {
        if (!summary) {
            return [];
        }

        return [
            {
                label: "Present",
                value: summary.present,
                barClass: "bg-green-500",
            },
            {
                label: "Late",
                value: summary.late,
                barClass: "bg-amber-500",
            },
            {
                label: "Authorised absence",
                value: summary.authorised_absence,
                barClass: "bg-blue-500",
            },
            {
                label: "Unauthorised absence",
                value: summary.unauthorised_absence,
                barClass: "bg-red-500",
            },
        ];
    }, [summary]);

    const overallAttendance = useMemo(() => {
        if (!summary) {
            return 0;
        }

        return getAttendancePercentage(
            summary.present,
            summary.total_records,
        );
    }, [summary]);

    const totalRegisters =
        (summary?.submitted_registers ?? 0) +
        (summary?.unsubmitted_registers ?? 0);

    const registerCompletion = getPercentage(
        summary?.submitted_registers ?? 0,
        totalRegisters,
    );

    const filteredRegisters = useMemo(() => {
        if (!summary) {
            return [];
        }

        const query = registerSearch.trim().toLowerCase();

        return summary.registers.filter((register) => {
            const className =
                register.class_name ??
                `Class ${register.class_group_id}`;

            const matchesSearch =
                query.length === 0 ||
                className.toLowerCase().includes(query) ||
                register.session_type
                    .toLowerCase()
                    .includes(query);

            const matchesStatus =
                registerStatusFilter === "all" ||
                (registerStatusFilter === "submitted"
                    ? register.is_submitted
                    : !register.is_submitted);

            return matchesSearch && matchesStatus;
        });
    }, [
        registerSearch,
        registerStatusFilter,
        summary,
    ]);

    const sortedClasses = useMemo(() => {
        if (!summary) {
            return [];
        }

        const classes = [...summary.classes];

        if (classSort === "highest") {
            return classes.sort(
                (first, second) =>
                    getClassAttendancePercentage(second) -
                    getClassAttendancePercentage(first),
            );
        }

        if (classSort === "lowest") {
            return classes.sort(
                (first, second) =>
                    getClassAttendancePercentage(first) -
                    getClassAttendancePercentage(second),
            );
        }

        return classes.sort((first, second) =>
            (
                first.class_name ??
                `Class ${first.class_group_id}`
            ).localeCompare(
                second.class_name ??
                `Class ${second.class_group_id}`,
                "en-GB",
            ),
        );
    }, [classSort, summary]);

    const hasRegisterFilters =
        registerSearch.trim().length > 0 ||
        registerStatusFilter !== "all";

    function clearRegisterFilters() {
        setRegisterSearch("");
        setRegisterStatusFilter("all");
    }

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
                <header className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-700">
                            School administration
                        </p>

                        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                            Attendance Overview
                        </h1>

                        <p className="mt-2 max-w-3xl text-base text-slate-600 sm:text-lg">
                            Monitor register completion, attendance
                            patterns, class performance and daily
                            attendance trends.
                        </p>
                    </div>

                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                        <label className="grid gap-1.5">
                            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                Summary date
                            </span>

                            <span className="relative">
                                <CalendarDays
                                    aria-hidden="true"
                                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                                />

                                <input
                                    type="date"
                                    value={summaryDate}
                                    onChange={(event) =>
                                        setSummaryDate(
                                            event.target.value,
                                        )
                                    }
                                    max={getTodayIsoDate()}
                                    className="rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm font-semibold text-slate-700 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                />
                            </span>
                        </label>

                        <button
                            type="button"
                            onClick={() =>
                                void loadAttendance({
                                    refresh: true,
                                })
                            }
                            disabled={loading || refreshing}
                            data-custom-button="true"
                            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
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
                    </div>
                </header>

                <div
                    className="sr-only"
                    role="status"
                    aria-live="polite"
                >
                    {loading
                        ? "Loading attendance dashboard."
                        : summary
                            ? `Attendance dashboard loaded for ${formatDisplayDate(
                                summaryDate,
                            )}.`
                            : "No attendance summary available."}
                </div>

                {error && (
                    <div
                        role="alert"
                        className="mt-6 flex flex-col gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:flex-row sm:items-center sm:justify-between"
                    >
                        <span className="font-medium">
                            {error}
                        </span>

                        <button
                            type="button"
                            onClick={() =>
                                void loadAttendance()
                            }
                            disabled={loading}
                            data-custom-button="true"
                            className="w-fit rounded-xl border border-red-300 bg-white px-4 py-2 font-bold text-red-700 transition hover:bg-red-100 disabled:opacity-60"
                        >
                            Retry
                        </button>
                    </div>
                )}

                {loading ? (
                    <AttendanceLoadingState />
                ) : !summary ? (
                    <EmptyDashboardState
                        onRetry={() =>
                            void loadAttendance()
                        }
                    />
                ) : (
                    <>
                        <section className="mt-8 rounded-2xl border border-blue-100 bg-blue-50 px-5 py-4">
                            <p className="text-sm font-bold text-blue-800">
                                Summary for{" "}
                                {formatDisplayDate(summaryDate)}
                            </p>

                            <p className="mt-1 text-sm text-blue-700">
                                Figures below reflect attendance
                                records and register completion for
                                the selected date.
                            </p>
                        </section>

                        <section
                            aria-label="Attendance summary"
                            className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5"
                        >
                            <MetricCard
                                title="Attendance"
                                value={`${overallAttendance}%`}
                                note={`${summary.present} present`}
                                icon={
                                    <TrendingUp className="h-6 w-6" />
                                }
                                iconClass="bg-blue-50 text-blue-700"
                            />

                            <MetricCard
                                title="Present"
                                value={summary.present}
                                note={`${getPercentage(
                                    summary.present,
                                    summary.total_records,
                                )}% of records`}
                                icon={
                                    <UserRoundCheck className="h-6 w-6" />
                                }
                                iconClass="bg-green-50 text-green-700"
                            />

                            <MetricCard
                                title="Late"
                                value={summary.late}
                                note={`${getPercentage(
                                    summary.late,
                                    summary.total_records,
                                )}% of records`}
                                icon={
                                    <Clock3 className="h-6 w-6" />
                                }
                                iconClass="bg-amber-50 text-amber-700"
                            />

                            <MetricCard
                                title="Authorised"
                                value={summary.authorised_absence}
                                note={`${getPercentage(
                                    summary.authorised_absence,
                                    summary.total_records,
                                )}% of records`}
                                icon={
                                    <CheckCircle2 className="h-6 w-6" />
                                }
                                iconClass="bg-cyan-50 text-cyan-700"
                            />

                            <MetricCard
                                title="Unauthorised"
                                value={summary.unauthorised_absence}
                                note={`${getPercentage(
                                    summary.unauthorised_absence,
                                    summary.total_records,
                                )}% of records`}
                                icon={
                                    <ShieldAlert className="h-6 w-6" />
                                }
                                iconClass="bg-red-50 text-red-700"
                            />
                        </section>

                        <section className="mt-6 grid gap-6 xl:grid-cols-3">
                            <DashboardPanel
                                title="Attendance Breakdown"
                                description="Distribution of attendance marks for the selected date."
                            >
                                <div className="space-y-5">
                                    {attendanceBreakdown.map(
                                        (item) => (
                                            <PercentageBar
                                                key={item.label}
                                                label={item.label}
                                                value={item.value}
                                                total={
                                                    summary.total_records
                                                }
                                                colorClass={
                                                    item.barClass
                                                }
                                            />
                                        ),
                                    )}
                                </div>
                            </DashboardPanel>

                            <DashboardPanel
                                title="Register Completion"
                                description="Submission progress for registers scheduled on this date."
                            >
                                <div className="space-y-5">
                                    <PercentageBar
                                        label="Submitted"
                                        value={
                                            summary.submitted_registers
                                        }
                                        total={totalRegisters}
                                        colorClass="bg-green-500"
                                    />

                                    <PercentageBar
                                        label="Unsubmitted"
                                        value={
                                            summary.unsubmitted_registers
                                        }
                                        total={totalRegisters}
                                        colorClass="bg-orange-500"
                                    />

                                    <div className="rounded-xl bg-slate-50 p-4">
                                        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                            Completion rate
                                        </p>

                                        <p className="mt-2 text-3xl font-extrabold text-slate-950">
                                            {registerCompletion}%
                                        </p>
                                    </div>
                                </div>
                            </DashboardPanel>

                            <DashboardPanel
                                title="Overall Totals"
                                description="Records and operational coverage for the selected date."
                            >
                                <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                                    <TotalRow
                                        label="Total records"
                                        value={summary.total_records}
                                    />
                                    <TotalRow
                                        label="Classes"
                                        value={
                                            summary.classes.length
                                        }
                                    />
                                    <TotalRow
                                        label="Registers"
                                        value={
                                            summary.registers.length
                                        }
                                    />
                                </div>
                            </DashboardPanel>
                        </section>

                        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        Attendance Trends
                                    </h2>

                                    <p className="mt-1 text-sm text-slate-500">
                                        Daily attendance percentages
                                        across the available trend
                                        period.
                                    </p>
                                </div>

                                {trends && (
                                    <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                                        {formatDisplayDate(
                                            trends.start_date,
                                        )}{" "}
                                        –{" "}
                                        {formatDisplayDate(
                                            trends.end_date,
                                        )}
                                    </span>
                                )}
                            </div>

                            {!trends ||
                                trends.points.length === 0 ? (
                                <InlineEmptyState
                                    icon={
                                        <TrendingUp className="h-8 w-8" />
                                    }
                                    title="No trend data"
                                    description="No attendance trend data is available for the current period."
                                />
                            ) : (
                                <div className="mt-8 overflow-x-auto pb-2">
                                    <div className="flex min-w-[700px] items-end gap-3">
                                        {trends.points.map(
                                            (point) => (
                                                <div
                                                    key={
                                                        point.trend_date
                                                    }
                                                    className="flex min-w-[64px] flex-1 flex-col items-center"
                                                >
                                                    <div className="mb-2 text-xs font-extrabold text-slate-700">
                                                        {
                                                            point.attendance_percentage
                                                        }
                                                        %
                                                    </div>

                                                    <div className="flex h-52 w-full items-end rounded-xl bg-slate-100 p-1">
                                                        <div
                                                            className="w-full rounded-lg bg-blue-500 transition-all"
                                                            style={{
                                                                height: `${Math.max(
                                                                    point.attendance_percentage,
                                                                    4,
                                                                )}%`,
                                                            }}
                                                            aria-label={`${point.trend_date}: ${point.attendance_percentage}% attendance`}
                                                        />
                                                    </div>

                                                    <div className="mt-2 text-center text-xs font-medium text-slate-500">
                                                        {new Date(
                                                            `${point.trend_date}T00:00:00`,
                                                        ).toLocaleDateString(
                                                            "en-GB",
                                                            {
                                                                day: "2-digit",
                                                                month: "short",
                                                            },
                                                        )}
                                                    </div>
                                                </div>
                                            ),
                                        )}
                                    </div>
                                </div>
                            )}
                        </section>

                        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        Registers
                                    </h2>

                                    <p className="mt-1 text-sm text-slate-500">
                                        Review register status and
                                        open individual sessions.
                                    </p>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2">
                                    <label className="grid gap-1.5">
                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                            Search
                                        </span>

                                        <span className="relative">
                                            <Search
                                                aria-hidden="true"
                                                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                                            />

                                            <input
                                                type="search"
                                                value={
                                                    registerSearch
                                                }
                                                onChange={(
                                                    event,
                                                ) =>
                                                    setRegisterSearch(
                                                        event
                                                            .target
                                                            .value,
                                                    )
                                                }
                                                placeholder="Class or session..."
                                                className="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                            />
                                        </span>
                                    </label>

                                    <label className="grid gap-1.5">
                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                            Status
                                        </span>

                                        <select
                                            value={
                                                registerStatusFilter
                                            }
                                            onChange={(
                                                event,
                                            ) =>
                                                setRegisterStatusFilter(
                                                    event
                                                        .target
                                                        .value as RegisterStatusFilter,
                                                )
                                            }
                                            className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                        >
                                            <option value="all">
                                                All registers
                                            </option>
                                            <option value="submitted">
                                                Submitted
                                            </option>
                                            <option value="unsubmitted">
                                                Not submitted
                                            </option>
                                        </select>
                                    </label>
                                </div>
                            </div>

                            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
                                <p className="text-sm font-medium text-slate-600">
                                    Showing{" "}
                                    <span className="font-extrabold text-slate-950">
                                        {
                                            filteredRegisters.length
                                        }
                                    </span>{" "}
                                    of{" "}
                                    <span className="font-extrabold text-slate-950">
                                        {
                                            summary.registers
                                                .length
                                        }
                                    </span>{" "}
                                    registers
                                </p>

                                {hasRegisterFilters && (
                                    <button
                                        type="button"
                                        onClick={
                                            clearRegisterFilters
                                        }
                                        data-custom-button="true"
                                        className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                                    >
                                        Clear filters
                                    </button>
                                )}
                            </div>

                            {filteredRegisters.length === 0 ? (
                                <InlineEmptyState
                                    icon={
                                        <CalendarDays className="h-8 w-8" />
                                    }
                                    title={
                                        hasRegisterFilters
                                            ? "No matching registers"
                                            : "No registers found"
                                    }
                                    description={
                                        hasRegisterFilters
                                            ? "No registers match the current search and status filter."
                                            : "No registers were found for the selected date."
                                    }
                                />
                            ) : (
                                <>
                                    <div className="mt-5 hidden overflow-x-auto md:block">
                                        <table className="w-full text-left text-sm">
                                            <thead className="border-b border-slate-200 text-xs font-bold uppercase tracking-wide text-slate-500">
                                                <tr>
                                                    <th className="px-3 py-3">
                                                        Class
                                                    </th>
                                                    <th className="px-3 py-3">
                                                        Session
                                                    </th>
                                                    <th className="px-3 py-3">
                                                        Records
                                                    </th>
                                                    <th className="px-3 py-3">
                                                        Status
                                                    </th>
                                                    <th className="px-3 py-3 text-right">
                                                        Action
                                                    </th>
                                                </tr>
                                            </thead>

                                            <tbody>
                                                {filteredRegisters.map(
                                                    (
                                                        register,
                                                    ) => (
                                                        <RegisterTableRow
                                                            key={
                                                                register.session_id
                                                            }
                                                            register={
                                                                register
                                                            }
                                                        />
                                                    ),
                                                )}
                                            </tbody>
                                        </table>
                                    </div>

                                    <div className="mt-5 grid gap-3 md:hidden">
                                        {filteredRegisters.map(
                                            (register) => (
                                                <RegisterCard
                                                    key={
                                                        register.session_id
                                                    }
                                                    register={
                                                        register
                                                    }
                                                />
                                            ),
                                        )}
                                    </div>
                                </>
                            )}
                        </section>

                        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        Attendance by Class
                                    </h2>

                                    <p className="mt-1 text-sm text-slate-500">
                                        Compare attendance outcomes
                                        across classes for the selected
                                        date.
                                    </p>
                                </div>

                                <label className="grid gap-1.5">
                                    <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                        Sort classes
                                    </span>

                                    <select
                                        value={classSort}
                                        onChange={(event) =>
                                            setClassSort(
                                                event.target
                                                    .value as ClassSort,
                                            )
                                        }
                                        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                    >
                                        <option value="alphabetical">
                                            Alphabetical
                                        </option>
                                        <option value="highest">
                                            Highest attendance
                                        </option>
                                        <option value="lowest">
                                            Lowest attendance
                                        </option>
                                    </select>
                                </label>
                            </div>

                            {sortedClasses.length === 0 ? (
                                <InlineEmptyState
                                    icon={
                                        <UsersRound className="h-8 w-8" />
                                    }
                                    title="No class data"
                                    description="No class attendance data was found for the selected date."
                                />
                            ) : (
                                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                                    {sortedClasses.map(
                                        (classSummary) => (
                                            <ClassAttendanceCard
                                                key={
                                                    classSummary.class_group_id
                                                }
                                                classSummary={
                                                    classSummary
                                                }
                                            />
                                        ),
                                    )}
                                </div>
                            )}
                        </section>
                    </>
                )}
            </div>
        </main>
    );
}

function MetricCard({
    title,
    value,
    note,
    icon,
    iconClass,
}: {
    title: string;
    value: number | string;
    note: string;
    icon: ReactNode;
    iconClass: string;
}) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="text-sm font-bold text-slate-500">
                        {title}
                    </p>

                    <p className="mt-3 text-3xl font-extrabold text-slate-950">
                        {value}
                    </p>

                    <p className="mt-1 text-xs font-medium text-slate-500">
                        {note}
                    </p>
                </div>

                <div
                    aria-hidden="true"
                    className={`rounded-xl p-3 ${iconClass}`}
                >
                    {icon}
                </div>
            </div>
        </article>
    );
}

function DashboardPanel({
    title,
    description,
    children,
}: {
    title: string;
    description: string;
    children: ReactNode;
}) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-bold text-slate-950">
                {title}
            </h2>

            <p className="mt-1 text-sm leading-6 text-slate-500">
                {description}
            </p>

            <div className="mt-6">{children}</div>
        </article>
    );
}

function PercentageBar({
    label,
    value,
    total,
    colorClass,
}: {
    label: string;
    value: number;
    total: number;
    colorClass: string;
}) {
    const percentage = getPercentage(value, total);

    return (
        <div>
            <div className="mb-2 flex items-center justify-between gap-3 text-sm font-semibold">
                <span className="text-slate-700">
                    {label}
                </span>

                <span className="text-slate-950">
                    {value}{" "}
                    <span className="text-slate-500">
                        ({percentage}%)
                    </span>
                </span>
            </div>

            <div
                className="h-3 overflow-hidden rounded-full bg-slate-200"
                role="progressbar"
                aria-label={label}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percentage}
            >
                <div
                    className={`h-full rounded-full transition-all ${colorClass}`}
                    style={{
                        width: `${Math.min(
                            percentage,
                            100,
                        )}%`,
                    }}
                />
            </div>
        </div>
    );
}

function TotalRow({
    label,
    value,
}: {
    label: string;
    value: number;
}) {
    return (
        <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {label}
            </p>

            <p className="mt-2 text-3xl font-extrabold text-slate-950">
                {value}
            </p>
        </div>
    );
}

function RegisterTableRow({
    register,
}: {
    register: RegisterSummary;
}) {
    const className =
        register.class_name ??
        `Class ${register.class_group_id}`;

    return (
        <tr className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
            <td className="px-3 py-4 font-bold text-slate-900">
                {className}
            </td>

            <td className="px-3 py-4 font-medium uppercase text-slate-600">
                {register.session_type}
            </td>

            <td className="px-3 py-4 text-slate-600">
                {register.total_records}
            </td>

            <td className="px-3 py-4">
                <StatusBadge
                    submitted={
                        register.is_submitted
                    }
                />
            </td>

            <td className="px-3 py-4 text-right">
                <Link
                    href={`/school-admin/attendance/registers/${register.session_id}`}
                    className="inline-flex rounded-lg px-3 py-2 text-sm font-bold text-blue-700 transition hover:bg-blue-50 hover:text-blue-800"
                >
                    View register
                </Link>
            </td>
        </tr>
    );
}

function RegisterCard({
    register,
}: {
    register: RegisterSummary;
}) {
    const className =
        register.class_name ??
        `Class ${register.class_group_id}`;

    return (
        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h3 className="font-bold text-slate-950">
                        {className}
                    </h3>

                    <p className="mt-1 text-sm font-medium uppercase text-slate-500">
                        {register.session_type}
                    </p>
                </div>

                <StatusBadge
                    submitted={register.is_submitted}
                />
            </div>

            <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-4">
                <span className="text-sm font-medium text-slate-600">
                    {register.total_records} records
                </span>

                <Link
                    href={`/school-admin/attendance/registers/${register.session_id}`}
                    className="rounded-lg px-3 py-2 text-sm font-bold text-blue-700 transition hover:bg-blue-50"
                >
                    View register
                </Link>
            </div>
        </article>
    );
}

function StatusBadge({
    submitted,
}: {
    submitted: boolean;
}) {
    return (
        <span
            className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${submitted
                ? "bg-green-100 text-green-700"
                : "bg-orange-100 text-orange-700"
                }`}
        >
            {submitted
                ? "Submitted"
                : "Not submitted"}
        </span>
    );
}

function ClassAttendanceCard({
    classSummary,
}: {
    classSummary: ClassSummary;
}) {
    const className =
        classSummary.class_name ??
        `Class ${classSummary.class_group_id}`;

    const attendancePercentage =
        getClassAttendancePercentage(
            classSummary,
        );

    return (
        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-blue-200 hover:bg-white hover:shadow-md">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h3 className="text-lg font-bold text-slate-950">
                        {className}
                    </h3>

                    <p className="mt-1 text-sm text-slate-500">
                        {classSummary.total_records} records
                    </p>
                </div>

                <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-extrabold text-blue-700">
                    {attendancePercentage}% attendance
                </span>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <PercentageBar
                    label="Present"
                    value={classSummary.present}
                    total={classSummary.total_records}
                    colorClass="bg-green-500"
                />

                <PercentageBar
                    label="Late"
                    value={classSummary.late}
                    total={classSummary.total_records}
                    colorClass="bg-amber-500"
                />

                <PercentageBar
                    label="Authorised"
                    value={
                        classSummary.authorised_absence
                    }
                    total={classSummary.total_records}
                    colorClass="bg-blue-500"
                />

                <PercentageBar
                    label="Unauthorised"
                    value={
                        classSummary.unauthorised_absence
                    }
                    total={classSummary.total_records}
                    colorClass="bg-red-500"
                />
            </div>
        </article>
    );
}

function InlineEmptyState({
    icon,
    title,
    description,
}: {
    icon: ReactNode;
    title: string;
    description: string;
}) {
    return (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
            <div
                aria-hidden="true"
                className="mx-auto w-fit text-slate-400"
            >
                {icon}
            </div>

            <h3 className="mt-4 text-lg font-bold text-slate-950">
                {title}
            </h3>

            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                {description}
            </p>
        </div>
    );
}

function EmptyDashboardState({
    onRetry,
}: {
    onRetry: () => void;
}) {
    return (
        <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center shadow-sm">
            <CalendarDays
                className="mx-auto h-12 w-12 text-slate-400"
                aria-hidden="true"
            />

            <h2 className="mt-4 text-xl font-bold text-slate-950">
                No attendance summary found
            </h2>

            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                No attendance data is available for the selected
                date. Try refreshing or choose another date.
            </p>

            <button
                type="button"
                onClick={onRetry}
                data-custom-button="true"
                className="mt-5 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-blue-800"
            >
                Retry
            </button>
        </section>
    );
}

function AttendanceLoadingState() {
    return (
        <div
            className="mt-8 space-y-6"
            aria-hidden="true"
        >
            <div className="h-20 animate-pulse rounded-2xl border border-slate-200 bg-white" />

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                {Array.from({ length: 5 }).map(
                    (_, index) => (
                        <div
                            key={index}
                            className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white"
                        />
                    ),
                )}
            </div>

            <div className="grid gap-6 xl:grid-cols-3">
                {Array.from({ length: 3 }).map(
                    (_, index) => (
                        <div
                            key={index}
                            className="h-72 animate-pulse rounded-2xl border border-slate-200 bg-white"
                        />
                    ),
                )}
            </div>

            <div className="h-80 animate-pulse rounded-2xl border border-slate-200 bg-white" />

            <div className="h-96 animate-pulse rounded-2xl border border-slate-200 bg-white" />
        </div>
    );
}
