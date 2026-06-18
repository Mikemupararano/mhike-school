import { apiPost } from "@/lib/api";

export type PublishSessionResponse = {
    published_count: number;
};

export async function publishReportSession(
    reportSessionId: number,
): Promise<PublishSessionResponse> {
    return apiPost<PublishSessionResponse>(
        `/student-reports/publish-session/${reportSessionId}`,
        {},
    );
}