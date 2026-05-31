import { apiGet } from "@/lib/api";

export type TimetableEntry = {
    id: number;
    title: string | null;
    room: string | null;
    day_of_week: string;
    timetable_period_id: number;
    class_group_id?: number | null;
    teacher_id?: number | null;
};

export async function getMyStudentTimetable(): Promise<TimetableEntry[]> {
    return apiGet<TimetableEntry[]>("/timetables/student/me");
}

export async function getMyTeacherTimetable(): Promise<TimetableEntry[]> {
    return apiGet<TimetableEntry[]>("/timetables/teacher/me");
}

export async function getChildTimetable(
    childId: number | string,
    classGroupId?: number | string | null,
): Promise<TimetableEntry[]> {
    const query =
        classGroupId !== undefined && classGroupId !== null
            ? `?class_group_id=${classGroupId}`
            : "";

    return apiGet<TimetableEntry[]>(
        `/timetables/parent/child/${childId}${query}`,
    );
}