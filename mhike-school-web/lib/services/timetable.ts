import { apiGet, apiPost } from "@/lib/api";

export interface TimetablePeriod {
    id: number;
    school_id: number;
    name: string;
    short_name: string;
    period_number: number;
    start_time: string;
    end_time: string;
}

export interface Timetable {
    id: number;
    school_id: number;
    name: string;
    academic_year: string;
    effective_from: string;
    effective_to?: string | null;
    is_active: boolean;
}

export interface TimetableEntry {
    id: number;
    timetable_id: number;
    school_id: number;
    class_group_id: number;
    course_id?: number | null;
    teacher_id?: number | null;
    timetable_period_id: number;
    day_of_week: string;
    title: string;
    room?: string | null;
    notes?: string | null;
}

export interface TimetableAssignment {
    id: number;
    timetable_id: number;
    school_id: number;
    assignment_type: string;
    user_id?: number | null;
    class_group_id?: number | null;
}

export interface TimetableEntryFilters {
    timetable_id?: number;
    class_group_id?: number;
    course_id?: number;
    teacher_id?: number;
    day_of_week?: string;
    limit?: number;
    offset?: number;
}

export interface TimetableFilters {
    academic_year?: string;
    is_active?: boolean;
    limit?: number;
    offset?: number;
}

export interface TimetableAssignmentFilters {
    timetable_id?: number;
    assignment_type?: string;
    user_id?: number;
    class_group_id?: number;
    limit?: number;
    offset?: number;
}

const TIMETABLE_BASE = "/timetables";

function withQuery<T extends object>(
    path: string,
    params?: T,
): string {
    if (!params) {
        return path;
    }

    const searchParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
        if (
            value !== undefined &&
            value !== null &&
            value !== ""
        ) {
            searchParams.set(
                key,
                String(value),
            );
        }
    });

    const query = searchParams.toString();

    return query
        ? `${path}?${query}`
        : path;
}

export async function listTimetablePeriods(): Promise<TimetablePeriod[]> {
    return apiGet<TimetablePeriod[]>(
        `${TIMETABLE_BASE}/periods`,
    );
}

export async function createTimetablePeriod(
    payload: Partial<TimetablePeriod>,
): Promise<TimetablePeriod> {
    return apiPost<TimetablePeriod>(
        `${TIMETABLE_BASE}/periods`,
        payload,
    );
}

export async function listTimetables(
    filters?: TimetableFilters,
): Promise<Timetable[]> {
    return apiGet<Timetable[]>(
        withQuery(
            TIMETABLE_BASE,
            filters,
        ),
    );
}

export async function createTimetable(
    payload: Partial<Timetable>,
): Promise<Timetable> {
    return apiPost<Timetable>(
        TIMETABLE_BASE,
        payload,
    );
}

export async function listTimetableEntries(
    filters?: TimetableEntryFilters,
): Promise<TimetableEntry[]> {
    return apiGet<TimetableEntry[]>(
        withQuery(
            `${TIMETABLE_BASE}/entries`,
            filters,
        ),
    );
}

export async function createTimetableEntry(
    payload: Partial<TimetableEntry>,
): Promise<TimetableEntry> {
    return apiPost<TimetableEntry>(
        `${TIMETABLE_BASE}/entries`,
        payload,
    );
}

export async function getTeacherTimetable(
    day_of_week?: string,
): Promise<TimetableEntry[]> {
    return apiGet<TimetableEntry[]>(
        withQuery(
            `${TIMETABLE_BASE}/teacher/me`,
            {
                day_of_week,
            },
        ),
    );
}

export async function getStudentTimetable(
    class_group_id?: number,
    day_of_week?: string,
): Promise<TimetableEntry[]> {
    return apiGet<TimetableEntry[]>(
        withQuery(
            `${TIMETABLE_BASE}/student/me`,
            {
                class_group_id,
                day_of_week,
            },
        ),
    );
}

export async function getParentChildTimetable(
    studentId: number,
    class_group_id?: number,
    day_of_week?: string,
): Promise<TimetableEntry[]> {
    return apiGet<TimetableEntry[]>(
        withQuery(
            `${TIMETABLE_BASE}/parent/child/${studentId}`,
            {
                class_group_id,
                day_of_week,
            },
        ),
    );
}

export async function listTimetableAssignments(
    filters?: TimetableAssignmentFilters,
): Promise<TimetableAssignment[]> {
    return apiGet<TimetableAssignment[]>(
        withQuery(
            `${TIMETABLE_BASE}/assignments`,
            filters,
        ),
    );
}

export async function createTimetableAssignment(
    payload: Partial<TimetableAssignment>,
): Promise<TimetableAssignment> {
    return apiPost<TimetableAssignment>(
        `${TIMETABLE_BASE}/assignments`,
        payload,
    );
}