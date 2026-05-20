import apiClient from "@/lib/api/client";

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

const TIMETABLE_BASE = "/api/v1/timetables";

export async function listTimetablePeriods(): Promise<TimetablePeriod[]> {
    const response = await apiClient.get<TimetablePeriod[]>(
        `${TIMETABLE_BASE}/periods`
    );

    return response.data;
}

export async function createTimetablePeriod(
    payload: Partial<TimetablePeriod>
): Promise<TimetablePeriod> {
    const response = await apiClient.post<TimetablePeriod>(
        `${TIMETABLE_BASE}/periods`,
        payload
    );

    return response.data;
}

export async function listTimetables(
    filters?: TimetableFilters
): Promise<Timetable[]> {
    const response = await apiClient.get<Timetable[]>(TIMETABLE_BASE, {
        params: filters,
    });

    return response.data;
}

export async function createTimetable(
    payload: Partial<Timetable>
): Promise<Timetable> {
    const response = await apiClient.post<Timetable>(
        TIMETABLE_BASE,
        payload
    );

    return response.data;
}

export async function listTimetableEntries(
    filters?: TimetableEntryFilters
): Promise<TimetableEntry[]> {
    const response = await apiClient.get<TimetableEntry[]>(
        `${TIMETABLE_BASE}/entries`,
        {
            params: filters,
        }
    );

    return response.data;
}

export async function createTimetableEntry(
    payload: Partial<TimetableEntry>
): Promise<TimetableEntry> {
    const response = await apiClient.post<TimetableEntry>(
        `${TIMETABLE_BASE}/entries`,
        payload
    );

    return response.data;
}

export async function getTeacherTimetable(
    day_of_week?: string
): Promise<TimetableEntry[]> {
    const response = await apiClient.get<TimetableEntry[]>(
        `${TIMETABLE_BASE}/teacher/me`,
        {
            params: {
                day_of_week,
            },
        }
    );

    return response.data;
}

export async function getStudentTimetable(
    class_group_id?: number,
    day_of_week?: string
): Promise<TimetableEntry[]> {
    const response = await apiClient.get<TimetableEntry[]>(
        `${TIMETABLE_BASE}/student/me`,
        {
            params: {
                class_group_id,
                day_of_week,
            },
        }
    );

    return response.data;
}

export async function getParentChildTimetable(
    studentId: number,
    class_group_id?: number,
    day_of_week?: string
): Promise<TimetableEntry[]> {
    const response = await apiClient.get<TimetableEntry[]>(
        `${TIMETABLE_BASE}/parent/child/${studentId}`,
        {
            params: {
                class_group_id,
                day_of_week,
            },
        }
    );

    return response.data;
}

export async function listTimetableAssignments(
    filters?: TimetableAssignmentFilters
): Promise<TimetableAssignment[]> {
    const response = await apiClient.get<TimetableAssignment[]>(
        `${TIMETABLE_BASE}/assignments`,
        {
            params: filters,
        }
    );

    return response.data;
}

export async function createTimetableAssignment(
    payload: Partial<TimetableAssignment>
): Promise<TimetableAssignment> {
    const response = await apiClient.post<TimetableAssignment>(
        `${TIMETABLE_BASE}/assignments`,
        payload
    );

    return response.data;
}