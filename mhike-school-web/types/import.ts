export const IMPORT_OPERATIONS = [
    "create",
    "update",
    "upsert",
    "delete",
] as const;

export type ImportOperation =
    (typeof IMPORT_OPERATIONS)[number];

export const IMPORT_STATUSES = [
    "uploaded",
    "parsing",
    "validating",
    "ready",
    "queued",
    "processing",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
] as const;

export type ImportStatus =
    (typeof IMPORT_STATUSES)[number];

export const IMPORT_ROW_STATUSES = [
    "pending",
    "valid",
    "warning",
    "invalid",
    "queued",
    "processing",
    "imported",
    "updated",
    "skipped",
    "failed",
] as const;

export type ImportRowStatus =
    (typeof IMPORT_ROW_STATUSES)[number];

export type ImportMetadata =
    Record<string, unknown>;

export type ImportIssue =
    Record<string, unknown>;

export interface ImportTypeRead {
    value: string;
    label: string;
    description: string | null;
}

export interface ImportBatchCreate {
    import_type: string;
    operation?: ImportOperation;
    original_filename: string;

    stored_filename?: string | null;
    file_format?: string | null;
    mime_type?: string | null;
    file_size_bytes?: number | null;
    file_hash?: string | null;

    column_mapping?: ImportMetadata;
    import_options?: ImportMetadata;
}

export interface ImportBatchUpdate {
    operation?: ImportOperation;

    column_mapping?: ImportMetadata | null;
    import_options?: ImportMetadata | null;

    current_stage?: string | null;
    validation_summary?: ImportMetadata | null;
    result_summary?: ImportMetadata | null;

    error_message?: string | null;
    error_report_path?: string | null;
}

export interface ImportBatchSummary {
    id: number;

    import_type: string;
    operation: ImportOperation;
    status: ImportStatus;

    original_filename: string;

    total_rows: number;
    successful_rows: number;
    warning_rows: number;
    failed_rows: number;
    skipped_rows: number;

    current_stage: string | null;

    created_at: string;
    completed_at: string | null;

    is_archived: boolean;

    /**
     * These counters are guaranteed on the full batch response.
     * They remain optional here because summary endpoints may omit them.
     */
    validated_rows?: number;
    processed_rows?: number;

    /**
     * Temporary compatibility aliases for older dashboard components.
     *
     * New code should prefer:
     * - validated_rows
     * - failed_rows
     * - successful_rows
     */
    valid_rows?: number;
    invalid_rows?: number;
    imported_rows?: number;
}

export interface ImportBatchRead
    extends ImportBatchSummary {
    school_id: number;
    uploaded_by_id: number;

    stored_filename: string | null;
    file_format: string | null;
    mime_type: string | null;
    file_size_bytes: number | null;
    file_hash: string | null;

    column_mapping: ImportMetadata;
    import_options: ImportMetadata;

    validated_rows: number;
    processed_rows: number;

    validation_summary: ImportMetadata;
    result_summary: ImportMetadata;

    error_message: string | null;
    error_report_path: string | null;

    confirmed_at: string | null;
    queued_at: string | null;
    started_at: string | null;
    completed_at: string | null;
    cancelled_at: string | null;

    created_at: string;
    updated_at: string;

    is_archived: boolean;
    archived_at: string | null;
    archived_by_id: number | null;
    archive_reason: string | null;
}

export interface ImportBatchProgress {
    id: number;
    school_id: number;

    import_type: string;
    status: ImportStatus;
    current_stage: string | null;

    total_rows: number;
    validated_rows: number;
    processed_rows: number;

    successful_rows: number;
    warning_rows: number;
    failed_rows: number;
    skipped_rows: number;

    validation_percentage: number;
    progress_percentage: number;

    remaining_validation_rows: number;
    remaining_processing_rows: number;

    is_finished: boolean;
    is_archived: boolean;

    error_message: string | null;

    queued_at: string | null;
    started_at: string | null;
    completed_at: string | null;
    cancelled_at: string | null;
    updated_at: string;
}

export interface ImportRowCreate {
    batch_id: number;
    school_id: number;

    row_number: number;

    original_data: ImportMetadata;
    normalised_data?: ImportMetadata;

    status?: ImportRowStatus;

    validation_errors?: ImportIssue[];
    validation_warnings?: ImportIssue[];

    entity_type?: string | null;
}

export interface ImportRowUpdate {
    status?: ImportRowStatus;

    normalised_data?: ImportMetadata | null;
    validation_errors?: ImportIssue[] | null;
    validation_warnings?: ImportIssue[] | null;

    entity_type?: string | null;
    created_entity_id?: number | null;

    attempt_count?: number;
    error_message?: string | null;
    processed_at?: string | null;
}

export interface ImportRowRead {
    id: number;
    batch_id: number;
    school_id: number;

    row_number: number;

    original_data: ImportMetadata;
    normalised_data: ImportMetadata;

    status: ImportRowStatus;

    validation_errors: ImportIssue[];
    validation_warnings: ImportIssue[];

    entity_type: string | null;
    created_entity_id: number | null;

    attempt_count: number;

    error_message: string | null;
    processed_at: string | null;

    created_at: string;
    updated_at: string;

    /**
     * Temporary compatibility aliases for older row-detail code.
     *
     * New code should prefer:
     * - original_data
     * - created_entity_id
     */
    raw_data?: ImportMetadata;
    imported_record_id?: number | null;
}

export interface ImportBatchListParams {
    import_type?: string;
    status?: ImportStatus;
    uploaded_by_id?: number;
    include_archived?: boolean;
    skip?: number;
    limit?: number;
}

export interface ImportRowListParams {
    status?: ImportRowStatus;
    skip?: number;
    limit?: number;
}

export interface ImportBatchCountParams {
    import_type?: string;
    status?: ImportStatus;
    uploaded_by_id?: number;
    include_archived?: boolean;
}

export interface ImportRowCountParams {
    status?: ImportRowStatus;
}

/**
 * Current count endpoints return:
 *
 *     { total: number }
 *
 * ``count`` remains optional for compatibility with older deployments.
 */
export interface ImportCountResponse {
    total?: number;
    count?: number;
}