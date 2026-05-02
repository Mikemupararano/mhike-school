import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { User } from "@/types/user";
import type {
    ClassGroup,
    CreateClassInput,
    UpdateClassInput,
    EnrollmentCreateInput,
    EnrollmentResponse,
} from "@/types/class";

export async function listClasses(): Promise<ClassGroup[]> {
    return apiGet<ClassGroup[]>("/classes");
}

export async function getClass(classId: number): Promise<ClassGroup> {
    return apiGet<ClassGroup>(`/classes/${classId}`);
}

export async function createClass(
    data: CreateClassInput,
): Promise<ClassGroup> {
    return apiPost<ClassGroup>("/classes", data);
}

export async function updateClass(
    classId: number,
    data: UpdateClassInput,
): Promise<ClassGroup> {
    return apiPatch<ClassGroup>(`/classes/${classId}`, data);
}

export async function assignTeacher(
    classId: number,
    teacherId: number,
): Promise<ClassGroup> {
    return apiPatch<ClassGroup>(
        `/classes/${classId}/assign-teacher?teacher_id=${teacherId}`,
    );
}

export async function getClassStudents(classId: number): Promise<User[]> {
    return apiGet<User[]>(`/classes/${classId}/students`);
}

export async function enrollStudent(
    classId: number,
    studentId: number,
): Promise<EnrollmentResponse> {
    const data: EnrollmentCreateInput = {
        class_id: classId,
        user_id: studentId,
    };

    return apiPost<EnrollmentResponse>("/enrollments", data);
}

export async function removeStudent(
    classId: number,
    studentId: number,
): Promise<void> {
    const data: EnrollmentCreateInput = {
        class_id: classId,
        user_id: studentId,
    };

    return apiDelete<void>("/enrollments", data);
}