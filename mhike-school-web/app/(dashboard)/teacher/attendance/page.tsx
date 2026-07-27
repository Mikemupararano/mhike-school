"use client";

import {
    AlertCircle,
    CalendarDays,
    Check,
    CheckCircle2,
    Clock3,
    Loader2,
    MapPin,
    RefreshCw,
    RotateCcw,
    Search,
    Send,
    UserCheck,
    UserMinus,
    UserRoundCheck,
    Users,
    X,
} from "lucide-react";
import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";

import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";

type TimetableEntry = {
    id: number;
    title: string | null;
    room: string | null;
    day_of_week: string;
    timetable_period_id: number;
    class_group_id: number | null;
};

type AttendanceSession = {
    id: number;
    school_id: number;
    class_group_id: number;
    session_date: string;
    session_type: "am" | "pm";
    timetable_entry_id: number | null;
    timetable_period_id: number | null;
};

type AttendanceStatus =
    | "present"
    | "late"
    | "authorised_absence"
    | "unauthorised_absence";

type RegisterStatus =
    | "not_loaded"
    | "empty"
    | "incomplete"
    | "ready";

type Student = {
    id: number;
    first_name?: string;
    last_name?: string;
    email?: string;
};

type StudentAttendance = {
    student_id: number;
    status: AttendanceStatus;
    notes: string;
};

type AttendanceRecord = {
    student_id: number;
    status: AttendanceStatus;
    notes: string | null;
};

type StatusOption = {
    value: AttendanceStatus;
    label: string;
    shortLabel: string;
};

const STATUS_OPTIONS: StatusOption[] = [
    {
        value: "present",
        label: "Present",
        shortLabel: "P",
    },
    {
        value: "late",
        label: "Late",
        shortLabel: "L",
    },
    {
        value: "authorised_absence",
        label: "Authorised absence",
        shortLabel: "AA",
    },
    {
        value: "unauthorised_absence",
        label: "Unauthorised absence",
        shortLabel: "UA",
    },
];

function getTodayIsoDate(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

function getTodayName(): string {
    return new Date()
        .toLocaleDateString("en-GB", {
            weekday: "long",
        })
        .toLowerCase();
}

function getStudentName(student: Student): string {
    const name = [
        student.first_name?.trim(),
        student.last_name?.trim(),
    ]
        .filter(Boolean)
        .join(" ");

    return name || student.email || `Student ${student.id}`;
}

function getErrorMessage(
    error: unknown,
    fallback: string,
): string {
    return error instanceof Error ? error.message : fallback;
}

async function getResponseError(
    response: Response,
    fallback: string,
): Promise<string> {
    try {
        const body = (await response.json()) as {
            detail?: unknown;
            message?: unknown;
        };

        if (
            typeof body.detail === "string" &&
            body.detail.trim()
        ) {
            return body.detail;
        }

        if (
            typeof body.message === "string" &&
            body.message.trim()
        ) {
            return body.message;
        }
    } catch {
        // The fallback is used when the response is not JSON.
    }

    return fallback;
}

function cloneAttendanceMap(
    value: Record<number, StudentAttendance>,
): Record<number, StudentAttendance> {
    return Object.fromEntries(
        Object.entries(value).map(([studentId, attendance]) => [
            Number(studentId),
            { ...attendance },
        ]),
    );
}

function attendanceMapsMatch(
    first: Record<number, StudentAttendance>,
    second: Record<number, StudentAttendance>,
): boolean {
    const firstKeys = Object.keys(first);
    const secondKeys = Object.keys(second);

    if (firstKeys.length !== secondKeys.length) {
        return false;
    }

    return firstKeys.every((key) => {
        const studentId = Number(key);
        const firstAttendance = first[studentId];
        const secondAttendance = second[studentId];

        return (
            firstAttendance?.status === secondAttendance?.status &&
            firstAttendance?.notes.trim() ===
            secondAttendance?.notes.trim()
        );
    });
}

export default function TeacherAttendanceRegisterPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherAttendanceRegisterContent />
        </RoleGate>
    );
}

function TeacherAttendanceRegisterContent() {
    const [entries, setEntries] = useState<TimetableEntry[]>([]);
    const [students, setStudents] = useState<Student[]>([]);
    const [selectedEntryId, setSelectedEntryId] =
        useState<number | null>(null);
    const [autoLoadedEntryId, setAutoLoadedEntryId] =
        useState<number | null>(null);

    const [session, setSession] =
        useState<AttendanceSession | null>(null);
    const [attendanceMap, setAttendanceMap] = useState<
        Record<number, StudentAttendance>
    >({});
    const [lastSavedMap, setLastSavedMap] = useState<
        Record<number, StudentAttendance>
    >({});

    const [isLoadingTimetable, setIsLoadingTimetable] =
        useState(true);
    const [isLoadingStudents, setIsLoadingStudents] =
        useState(false);
    const [isLoadingRegister, setIsLoadingRegister] =
        useState(false);
    const [isSubmitting, setIsSubmitting] =
        useState(false);

    const [message, setMessage] =
        useState<string | null>(null);
    const [error, setError] =
        useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState<
        AttendanceStatus | "all"
    >("all");

    const messageTimerRef =
        useRef<ReturnType<typeof setTimeout> | null>(null);

    const selectedEntry = useMemo(
        () =>
            entries.find(
                (entry) => entry.id === selectedEntryId,
            ) ?? null,
        [entries, selectedEntryId],
    );

    const attendanceSummary = useMemo(() => {
        const values = Object.values(attendanceMap);

        return {
            present: values.filter(
                (item) => item.status === "present",
            ).length,
            late: values.filter(
                (item) => item.status === "late",
            ).length,
            authorisedAbsence: values.filter(
                (item) =>
                    item.status === "authorised_absence",
            ).length,
            unauthorisedAbsence: values.filter(
                (item) =>
                    item.status === "unauthorised_absence",
            ).length,
        };
    }, [attendanceMap]);

    const markedCount = useMemo(
        () =>
            students.filter(
                (student) =>
                    attendanceMap[student.id] !== undefined,
            ).length,
        [attendanceMap, students],
    );

    const registerStatus: RegisterStatus = useMemo(() => {
        if (!session) {
            return "not_loaded";
        }

        if (students.length === 0) {
            return "empty";
        }

        if (markedCount < students.length) {
            return "incomplete";
        }

        return "ready";
    }, [markedCount, session, students.length]);

    const hasUnsavedChanges = useMemo(
        () =>
            Boolean(session) &&
            !attendanceMapsMatch(
                attendanceMap,
                lastSavedMap,
            ),
        [attendanceMap, lastSavedMap, session],
    );

    const filteredStudents = useMemo(() => {
        const query = searchQuery
            .trim()
            .toLocaleLowerCase("en-GB");

        return students.filter((student) => {
            const attendance = attendanceMap[student.id];
            const searchableText = [
                getStudentName(student),
                student.email ?? "",
                String(student.id),
            ]
                .join(" ")
                .toLocaleLowerCase("en-GB");

            const matchesSearch =
                !query || searchableText.includes(query);
            const matchesStatus =
                statusFilter === "all" ||
                attendance?.status === statusFilter;

            return matchesSearch && matchesStatus;
        });
    }, [
        attendanceMap,
        searchQuery,
        statusFilter,
        students,
    ]);

    const progressPercentage =
        students.length > 0
            ? Math.round(
                (markedCount / students.length) * 100,
            )
            : 0;

    const clearTransientMessage = useCallback(() => {
        if (messageTimerRef.current) {
            clearTimeout(messageTimerRef.current);
            messageTimerRef.current = null;
        }
    }, []);

    const showSuccessMessage = useCallback(
        (nextMessage: string) => {
            clearTransientMessage();
            setMessage(nextMessage);

            messageTimerRef.current = setTimeout(() => {
                setMessage(null);
            }, 5000);
        },
        [clearTransientMessage],
    );

    const loadTeacherTimetable = useCallback(async () => {
        try {
            setIsLoadingTimetable(true);
            setError(null);

            const response = await fetch(
                "/api/v1/timetables/teacher/me",
                {
                    credentials: "include",
                    cache: "no-store",
                },
            );

            if (!response.ok) {
                throw new Error(
                    await getResponseError(
                        response,
                        "Failed to load teacher timetable.",
                    ),
                );
            }

            const data =
                (await response.json()) as TimetableEntry[];

            setEntries(data);

            const todayName = getTodayName();
            const todaysEntries = data.filter(
                (entry) =>
                    entry.day_of_week.toLowerCase() ===
                    todayName,
            );

            const defaultEntry =
                todaysEntries[0] ?? data[0] ?? null;

            setSelectedEntryId(
                defaultEntry?.id ?? null,
            );
        } catch (err) {
            setEntries([]);
            setSelectedEntryId(null);
            setError(
                getErrorMessage(
                    err,
                    "Failed to load teacher timetable.",
                ),
            );
        } finally {
            setIsLoadingTimetable(false);
        }
    }, []);

    useEffect(() => {
        void loadTeacherTimetable();
    }, [loadTeacherTimetable]);

    useEffect(
        () => () => clearTransientMessage(),
        [clearTransientMessage],
    );

    useEffect(() => {
        if (!hasUnsavedChanges) {
            return;
        }

        const handleBeforeUnload = (
            event: BeforeUnloadEvent,
        ) => {
            event.preventDefault();
        };

        window.addEventListener(
            "beforeunload",
            handleBeforeUnload,
        );

        return () =>
            window.removeEventListener(
                "beforeunload",
                handleBeforeUnload,
            );
    }, [hasUnsavedChanges]);

    const loadStudents = useCallback(async () => {
        if (
            !selectedEntry ||
            selectedEntry.class_group_id === null
        ) {
            setStudents([]);
            setAttendanceMap({});
            setLastSavedMap({});
            return;
        }

        try {
            setIsLoadingStudents(true);
            setError(null);

            const response = await fetch(
                `/api/v1/classes/${selectedEntry.class_group_id}/students`,
                {
                    credentials: "include",
                    cache: "no-store",
                },
            );

            if (!response.ok) {
                throw new Error(
                    await getResponseError(
                        response,
                        "Failed to load class pupils.",
                    ),
                );
            }

            const data = (await response.json()) as Student[];
            const initialMap: Record<
                number,
                StudentAttendance
            > = {};

            for (const student of data) {
                initialMap[student.id] = {
                    student_id: student.id,
                    status: "present",
                    notes: "",
                };
            }

            setStudents(data);
            setAttendanceMap(initialMap);
            setLastSavedMap(cloneAttendanceMap(initialMap));
        } catch (err) {
            setStudents([]);
            setAttendanceMap({});
            setLastSavedMap({});
            setError(
                getErrorMessage(
                    err,
                    "Failed to load pupils.",
                ),
            );
        } finally {
            setIsLoadingStudents(false);
        }
    }, [selectedEntry]);

    useEffect(() => {
        void loadStudents();
    }, [loadStudents]);

    const loadExistingAttendanceRecords =
        useCallback(
            async (register: AttendanceSession) => {
                const query = new URLSearchParams({
                    class_group_id: String(
                        register.class_group_id,
                    ),
                    session_date:
                        register.session_date,
                });

                if (
                    register.timetable_entry_id !== null
                ) {
                    query.set(
                        "timetable_entry_id",
                        String(
                            register.timetable_entry_id,
                        ),
                    );
                }

                const response = await fetch(
                    `/api/v1/attendance/records?${query.toString()}`,
                    {
                        credentials: "include",
                        cache: "no-store",
                    },
                );

                if (!response.ok) {
                    throw new Error(
                        await getResponseError(
                            response,
                            "Failed to load existing attendance records.",
                        ),
                    );
                }

                const records =
                    (await response.json()) as AttendanceRecord[];

                setAttendanceMap((previous) => {
                    const next =
                        cloneAttendanceMap(previous);

                    for (const record of records) {
                        next[record.student_id] = {
                            student_id:
                                record.student_id,
                            status: record.status,
                            notes: record.notes ?? "",
                        };
                    }

                    setLastSavedMap(
                        cloneAttendanceMap(next),
                    );
                    return next;
                });
            },
            [],
        );

    const createAttendanceSession =
        useCallback(async () => {
            if (
                !selectedEntry ||
                selectedEntry.class_group_id === null
            ) {
                setError(
                    "Select a timetable entry with a class group first.",
                );
                return;
            }

            try {
                setIsLoadingRegister(true);
                setError(null);
                setMessage(null);

                const response = await fetch(
                    "/api/v1/attendance/sessions/from-timetable",
                    {
                        method: "POST",
                        credentials: "include",
                        headers: {
                            "Content-Type":
                                "application/json",
                        },
                        body: JSON.stringify({
                            timetable_entry_id:
                                selectedEntry.id,
                            timetable_period_id:
                                selectedEntry.timetable_period_id,
                            class_group_id:
                                selectedEntry.class_group_id,
                            session_date:
                                getTodayIsoDate(),
                            session_type: "am",
                        }),
                    },
                );

                if (!response.ok) {
                    throw new Error(
                        await getResponseError(
                            response,
                            "Failed to load attendance register.",
                        ),
                    );
                }

                const data =
                    (await response.json()) as AttendanceSession;

                setSession(data);
                await loadExistingAttendanceRecords(data);
                showSuccessMessage(
                    "Attendance register loaded successfully.",
                );
            } catch (err) {
                setSession(null);
                setError(
                    getErrorMessage(
                        err,
                        "Failed to load attendance register.",
                    ),
                );
            } finally {
                setIsLoadingRegister(false);
            }
        }, [
            loadExistingAttendanceRecords,
            selectedEntry,
            showSuccessMessage,
        ]);

    useEffect(() => {
        if (
            !selectedEntry ||
            selectedEntry.class_group_id === null ||
            students.length === 0 ||
            session ||
            autoLoadedEntryId === selectedEntry.id
        ) {
            return;
        }

        setAutoLoadedEntryId(selectedEntry.id);
        void createAttendanceSession();
    }, [
        autoLoadedEntryId,
        createAttendanceSession,
        selectedEntry,
        session,
        students.length,
    ]);

    function updateStudentAttendance(
        studentId: number,
        updates: Partial<StudentAttendance>,
    ) {
        setAttendanceMap((previous) => ({
            ...previous,
            [studentId]: {
                student_id: studentId,
                status:
                    previous[studentId]?.status ??
                    "present",
                notes:
                    previous[studentId]?.notes ?? "",
                ...updates,
            },
        }));
    }

    function markAll(status: AttendanceStatus) {
        setAttendanceMap((previous) => {
            const next = cloneAttendanceMap(previous);

            for (const student of students) {
                next[student.id] = {
                    student_id: student.id,
                    status,
                    notes:
                        next[student.id]?.notes ?? "",
                };
            }

            return next;
        });
        setMessage(null);
        setError(null);
    }

    function resetRegister() {
        setAttendanceMap(
            cloneAttendanceMap(lastSavedMap),
        );
        setMessage(null);
        setError(null);
    }

    function selectEntry(entryId: number) {
        if (entryId === selectedEntryId) {
            return;
        }

        if (
            hasUnsavedChanges &&
            !window.confirm(
                "You have unsaved attendance changes. Change lesson and discard them?",
            )
        ) {
            return;
        }

        setSelectedEntryId(entryId);
        setSession(null);
        setMessage(null);
        setError(null);
        setAutoLoadedEntryId(null);
        setSearchQuery("");
        setStatusFilter("all");
    }

    async function submitAllAttendanceRecords() {
        if (!session) {
            setError(
                "Create or load an attendance register first.",
            );
            return;
        }

        if (students.length === 0) {
            setError(
                "There are no pupils in this register.",
            );
            return;
        }

        try {
            setIsSubmitting(true);
            setError(null);
            setMessage(null);

            const attendanceValues = students.map(
                (student) =>
                    attendanceMap[student.id] ?? {
                        student_id: student.id,
                        status:
                            "present" as AttendanceStatus,
                        notes: "",
                    },
            );

            const response = await fetch(
                "/api/v1/attendance/records/bulk",
                {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify({
                        records: attendanceValues.map(
                            (item) => ({
                                attendance_session_id:
                                    session.id,
                                student_id:
                                    item.student_id,
                                status: item.status,
                                notes:
                                    item.notes.trim() ||
                                    null,
                            }),
                        ),
                    }),
                },
            );

            if (!response.ok) {
                throw new Error(
                    await getResponseError(
                        response,
                        "Failed to submit attendance records.",
                    ),
                );
            }

            setLastSavedMap(
                cloneAttendanceMap(attendanceMap),
            );
            showSuccessMessage(
                "Attendance register submitted successfully.",
            );
        } catch (err) {
            setError(
                getErrorMessage(
                    err,
                    "Failed to submit attendance records.",
                ),
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    const isBusy =
        isLoadingStudents ||
        isLoadingRegister ||
        isSubmitting;

    if (isLoadingTimetable) {
        return <AttendanceLoadingState />;
    }

    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
                <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">
                            Teacher workspace
                        </p>
                        <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
                            Attendance Register
                        </h1>
                        <p className="mt-2 max-w-3xl text-base leading-7 text-slate-600">
                            Select a lesson, review the class
                            register and submit attendance for
                            today.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() =>
                            void loadTeacherTimetable()
                        }
                        disabled={isBusy}
                        data-custom-button="true"
                        className="inline-flex w-fit items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        <RefreshCw
                            aria-hidden="true"
                            className="h-4 w-4"
                        />
                        Refresh timetable
                    </button>
                </header>

                <div
                    aria-live="polite"
                    className="mt-6 space-y-3"
                >
                    {message && (
                        <section
                            role="status"
                            className="flex items-start gap-3 rounded-2xl border border-green-200 bg-green-50 p-4 text-sm font-semibold text-green-800"
                        >
                            <CheckCircle2
                                aria-hidden="true"
                                className="mt-0.5 h-5 w-5 shrink-0"
                            />
                            <span>{message}</span>
                        </section>
                    )}

                    {error && (
                        <section
                            role="alert"
                            className="flex flex-col gap-4 rounded-2xl border border-red-200 bg-red-50 p-4 sm:flex-row sm:items-center sm:justify-between"
                        >
                            <div className="flex items-start gap-3 text-sm font-semibold text-red-800">
                                <AlertCircle
                                    aria-hidden="true"
                                    className="mt-0.5 h-5 w-5 shrink-0"
                                />
                                <span>{error}</span>
                            </div>

                            <button
                                type="button"
                                onClick={() => {
                                    setError(null);
                                    if (!session) {
                                        void createAttendanceSession();
                                    }
                                }}
                                data-custom-button="true"
                                className="inline-flex w-fit items-center justify-center gap-2 rounded-xl border border-red-300 bg-white px-3 py-2 text-sm font-bold text-red-700 transition hover:bg-red-100"
                            >
                                <RefreshCw
                                    aria-hidden="true"
                                    className="h-4 w-4"
                                />
                                Retry
                            </button>
                        </section>
                    )}
                </div>

                <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-slate-950">
                                Lessons
                            </h2>
                            <p className="mt-1 text-sm text-slate-600">
                                Today&apos;s first lesson is selected
                                automatically where available.
                            </p>
                        </div>

                        <span className="inline-flex w-fit items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 ring-1 ring-inset ring-blue-200">
                            <CalendarDays
                                aria-hidden="true"
                                className="h-4 w-4"
                            />
                            {new Date().toLocaleDateString(
                                "en-GB",
                                {
                                    weekday: "long",
                                    day: "numeric",
                                    month: "long",
                                },
                            )}
                        </span>
                    </div>

                    {entries.length === 0 ? (
                        <EmptyLessonsState
                            onRetry={() =>
                                void loadTeacherTimetable()
                            }
                        />
                    ) : (
                        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                            {entries.map((entry) => {
                                const isSelected =
                                    selectedEntryId ===
                                    entry.id;

                                return (
                                    <button
                                        key={entry.id}
                                        type="button"
                                        aria-pressed={
                                            isSelected
                                        }
                                        onClick={() =>
                                            selectEntry(
                                                entry.id,
                                            )
                                        }
                                        data-custom-button="true"
                                        className={`rounded-2xl border p-4 text-left shadow-sm transition focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${isSelected
                                            ? "border-blue-700 bg-blue-700 text-white"
                                            : "border-slate-200 bg-white text-slate-800 hover:border-blue-300 hover:bg-blue-50"
                                            }`}
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <p className="truncate text-base font-bold">
                                                    {entry.title ??
                                                        "Untitled lesson"}
                                                </p>
                                                <p className="mt-1 text-sm opacity-80">
                                                    {
                                                        entry.day_of_week
                                                    }{" "}
                                                    · Period{" "}
                                                    {
                                                        entry.timetable_period_id
                                                    }
                                                </p>
                                            </div>

                                            {isSelected && (
                                                <span className="rounded-full bg-white/20 p-1.5">
                                                    <Check
                                                        aria-hidden="true"
                                                        className="h-4 w-4"
                                                    />
                                                </span>
                                            )}
                                        </div>

                                        <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold opacity-80">
                                            {entry.room && (
                                                <span className="inline-flex items-center gap-1">
                                                    <MapPin
                                                        aria-hidden="true"
                                                        className="h-3.5 w-3.5"
                                                    />
                                                    {
                                                        entry.room
                                                    }
                                                </span>
                                            )}

                                            {entry.class_group_id ===
                                                null && (
                                                    <span>
                                                        No class
                                                        assigned
                                                    </span>
                                                )}
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    )}

                    <div className="mt-5 flex flex-wrap items-center gap-3">
                        <button
                            type="button"
                            disabled={
                                isLoadingRegister ||
                                !selectedEntry ||
                                selectedEntry.class_group_id ===
                                null
                            }
                            onClick={() =>
                                void createAttendanceSession()
                            }
                            data-custom-button="true"
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-5 py-3 text-sm font-bold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {isLoadingRegister ? (
                                <Loader2
                                    aria-hidden="true"
                                    className="h-4 w-4 animate-spin"
                                />
                            ) : (
                                <UserRoundCheck
                                    aria-hidden="true"
                                    className="h-4 w-4"
                                />
                            )}

                            {isLoadingRegister
                                ? "Loading register..."
                                : session
                                    ? `Reload register #${session.id}`
                                    : "Load register"}
                        </button>

                        {selectedEntry &&
                            selectedEntry.class_group_id ===
                            null && (
                                <p className="text-sm font-medium text-amber-700">
                                    This timetable entry has no
                                    class group assigned.
                                </p>
                            )}
                    </div>
                </section>

                <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <div className="border-b border-slate-200 p-4 sm:p-6">
                        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                            <div>
                                <h2 className="text-xl font-bold text-slate-950">
                                    Pupil attendance
                                </h2>
                                <p className="mt-1 text-sm text-slate-600">
                                    {selectedEntry
                                        ? selectedEntry.title ??
                                        "Selected lesson"
                                        : "Select a lesson to begin"}
                                    {session
                                        ? ` · Register #${session.id}`
                                        : ""}
                                </p>
                            </div>

                            <div className="flex flex-wrap gap-2">
                                <RegisterStatusBadge
                                    status={registerStatus}
                                />
                                {hasUnsavedChanges && (
                                    <span className="inline-flex items-center rounded-full bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-700 ring-1 ring-inset ring-amber-200">
                                        Unsaved changes
                                    </span>
                                )}
                            </div>
                        </div>

                        <div className="mt-5">
                            <div className="flex items-center justify-between gap-4 text-sm">
                                <span className="font-bold text-slate-700">
                                    Register progress
                                </span>
                                <span className="font-semibold text-slate-600">
                                    {markedCount}/{students.length} pupils
                                </span>
                            </div>
                            <div
                                className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200"
                                role="progressbar"
                                aria-label="Register completion"
                                aria-valuemin={0}
                                aria-valuemax={100}
                                aria-valuenow={
                                    progressPercentage
                                }
                            >
                                <div
                                    className="h-full rounded-full bg-blue-700 transition-all"
                                    style={{
                                        width: `${progressPercentage}%`,
                                    }}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 sm:p-6 xl:grid-cols-4">
                        <SummaryCard
                            icon={UserCheck}
                            label="Present"
                            value={
                                attendanceSummary.present
                            }
                            className="border-green-200 bg-green-50 text-green-800"
                        />
                        <SummaryCard
                            icon={Clock3}
                            label="Late"
                            value={attendanceSummary.late}
                            className="border-amber-200 bg-amber-50 text-amber-800"
                        />
                        <SummaryCard
                            icon={UserMinus}
                            label="Authorised"
                            value={
                                attendanceSummary.authorisedAbsence
                            }
                            className="border-blue-200 bg-blue-50 text-blue-800"
                        />
                        <SummaryCard
                            icon={X}
                            label="Unauthorised"
                            value={
                                attendanceSummary.unauthorisedAbsence
                            }
                            className="border-red-200 bg-red-50 text-red-800"
                        />
                    </div>

                    {isLoadingStudents ? (
                        <StudentsLoadingState />
                    ) : students.length === 0 ? (
                        <EmptyStudentsState
                            hasSelectedEntry={Boolean(
                                selectedEntry,
                            )}
                        />
                    ) : (
                        <>
                            <div className="border-b border-slate-200 p-4 sm:p-6">
                                <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                                    <div className="grid flex-1 gap-3 sm:grid-cols-2">
                                        <label className="grid gap-2">
                                            <span className="text-sm font-bold text-slate-700">
                                                Search pupils
                                            </span>
                                            <div className="relative">
                                                <Search
                                                    aria-hidden="true"
                                                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                                                />
                                                <input
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
                                                    placeholder="Name, email or pupil ID"
                                                    className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                                />
                                            </div>
                                        </label>

                                        <label className="grid gap-2">
                                            <span className="text-sm font-bold text-slate-700">
                                                Filter status
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
                                                            .value as
                                                        | AttendanceStatus
                                                        | "all",
                                                    )
                                                }
                                                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                                            >
                                                <option value="all">
                                                    All statuses
                                                </option>
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

                                    <div className="flex flex-wrap gap-2">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                markAll(
                                                    "present",
                                                )
                                            }
                                            disabled={isBusy}
                                            data-custom-button="true"
                                            className="rounded-xl border border-green-300 bg-green-50 px-3 py-2 text-sm font-bold text-green-800 transition hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            Mark all present
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() =>
                                                markAll("late")
                                            }
                                            disabled={isBusy}
                                            data-custom-button="true"
                                            className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-bold text-amber-800 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            Mark all late
                                        </button>
                                        <button
                                            type="button"
                                            onClick={
                                                resetRegister
                                            }
                                            disabled={
                                                isBusy ||
                                                !hasUnsavedChanges
                                            }
                                            data-custom-button="true"
                                            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            <RotateCcw
                                                aria-hidden="true"
                                                className="h-4 w-4"
                                            />
                                            Reset
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {filteredStudents.length === 0 ? (
                                <div className="p-8 text-center">
                                    <h3 className="text-lg font-bold text-slate-950">
                                        No matching pupils
                                    </h3>
                                    <p className="mt-2 text-sm text-slate-600">
                                        Change the search or
                                        status filter and try
                                        again.
                                    </p>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setSearchQuery("");
                                            setStatusFilter(
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
                                <div className="divide-y divide-slate-200">
                                    {filteredStudents.map(
                                        (student) => (
                                            <StudentAttendanceRow
                                                key={
                                                    student.id
                                                }
                                                student={
                                                    student
                                                }
                                                attendance={
                                                    attendanceMap[
                                                    student
                                                        .id
                                                    ]
                                                }
                                                disabled={
                                                    isBusy
                                                }
                                                onChange={
                                                    updateStudentAttendance
                                                }
                                            />
                                        ),
                                    )}
                                </div>
                            )}

                            <div className="sticky bottom-0 border-t border-slate-200 bg-white/95 p-4 backdrop-blur sm:p-6">
                                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                                    <div>
                                        <p className="text-sm font-bold text-slate-900">
                                            {hasUnsavedChanges
                                                ? "The register has unsaved changes."
                                                : "The register is up to date."}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            Review absence
                                            codes and notes
                                            before submitting.
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        disabled={
                                            isSubmitting ||
                                            !session ||
                                            students.length ===
                                            0 ||
                                            !hasUnsavedChanges
                                        }
                                        onClick={() =>
                                            void submitAllAttendanceRecords()
                                        }
                                        data-custom-button="true"
                                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        {isSubmitting ? (
                                            <Loader2
                                                aria-hidden="true"
                                                className="h-4 w-4 animate-spin"
                                            />
                                        ) : (
                                            <Send
                                                aria-hidden="true"
                                                className="h-4 w-4"
                                            />
                                        )}

                                        {isSubmitting
                                            ? "Submitting register..."
                                            : "Submit full register"}
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </section>
            </div>
        </main>
    );
}

function StudentAttendanceRow({
    student,
    attendance,
    disabled,
    onChange,
}: {
    student: Student;
    attendance: StudentAttendance | undefined;
    disabled: boolean;
    onChange: (
        studentId: number,
        updates: Partial<StudentAttendance>,
    ) => void;
}) {
    const selectedStatus =
        attendance?.status ?? "present";

    return (
        <article className="grid gap-4 p-4 transition hover:bg-slate-50 sm:p-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(240px,1fr)_minmax(240px,1.2fr)] lg:items-center">
            <div className="min-w-0">
                <h3 className="truncate font-bold text-slate-950">
                    {getStudentName(student)}
                </h3>
                <p className="mt-1 truncate text-xs text-slate-500">
                    {student.email
                        ? student.email
                        : `Pupil ID ${student.id}`}
                </p>
            </div>

            <fieldset
                disabled={disabled}
                className="grid grid-cols-4 gap-2"
            >
                <legend className="sr-only">
                    Attendance status for{" "}
                    {getStudentName(student)}
                </legend>

                {STATUS_OPTIONS.map((option) => {
                    const isSelected =
                        selectedStatus === option.value;

                    return (
                        <label
                            key={option.value}
                            className={`cursor-pointer rounded-xl border px-2 py-2 text-center text-xs font-bold transition ${isSelected
                                ? getSelectedStatusClass(
                                    option.value,
                                )
                                : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                }`}
                            title={option.label}
                        >
                            <input
                                type="radio"
                                name={`attendance-${student.id}`}
                                value={option.value}
                                checked={isSelected}
                                onChange={() =>
                                    onChange(student.id, {
                                        status:
                                            option.value,
                                    })
                                }
                                className="sr-only"
                            />
                            <span aria-hidden="true">
                                {option.shortLabel}
                            </span>
                            <span className="sr-only">
                                {option.label}
                            </span>
                        </label>
                    );
                })}
            </fieldset>

            <label className="grid gap-2">
                <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                    Notes
                </span>
                <input
                    value={attendance?.notes ?? ""}
                    onChange={(event) =>
                        onChange(student.id, {
                            notes: event.target.value,
                        })
                    }
                    disabled={disabled}
                    maxLength={500}
                    placeholder="Optional attendance note"
                    className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
                />
            </label>
        </article>
    );
}

function getSelectedStatusClass(
    status: AttendanceStatus,
): string {
    if (status === "present") {
        return "border-green-600 bg-green-600 text-white";
    }

    if (status === "late") {
        return "border-amber-500 bg-amber-500 text-white";
    }

    if (status === "authorised_absence") {
        return "border-blue-600 bg-blue-600 text-white";
    }

    return "border-red-600 bg-red-600 text-white";
}

function SummaryCard({
    icon: Icon,
    label,
    value,
    className,
}: {
    icon: typeof UserCheck;
    label: string;
    value: number;
    className: string;
}) {
    return (
        <article
            className={`rounded-2xl border p-4 ${className}`}
        >
            <div className="flex items-center justify-between gap-3">
                <div>
                    <p className="text-sm font-bold">
                        {label}
                    </p>
                    <p className="mt-1 text-3xl font-extrabold">
                        {value}
                    </p>
                </div>
                <Icon
                    aria-hidden="true"
                    className="h-7 w-7 opacity-70"
                />
            </div>
        </article>
    );
}

function RegisterStatusBadge({
    status,
}: {
    status: RegisterStatus;
}) {
    const configuration = {
        not_loaded: {
            text: "Register not loaded",
            className:
                "bg-slate-100 text-slate-700 ring-slate-200",
        },
        empty: {
            text: "No pupils",
            className:
                "bg-slate-100 text-slate-700 ring-slate-200",
        },
        incomplete: {
            text: "Incomplete",
            className:
                "bg-amber-50 text-amber-700 ring-amber-200",
        },
        ready: {
            text: "Ready to submit",
            className:
                "bg-green-50 text-green-700 ring-green-200",
        },
    }[status];

    return (
        <span
            className={`inline-flex items-center rounded-full px-3 py-1.5 text-xs font-bold ring-1 ring-inset ${configuration.className}`}
        >
            {configuration.text}
        </span>
    );
}

function EmptyLessonsState({
    onRetry,
}: {
    onRetry: () => void;
}) {
    return (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <CalendarDays
                aria-hidden="true"
                className="mx-auto h-8 w-8 text-slate-400"
            />
            <h3 className="mt-3 text-lg font-bold text-slate-950">
                No timetable entries found
            </h3>
            <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600">
                No lessons are currently available for this
                teacher account.
            </p>
            <button
                type="button"
                onClick={onRetry}
                data-custom-button="true"
                className="mt-4 inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
            >
                <RefreshCw
                    aria-hidden="true"
                    className="h-4 w-4"
                />
                Try again
            </button>
        </div>
    );
}

function EmptyStudentsState({
    hasSelectedEntry,
}: {
    hasSelectedEntry: boolean;
}) {
    return (
        <div className="p-8 text-center">
            <Users
                aria-hidden="true"
                className="mx-auto h-8 w-8 text-slate-400"
            />
            <h3 className="mt-3 text-lg font-bold text-slate-950">
                {hasSelectedEntry
                    ? "No pupils found"
                    : "Select a lesson"}
            </h3>
            <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600">
                {hasSelectedEntry
                    ? "No pupils are currently assigned to the selected class."
                    : "Choose a timetable entry to load its attendance register."}
            </p>
        </div>
    );
}

function StudentsLoadingState() {
    return (
        <div
            aria-label="Loading pupils"
            className="divide-y divide-slate-200"
        >
            {Array.from({ length: 5 }).map(
                (_, index) => (
                    <div
                        key={index}
                        className="grid gap-4 p-5 lg:grid-cols-3"
                    >
                        <div className="h-12 animate-pulse rounded-xl bg-slate-200" />
                        <div className="h-12 animate-pulse rounded-xl bg-slate-200" />
                        <div className="h-12 animate-pulse rounded-xl bg-slate-200" />
                    </div>
                ),
            )}
        </div>
    );
}

function AttendanceLoadingState() {
    return (
        <main className="min-h-full bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
            <div
                className="mx-auto max-w-7xl"
                aria-label="Loading attendance page"
            >
                <div className="h-8 w-48 animate-pulse rounded-lg bg-slate-200" />
                <div className="mt-3 h-12 max-w-2xl animate-pulse rounded-xl bg-slate-200" />
                <div className="mt-6 h-72 animate-pulse rounded-2xl bg-slate-200" />
                <div className="mt-6 h-[34rem] animate-pulse rounded-2xl bg-slate-200" />
            </div>
        </main>
    );
}
