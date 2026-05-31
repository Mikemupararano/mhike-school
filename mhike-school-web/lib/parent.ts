import { apiGet } from "@/lib/api";

export type ParentStudentLink = {
    id: number;
    parent_id: number;
    student_id: number;
};

export type StudentAttendanceStatus =
    | "present"
    | "late"
    | "authorised_absence"
    | "unauthorised_absence";

export type StudentAttendanceHistoryRecord = {
    record_id: number;
    attendance_session_id: number;
    session_date: string;
    session_type: string;
    class_group_id: number;
    class_name: string | null;
    status: StudentAttendanceStatus;
    notes: string | null;
    marked_by_id: number | null;
    created_at: string;
    updated_at: string;
};

export type StudentAttendanceProfile = {
    student_id: number;
    student_name: string | null;
    school_id: number;
    total_records: number;
    present: number;
    late: number;
    authorised_absence: number;
    unauthorised_absence: number;
    attendance_percentage: number;
    history: StudentAttendanceHistoryRecord[];
};

export async function getMyLinkedChildren(): Promise<
    ParentStudentLink[]
> {
    return apiGet<ParentStudentLink[]>(
        "/parent-students/me/children",
    );
}

export async function getChildAttendanceProfile(
    studentId: number | string,
): Promise<StudentAttendanceProfile> {
    return apiGet<StudentAttendanceProfile>(
        `/parent-attendance/students/${studentId}/profile`,
    );
}

export async function getMyChildrenAttendanceProfiles(): Promise<
    StudentAttendanceProfile[]
> {
    const links =
        await getMyLinkedChildren();

    return Promise.all(
        links.map((link) =>
            getChildAttendanceProfile(
                link.student_id,
            ),
        ),
    );
}