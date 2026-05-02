/* =========================
   Core Class Model
========================= */

export type ClassGroup = {
    id: number;
    name: string;
    school_id: number;
    teacher_id?: number | null;
    created_at: string;
};

/* =========================
   Create / Update Inputs
========================= */

export type CreateClassInput = {
    name: string;
    teacher_id?: number | null;
};

export type UpdateClassInput = {
    name?: string;
    teacher_id?: number | null;
};

/* =========================
   Enrollments
========================= */

export type EnrollmentCreateInput = {
    user_id: number;
    class_id: number;
};

export type EnrollmentResponse = {
    id: number;
    user_id: number;
    class_id: number;
    created_at: string;
};

/* =========================
   Optional UI Helpers
========================= */

export type ClassWithCounts = ClassGroup & {
    student_count?: number;
};

export type ClassWithTeacher = ClassGroup & {
    teacher_name?: string;
};