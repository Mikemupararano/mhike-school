import { apiPost } from "@/lib/api";

export type ReportQualityIssue = {
    type: string;
    message: string;
    suggestion: string | null;
};

export type ReportQualityResponse = {
    original_comment: string;
    corrected_comment: string;
    issues: ReportQualityIssue[];
};

export type ReportNotesGenerateResponse = {
    notes: string;
    generated_comment: string;
};

export async function checkReportComment(
    comment: string,
): Promise<ReportQualityResponse> {
    return apiPost<ReportQualityResponse>(
        "/report-quality/check-comment",
        {
            comment,
        },
    );
}

export async function generateReportFromNotes(
    notes: string,
    studentName?: string,
    subject?: string,
    yearGroup?: string,
): Promise<ReportNotesGenerateResponse> {
    return apiPost<ReportNotesGenerateResponse>(
        "/report-quality/generate-from-notes",
        {
            notes,
            student_name: studentName,
            subject,
            year_group: yearGroup,
        },
    );
}