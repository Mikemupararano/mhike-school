import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";

export type AssignmentOut = {
    id: number;
    title: string;
    description?: string | null;
    course_id: number;
    school_id: number;
    created_by: number;
    due_date?: string | null;
    max_score: number;
    is_published: boolean;
    created_at: string;
};

export type AssignmentCreate = {
    title: string;
    description?: string | null;
    course_id: number;
    due_date?: string | null;
    max_score?: number;
    is_published?: boolean;
};

export type AssignmentUpdate = {
    title?: string;
    description?: string | null;
    due_date?: string | null;
    max_score?: number;
    is_published?: boolean;
};

export type AssignmentPublishIn = {
    is_published: boolean;
};

export type AssignmentSubmissionOut = {
    id: number;
    assignment_id: number;
    student_id: number;
    school_id: number;
    submission_text?: string | null;
    attachment_url?: string | null;
    status: string;
    score?: number | null;
    feedback?: string | null;
    graded_by?: number | null;
    graded_at?: string | null;
    submitted_at: string;
    created_at: string;
};

export type AssignmentSubmissionSubmit = {
    submission_text?: string | null;
    attachment_url?: string | null;
};

export type AssignmentSubmissionGrade = {
    score?: number | null;
    feedback?: string | null;
    status?: string;
};

export async function createAssignment(body: AssignmentCreate) {
    return apiPost<AssignmentOut>("/assignments", body);
}

export async function getMyTeacherAssignments() {
    return apiGet<AssignmentOut[]>("/assignments/me");
}

export async function getMyStudentAssignments() {
    return apiGet<AssignmentOut[]>("/assignments/my");
}

export async function getAssignment(assignmentId: number) {
    return apiGet<AssignmentOut>(`/assignments/${assignmentId}`);
}

export async function updateAssignment(
    assignmentId: number,
    body: AssignmentUpdate
) {
    return apiPatch<AssignmentOut>(`/assignments/${assignmentId}`, body);
}

export async function publishAssignment(
    assignmentId: number,
    body: AssignmentPublishIn
) {
    return apiPost<AssignmentOut>(
        `/assignments/${assignmentId}/publish`,
        body
    );
}

export async function deleteAssignment(assignmentId: number) {
    return apiDelete<void>(`/assignments/${assignmentId}`);
}

export async function submitAssignment(
    assignmentId: number,
    body: AssignmentSubmissionSubmit
) {
    return apiPost<AssignmentSubmissionOut>(
        `/assignment-submissions/${assignmentId}/submit`,
        body
    );
}

export async function getMySubmission(assignmentId: number) {
    return apiGet<AssignmentSubmissionOut>(
        `/assignment-submissions/${assignmentId}/me`
    );
}

export async function listAssignmentSubmissions(assignmentId: number) {
    return apiGet<AssignmentSubmissionOut[]>(
        `/assignment-submissions/assignment/${assignmentId}`
    );
}

export async function gradeSubmission(
    submissionId: number,
    body: AssignmentSubmissionGrade
) {
    return apiPost<AssignmentSubmissionOut>(
        `/assignment-submissions/${submissionId}/grade`,
        body
    );
}