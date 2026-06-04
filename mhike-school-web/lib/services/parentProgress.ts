import { apiGet } from "@/lib/api";

export type StudentProgressSummary = {
    student_id: number;
    attendance_percentage: number;
    assignments_completed: number;
    average_assignment_score: number | null;
    report_count: number;
    latest_report_title: string | null;
    recent_feedback_count: number;
};

export async function getParentStudentProgress(
    studentId: number,
): Promise<StudentProgressSummary> {
    return apiGet<StudentProgressSummary>(
        `/student-progress/parent/${studentId}`,
    );
}