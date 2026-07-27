"use client";

import {
    ArrowLeft,
    BookOpen,
    CalendarDays,
    ChevronDown,
    ChevronUp,
    ClipboardCheck,
    FileText,
    GraduationCap,
    Loader2,
    Mail,
    RefreshCw,
    Search,
    TriangleAlert,
    UserRound,
    Users,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";

const TOKEN_STORAGE_KEY = "mhike_token";
const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

type ClassSummary = {
    id: number;
    name: string;
    code?: string | null;
    subject_name?: string | null;
    year_group?: string | null;
    academic_year?: string | null;
    teacher_name?: string | null;
    room?: string | null;
    schedule_summary?: string | null;
    student_count?: number | null;
};

type ClassStudent = {
    id: number;
    first_name: string;
    last_name: string;
    email?: string | null;
    admission_number?: string | null;
    year_group?: string | null;
    attendance_percentage?: number | null;
    current_grade?: string | null;
    target_grade?: string | null;
    outstanding_reports?: number | null;
};

type ClassDetailResponse = {
    class: ClassSummary;
    students: ClassStudent[];
};

type SortKey =
    | "name"
    | "attendance"
    | "currentGrade"
    | "targetGrade";

type SortDirection = "asc" | "desc";

function getApiBaseUrl(): string {
    const configured =
        process.env.NEXT_PUBLIC_API_BASE_URL ??
        process.env.NEXT_PUBLIC_API_URL;

    return (configured?.trim() || DEFAULT_API_BASE_URL).replace(
        /\/+$/,
        "",
    );
}

function getAuthToken(): string {
    const token = window.sessionStorage.getItem(
        TOKEN_STORAGE_KEY,
    );

    if (!token) {
        throw new Error(
            "Your session has expired. Please sign in again.",
        );
    }

    return token;
}

async function requestJson<T>(path: string): Promise<T> {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${getAuthToken()}`,
            Accept: "application/json",
        },
        cache: "no-store",
    });

    if (!response.ok) {
        let message = `Request failed (${response.status}).`;

        try {
            const body = (await response.json()) as {
                detail?: unknown;
            };

            if (
                typeof body.detail === "string" &&
                body.detail.trim()
            ) {
                message = body.detail;
            }
        } catch {
            // Keep the HTTP fallback for non-JSON responses.
        }

        throw new Error(message);
    }

    return (await response.json()) as T;
}

function normaliseClassDetail(
    payload: unknown,
): ClassDetailResponse {
    if (
        typeof payload !== "object" ||
        payload === null
    ) {
        throw new Error("The class response was invalid.");
    }

    const value = payload as Record<string, unknown>;
    const rawClass =
        (value.class as Record<string, unknown> | undefined) ??
        (value.class_detail as
            | Record<string, unknown>
            | undefined) ??
        value;

    const rawStudents = Array.isArray(value.students)
        ? value.students
        : Array.isArray(value.members)
            ? value.members
            : [];

    const classId = Number(rawClass.id);

    if (!Number.isInteger(classId) || classId <= 0) {
        throw new Error("The class response did not include a valid ID.");
    }

    const classSummary: ClassSummary = {
        id: classId,
        name:
            typeof rawClass.name === "string" &&
                rawClass.name.trim()
                ? rawClass.name
                : `Class ${classId}`,
        code:
            typeof rawClass.code === "string"
                ? rawClass.code
                : null,
        subject_name:
            typeof rawClass.subject_name === "string"
                ? rawClass.subject_name
                : typeof rawClass.subject === "string"
                    ? rawClass.subject
                    : null,
        year_group:
            typeof rawClass.year_group === "string"
                ? rawClass.year_group
                : null,
        academic_year:
            typeof rawClass.academic_year === "string"
                ? rawClass.academic_year
                : null,
        teacher_name:
            typeof rawClass.teacher_name === "string"
                ? rawClass.teacher_name
                : null,
        room:
            typeof rawClass.room === "string"
                ? rawClass.room
                : null,
        schedule_summary:
            typeof rawClass.schedule_summary === "string"
                ? rawClass.schedule_summary
                : null,
        student_count:
            typeof rawClass.student_count === "number"
                ? rawClass.student_count
                : rawStudents.length,
    };

    const students = rawStudents.flatMap((item) => {
        if (
            typeof item !== "object" ||
            item === null
        ) {
            return [];
        }

        const student = item as Record<string, unknown>;
        const id = Number(
            student.id ?? student.student_id,
        );

        if (!Number.isInteger(id) || id <= 0) {
            return [];
        }

        const fullName =
            typeof student.name === "string"
                ? student.name.trim()
                : "";

        const nameParts = fullName
            ? fullName.split(/\s+/)
            : [];

        const firstName =
            typeof student.first_name === "string"
                ? student.first_name
                : nameParts[0] ?? "Student";

        const lastName =
            typeof student.last_name === "string"
                ? student.last_name
                : nameParts.slice(1).join(" ");

        return [
            {
                id,
                first_name: firstName,
                last_name: lastName,
                email:
                    typeof student.email === "string"
                        ? student.email
                        : null,
                admission_number:
                    typeof student.admission_number ===
                        "string"
                        ? student.admission_number
                        : null,
                year_group:
                    typeof student.year_group === "string"
                        ? student.year_group
                        : null,
                attendance_percentage:
                    typeof student.attendance_percentage ===
                        "number"
                        ? student.attendance_percentage
                        : null,
                current_grade:
                    typeof student.current_grade === "string"
                        ? student.current_grade
                        : typeof student.grade === "string"
                            ? student.grade
                            : null,
                target_grade:
                    typeof student.target_grade === "string"
                        ? student.target_grade
                        : null,
                outstanding_reports:
                    typeof student.outstanding_reports ===
                        "number"
                        ? student.outstanding_reports
                        : null,
            } satisfies ClassStudent,
        ];
    });

    return {
        class: classSummary,
        students,
    };
}

function getStudentName(student: ClassStudent): string {
    return `${student.first_name} ${student.last_name}`.trim();
}

function formatPercentage(
    value: number | null | undefined,
): string {
    if (
        typeof value !== "number" ||
        Number.isNaN(value)
    ) {
        return "Not available";
    }

    return `${Math.round(value)}%`;
}

function getAttendanceStatus(
    value: number | null | undefined,
): {
    label: string;
    className: string;
} {
    if (
        typeof value !== "number" ||
        Number.isNaN(value)
    ) {
        return {
            label: "No data",
            className:
                "bg-slate-100 text-slate-600 ring-slate-200",
        };
    }

    if (value >= 95) {
        return {
            label: "Strong",
            className:
                "bg-green-50 text-green-700 ring-green-200",
        };
    }

    if (value >= 90) {
        return {
            label: "Monitor",
            className:
                "bg-amber-50 text-amber-700 ring-amber-200",
        };
    }

    return {
        label: "Concern",
        className:
            "bg-red-50 text-red-700 ring-red-200",
    };
}

export default function TeacherClassDetailPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherClassDetailContent />
        </RoleGate>
    );
}

function TeacherClassDetailContent() {
    const router = useRouter();
    const params = useParams<{
        classId?: string | string[];
    }>();

    const rawClassId = Array.isArray(params.classId)
        ? params.classId[0]
        : params.classId;

    const classId = Number(rawClassId);
    const hasValidClassId =
        Number.isInteger(classId) && classId > 0;

    const [classSummary, setClassSummary] =
        useState<ClassSummary | null>(null);
    const [students, setStudents] = useState<
        ClassStudent[]
    >([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(
        null,
    );
    const [searchQuery, setSearchQuery] = useState("");
    const [attendanceFilter, setAttendanceFilter] =
        useState("all");
    const [sortKey, setSortKey] =
        useState<SortKey>("name");
    const [sortDirection, setSortDirection] =
        useState<SortDirection>("asc");

    const loadClass = useCallback(async () => {
        if (!hasValidClassId) {
            setLoading(false);
            setError("The class ID is invalid.");
            return;
        }

        try {
            setLoading(true);
            setError(null);

            let payload: unknown;

            try {
                payload = await requestJson<unknown>(
                    `/classes/${classId}`,
                );
            } catch (primaryError) {
                try {
                    payload = await requestJson<unknown>(
                        `/teacher/classes/${classId}`,
                    );
                } catch {
                    throw primaryError;
                }
            }

            const normalised =
                normaliseClassDetail(payload);

            setClassSummary(normalised.class);
            setStudents(normalised.students);
        } catch (err) {
            setClassSummary(null);
            setStudents([]);
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load class details.",
            );
        } finally {
            setLoading(false);
        }
    }, [classId, hasValidClassId]);

    useEffect(() => {
        void loadClass();
    }, [loadClass]);

    const filteredStudents = useMemo(() => {
        const query = searchQuery
            .trim()
            .toLocaleLowerCase("en-GB");

        const filtered = students.filter((student) => {
            const searchableText = [
                getStudentName(student),
                student.email ?? "",
                student.admission_number ?? "",
                student.year_group ?? "",
                student.current_grade ?? "",
                student.target_grade ?? "",
            ]
                .join(" ")
                .toLocaleLowerCase("en-GB");

            const matchesSearch =
                !query || searchableText.includes(query);

            const attendance =
                student.attendance_percentage;

            const matchesAttendance =
                attendanceFilter === "all" ||
                (attendanceFilter === "strong" &&
                    typeof attendance === "number" &&
                    attendance >= 95) ||
                (attendanceFilter === "monitor" &&
                    typeof attendance === "number" &&
                    attendance >= 90 &&
                    attendance < 95) ||
                (attendanceFilter === "concern" &&
                    typeof attendance === "number" &&
                    attendance < 90) ||
                (attendanceFilter === "unknown" &&
                    typeof attendance !== "number");

            return matchesSearch && matchesAttendance;
        });

        return [...filtered].sort((first, second) => {
            let comparison = 0;

            if (sortKey === "name") {
                comparison = getStudentName(first).localeCompare(
                    getStudentName(second),
                    "en-GB",
                    {
                        sensitivity: "base",
                    },
                );
            }

            if (sortKey === "attendance") {
                comparison =
                    (first.attendance_percentage ?? -1) -
                    (second.attendance_percentage ?? -1);
            }

            if (sortKey === "currentGrade") {
                comparison = (
                    first.current_grade ?? ""
                ).localeCompare(
                    second.current_grade ?? "",
                    "en-GB",
                    {
                        numeric: true,
                    },
                );
            }

            if (sortKey === "targetGrade") {
                comparison = (
                    first.target_grade ?? ""
                ).localeCompare(
                    second.target_grade ?? "",
                    "en-GB",
                    {
                        numeric: true,
                    },
                );
            }

            return sortDirection === "asc"
                ? comparison
                : -comparison;
        });
    }, [
        attendanceFilter,
        searchQuery,
        sortDirection,
        sortKey,
        students,
    ]);

    const averageAttendance = useMemo(() => {
        const values = students
            .map(
                (student) =>
                    student.attendance_percentage,
            )
            .filter(
                (value): value is number =>
                    typeof value === "number" &&
                    !Number.isNaN(value),
            );

        if (values.length === 0) {
            return null;
        }

        return (
            values.reduce(
                (total, value) => total + value,
                0,
            ) / values.length
        );
    }, [students]);

    const studentsOfConcern = useMemo(
        () =>
            students.filter(
                (student) =>
                    typeof student.attendance_percentage ===
                    "number" &&
                    student.attendance_percentage < 90,
            ).length,
        [students],
    );

    const outstandingReports = useMemo(
        () =>
            students.reduce(
                (total, student) =>
                    total +
                    (student.outstanding_reports ?? 0),
                0,
            ),
        [students],
    );

    function toggleSort(nextSortKey: SortKey) {
        if (sortKey === nextSortKey) {
            setSortDirection((current) =>
                current === "asc" ? "desc" : "asc",
            );
            return;
        }

        setSortKey(nextSortKey);
        setSortDirection("asc");
    }

    if (loading) {
        return <ClassDetailLoadingState />;
    }

    if (!classSummary) {
        return (
            <main className="min-h-full bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
                <div className="mx-auto max-w-5xl">
                    <section
                        role="alert"
                        className="rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm"
                    >
                        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-700">
                            <TriangleAlert
                                aria-hidden="true"
                                className="h-6 w-6"
                            />
                        </div>

                        <h1 className="mt-4 text-2xl font-extrabold text-slate-950">
                            Class unavailable
                        </h1>

                        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">
                            {error ??
                                "The requested class could not be found."}
                        </p>

                        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
                            {hasValidClassId && (
                                <button
                                    type="button"
                                    onClick={() =>
                                        void loadClass()
                                    }
                                    data-custom-button="true"
                                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-blue-800"
                                >
                                    <RefreshCw
                                        aria-hidden="true"
                                        className="h-4 w-4"
                                    />
                                    Retry
                                </button>
                            )}

                            <button
                                type="button"
                                onClick={() =>
                                    router.push(
                                        "/teacher/classes",
                                    )
                                }
                                data-custom-button="true"
                                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                            >
                                <ArrowLeft
                                    aria-hidden="true"
                                    className="h-4 w-4"
                                />
                                Back to classes
                            </button>
                        </div>
                    </section>
                </div>
            </main>
        );
    }

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
                <header className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                    <div>
                        <button
                            type="button"
                            onClick={() =>
                                router.push(
                                    "/teacher/classes",
                                )
                            }
                            data-custom-button="true"
                            className="inline-flex items-center gap-2 rounded-lg px-2 py-1 text-sm font-bold text-slate-600 transition hover:bg-slate-100 hover:text-slate-950"
                        >
                            <ArrowLeft
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            Back to classes
                        </button>

                        <div className="mt-4 flex items-start gap-4">
                            <div className="hidden rounded-2xl bg-blue-100 p-3 text-blue-700 sm:block">
                                <Users
                                    aria-hidden="true"
                                    className="h-7 w-7"
                                />
                            </div>

                            <div>
                                <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">
                                    Teacher class
                                </p>

                                <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                                    {classSummary.name}
                                </h1>

                                <p className="mt-2 max-w-3xl text-base text-slate-600">
                                    Review students, attendance,
                                    grades and reporting progress
                                    for this class.
                                </p>
                            </div>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={() => void loadClass()}
                        disabled={loading}
                        data-custom-button="true"
                        className="inline-flex w-fit items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {loading ? (
                            <Loader2
                                aria-hidden="true"
                                className="h-4 w-4 animate-spin"
                            />
                        ) : (
                            <RefreshCw
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                        )}
                        Refresh
                    </button>
                </header>

                <section
                    aria-label="Class information"
                    className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
                >
                    <InfoCard
                        icon={BookOpen}
                        label="Subject"
                        value={
                            classSummary.subject_name ??
                            "Not specified"
                        }
                    />
                    <InfoCard
                        icon={GraduationCap}
                        label="Year group"
                        value={
                            classSummary.year_group ??
                            "Not specified"
                        }
                    />
                    <InfoCard
                        icon={CalendarDays}
                        label="Academic year"
                        value={
                            classSummary.academic_year ??
                            "Not specified"
                        }
                    />
                    <InfoCard
                        icon={UserRound}
                        label="Teacher"
                        value={
                            classSummary.teacher_name ??
                            "Not specified"
                        }
                    />
                </section>

                <section
                    aria-label="Class summary"
                    className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
                >
                    <MetricCard
                        label="Students"
                        value={students.length.toString()}
                        hint={
                            classSummary.code
                                ? `Class code: ${classSummary.code}`
                                : "Enrolled learners"
                        }
                    />
                    <MetricCard
                        label="Average attendance"
                        value={formatPercentage(
                            averageAttendance,
                        )}
                        hint="Across available records"
                    />
                    <MetricCard
                        label="Attendance concerns"
                        value={studentsOfConcern.toString()}
                        hint="Below 90%"
                    />
                    <MetricCard
                        label="Outstanding reports"
                        value={outstandingReports.toString()}
                        hint="Across this class"
                    />
                </section>

                <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-slate-950">
                                Quick actions
                            </h2>
                            <p className="mt-1 text-sm text-slate-600">
                                Open the most common teacher
                                workflows for this class.
                            </p>
                        </div>

                        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                            <QuickAction
                                href={`/teacher/attendance?classId=${classSummary.id}`}
                                icon={ClipboardCheck}
                                label="Take attendance"
                            />
                            <QuickAction
                                href={`/teacher/reports?classId=${classSummary.id}`}
                                icon={FileText}
                                label="Open reports"
                            />
                            <QuickAction
                                href={`/messages?classId=${classSummary.id}`}
                                icon={Mail}
                                label="Message class"
                            />
                        </div>
                    </div>
                </section>

                <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <div className="border-b border-slate-200 p-4 sm:p-6">
                        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Students
                                </h2>
                                <p className="mt-1 text-sm text-slate-600">
                                    {filteredStudents.length} of{" "}
                                    {students.length} students shown.
                                </p>
                            </div>

                            <div className="grid gap-3 sm:grid-cols-2">
                                <label className="grid gap-2">
                                    <span className="text-sm font-bold text-slate-700">
                                        Search students
                                    </span>
                                    <div className="relative">
                                        <Search
                                            aria-hidden="true"
                                            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                                        />
                                        <input
                                            value={searchQuery}
                                            onChange={(event) =>
                                                setSearchQuery(
                                                    event.target
                                                        .value,
                                                )
                                            }
                                            placeholder="Name, email or admission number"
                                            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                        />
                                    </div>
                                </label>

                                <label className="grid gap-2">
                                    <span className="text-sm font-bold text-slate-700">
                                        Attendance
                                    </span>
                                    <select
                                        value={
                                            attendanceFilter
                                        }
                                        onChange={(event) =>
                                            setAttendanceFilter(
                                                event.target
                                                    .value,
                                            )
                                        }
                                        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                    >
                                        <option value="all">
                                            All students
                                        </option>
                                        <option value="strong">
                                            Strong: 95%+
                                        </option>
                                        <option value="monitor">
                                            Monitor: 90–94%
                                        </option>
                                        <option value="concern">
                                            Concern: below 90%
                                        </option>
                                        <option value="unknown">
                                            No attendance data
                                        </option>
                                    </select>
                                </label>
                            </div>
                        </div>
                    </div>

                    {students.length === 0 ? (
                        <EmptyStudentsState />
                    ) : filteredStudents.length === 0 ? (
                        <div className="p-8 text-center">
                            <h3 className="text-lg font-bold text-slate-950">
                                No matching students
                            </h3>
                            <p className="mt-2 text-sm text-slate-600">
                                Change the search or attendance
                                filter and try again.
                            </p>
                            <button
                                type="button"
                                onClick={() => {
                                    setSearchQuery("");
                                    setAttendanceFilter(
                                        "all",
                                    );
                                }}
                                data-custom-button="true"
                                className="mt-4 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                            >
                                Clear filters
                            </button>
                        </div>
                    ) : (
                        <>
                            <div className="hidden overflow-x-auto md:block">
                                <table className="min-w-full divide-y divide-slate-200">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <SortableHeader
                                                label="Student"
                                                active={
                                                    sortKey ===
                                                    "name"
                                                }
                                                direction={
                                                    sortDirection
                                                }
                                                onClick={() =>
                                                    toggleSort(
                                                        "name",
                                                    )
                                                }
                                            />
                                            <SortableHeader
                                                label="Attendance"
                                                active={
                                                    sortKey ===
                                                    "attendance"
                                                }
                                                direction={
                                                    sortDirection
                                                }
                                                onClick={() =>
                                                    toggleSort(
                                                        "attendance",
                                                    )
                                                }
                                            />
                                            <SortableHeader
                                                label="Current grade"
                                                active={
                                                    sortKey ===
                                                    "currentGrade"
                                                }
                                                direction={
                                                    sortDirection
                                                }
                                                onClick={() =>
                                                    toggleSort(
                                                        "currentGrade",
                                                    )
                                                }
                                            />
                                            <SortableHeader
                                                label="Target grade"
                                                active={
                                                    sortKey ===
                                                    "targetGrade"
                                                }
                                                direction={
                                                    sortDirection
                                                }
                                                onClick={() =>
                                                    toggleSort(
                                                        "targetGrade",
                                                    )
                                                }
                                            />
                                            <th className="px-5 py-3 text-right text-xs font-bold uppercase tracking-wide text-slate-500">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody className="divide-y divide-slate-100 bg-white">
                                        {filteredStudents.map(
                                            (student) => (
                                                <StudentTableRow
                                                    key={
                                                        student.id
                                                    }
                                                    student={
                                                        student
                                                    }
                                                    classId={
                                                        classSummary.id
                                                    }
                                                />
                                            ),
                                        )}
                                    </tbody>
                                </table>
                            </div>

                            <div className="grid gap-4 p-4 md:hidden">
                                {filteredStudents.map(
                                    (student) => (
                                        <StudentMobileCard
                                            key={student.id}
                                            student={student}
                                            classId={
                                                classSummary.id
                                            }
                                        />
                                    ),
                                )}
                            </div>
                        </>
                    )}
                </section>
            </div>
        </main>
    );
}

function InfoCard({
    icon: Icon,
    label,
    value,
}: {
    icon: typeof BookOpen;
    label: string;
    value: string;
}) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start gap-3">
                <div className="rounded-xl bg-blue-50 p-2.5 text-blue-700">
                    <Icon
                        aria-hidden="true"
                        className="h-5 w-5"
                    />
                </div>
                <div className="min-w-0">
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                        {label}
                    </p>
                    <p className="mt-1 truncate text-base font-bold text-slate-950">
                        {value}
                    </p>
                </div>
            </div>
        </article>
    );
}

function MetricCard({
    label,
    value,
    hint,
}: {
    label: string;
    value: string;
    hint: string;
}) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-bold text-slate-600">
                {label}
            </p>
            <p className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950">
                {value}
            </p>
            <p className="mt-1 text-xs text-slate-500">
                {hint}
            </p>
        </article>
    );
}

function QuickAction({
    href,
    icon: Icon,
    label,
}: {
    href: string;
    icon: typeof BookOpen;
    label: string;
}) {
    return (
        <Link
            href={href}
            data-custom-button="true"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800"
        >
            <Icon
                aria-hidden="true"
                className="h-4 w-4"
            />
            {label}
        </Link>
    );
}

function SortableHeader({
    label,
    active,
    direction,
    onClick,
}: {
    label: string;
    active: boolean;
    direction: SortDirection;
    onClick: () => void;
}) {
    return (
        <th className="px-5 py-3 text-left">
            <button
                type="button"
                onClick={onClick}
                data-custom-button="true"
                className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-slate-500 transition hover:text-slate-900"
            >
                {label}
                {active &&
                    (direction === "asc" ? (
                        <ChevronUp
                            aria-hidden="true"
                            className="h-3.5 w-3.5"
                        />
                    ) : (
                        <ChevronDown
                            aria-hidden="true"
                            className="h-3.5 w-3.5"
                        />
                    ))}
            </button>
        </th>
    );
}

function StudentTableRow({
    student,
    classId,
}: {
    student: ClassStudent;
    classId: number;
}) {
    const attendanceStatus = getAttendanceStatus(
        student.attendance_percentage,
    );

    return (
        <tr className="transition hover:bg-slate-50">
            <td className="px-5 py-4">
                <div>
                    <p className="font-bold text-slate-950">
                        {getStudentName(student)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                        {student.admission_number ??
                            student.email ??
                            `Student ${student.id}`}
                    </p>
                </div>
            </td>

            <td className="px-5 py-4">
                <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800">
                        {formatPercentage(
                            student.attendance_percentage,
                        )}
                    </span>
                    <span
                        className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ring-inset ${attendanceStatus.className}`}
                    >
                        {attendanceStatus.label}
                    </span>
                </div>
            </td>

            <td className="px-5 py-4 text-sm font-semibold text-slate-700">
                {student.current_grade ?? "—"}
            </td>

            <td className="px-5 py-4 text-sm font-semibold text-slate-700">
                {student.target_grade ?? "—"}
            </td>

            <td className="px-5 py-4">
                <div className="flex justify-end gap-2">
                    <Link
                        href={`/teacher/reports?classId=${classId}&studentId=${student.id}`}
                        data-custom-button="true"
                        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50"
                    >
                        Reports
                    </Link>
                    <Link
                        href={`/teacher/attendance?classId=${classId}&studentId=${student.id}`}
                        data-custom-button="true"
                        className="rounded-lg bg-blue-700 px-3 py-2 text-xs font-bold text-white transition hover:bg-blue-800"
                    >
                        Attendance
                    </Link>
                </div>
            </td>
        </tr>
    );
}

function StudentMobileCard({
    student,
    classId,
}: {
    student: ClassStudent;
    classId: number;
}) {
    const attendanceStatus = getAttendanceStatus(
        student.attendance_percentage,
    );

    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h3 className="font-bold text-slate-950">
                        {getStudentName(student)}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500">
                        {student.admission_number ??
                            student.email ??
                            `Student ${student.id}`}
                    </p>
                </div>

                <span
                    className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ring-inset ${attendanceStatus.className}`}
                >
                    {attendanceStatus.label}
                </span>
            </div>

            <dl className="mt-4 grid grid-cols-3 gap-3">
                <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                        Attendance
                    </dt>
                    <dd className="mt-1 font-bold text-slate-900">
                        {formatPercentage(
                            student.attendance_percentage,
                        )}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                        Current
                    </dt>
                    <dd className="mt-1 font-bold text-slate-900">
                        {student.current_grade ?? "—"}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                        Target
                    </dt>
                    <dd className="mt-1 font-bold text-slate-900">
                        {student.target_grade ?? "—"}
                    </dd>
                </div>
            </dl>

            <div className="mt-4 grid grid-cols-2 gap-3">
                <Link
                    href={`/teacher/reports?classId=${classId}&studentId=${student.id}`}
                    data-custom-button="true"
                    className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                >
                    Reports
                </Link>
                <Link
                    href={`/teacher/attendance?classId=${classId}&studentId=${student.id}`}
                    data-custom-button="true"
                    className="inline-flex items-center justify-center rounded-xl bg-blue-700 px-3 py-2 text-sm font-bold text-white transition hover:bg-blue-800"
                >
                    Attendance
                </Link>
            </div>
        </article>
    );
}

function EmptyStudentsState() {
    return (
        <div className="p-8 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                <Users
                    aria-hidden="true"
                    className="h-6 w-6"
                />
            </div>
            <h3 className="mt-4 text-lg font-bold text-slate-950">
                No students enrolled
            </h3>
            <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600">
                Students will appear here after they have been
                assigned to this class.
            </p>
        </div>
    );
}

function ClassDetailLoadingState() {
    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div
                className="mx-auto max-w-7xl"
                aria-hidden="true"
            >
                <div className="h-8 w-36 animate-pulse rounded-lg bg-slate-200" />
                <div className="mt-5 h-28 animate-pulse rounded-2xl bg-slate-200" />

                <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {Array.from({ length: 8 }).map(
                        (_, index) => (
                            <div
                                key={index}
                                className="h-28 animate-pulse rounded-2xl bg-slate-200"
                            />
                        ),
                    )}
                </div>

                <div className="mt-6 h-28 animate-pulse rounded-2xl bg-slate-200" />
                <div className="mt-6 h-96 animate-pulse rounded-2xl bg-slate-200" />
            </div>
        </main>
    );
}
