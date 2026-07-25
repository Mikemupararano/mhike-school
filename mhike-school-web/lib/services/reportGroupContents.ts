import { apiGet, apiPut } from "@/lib/api";

export type ReportGroupContent = {
    id: number;
    school_id: number;
    report_session_id: number;
    class_id: number;
    teacher_id: number | null;
    subject_name: string | null;
    work_covered: string | null;
    created_at: string;
    updated_at: string;
};

export type ReportGroupContentScope = {
    report_session_id: number;
    class_id: number;
    teacher_id?: number | null;
    subject_name?: string | null;
};

export type SaveReportGroupContentInput = ReportGroupContentScope & {
    work_covered: string | null;
};

function buildScopeQuery(scope: ReportGroupContentScope): string {
    const params = new URLSearchParams({
        report_session_id: String(scope.report_session_id),
        class_id: String(scope.class_id),
    });

    if (scope.teacher_id != null) {
        params.set("teacher_id", String(scope.teacher_id));
    }

    if (scope.subject_name?.trim()) {
        params.set("subject_name", scope.subject_name.trim());
    }

    return params.toString();
}

export async function getReportGroupContent(
    scope: ReportGroupContentScope,
): Promise<ReportGroupContent | null> {
    const query = buildScopeQuery(scope);

    try {
        return await apiGet<ReportGroupContent>(
            `/report-group-contents/scope?${query}`,
        );
    } catch (error) {
        if (
            error instanceof Error &&
            (error.message.includes("404") ||
                error.message.toLowerCase().includes("not found"))
        ) {
            return null;
        }

        throw error;
    }
}

export async function saveReportGroupContent(
    input: SaveReportGroupContentInput,
): Promise<ReportGroupContent> {
    return apiPut<ReportGroupContent>("/report-group-contents", {
        report_session_id: input.report_session_id,
        class_id: input.class_id,
        teacher_id: input.teacher_id ?? null,
        subject_name: input.subject_name?.trim() || null,
        work_covered: input.work_covered?.trim() || null,
    });
}