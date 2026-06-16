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