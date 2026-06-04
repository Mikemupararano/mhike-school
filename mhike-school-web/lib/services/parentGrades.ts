import { apiGet } from "@/lib/api";

export type ParentGrade = {
    submission_id: number;
    assignment_id: number;
    student_id: number;
    assignment_title: string;
    max_score: number;
    score: number | null;
    feedback: string | null;
    status: string;
    submitted_at: string;
    graded_at: string | null;
};

export async function getParentGrades(): Promise<ParentGrade[]> {
    return apiGet<ParentGrade[]>(
        "/assignment-submissions/parent/grades",
    );
}