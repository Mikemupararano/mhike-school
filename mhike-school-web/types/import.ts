export const IMPORT_OPERATIONS = [
    "create",
    "update",
    "upsert",
    "delete",
] as const;

export type ImportOperation =
    (typeof IMPORT_OPERATIONS)[number];

export const IMPORT_STATUSES = [
    "pending",
    "uploading",
    "staged",
    "validating",
    "validated",
    "processing",
    "completed",
    "partially_completed",
    "failed",
    "cancelled",
] as const;

export type ImportStatus =
    (typeof IMPORT_STATUSES)[number];

export const IMPORT_ROW_STATUSES = [
    "pending",
    "valid",
    "invalid",
    "processing",
    "completed",
    "failed",
    "skipped",
] as const;

export type ImportRowStatus =
    (typeof IMPORT_ROW_STATUSES)[number];

export type ImportMetadata =
    Record<string, unknown>;

export interface ImportBatchCreate {
    import_type: string;
    operation?: ImportOperation;
    original_filename?: string | null;
    metadata?: ImportMetadata | null;
}

export interface ImportBatchUpdate {
    import_type?: string;
    operation?: ImportOperation;
    status?: ImportStatus;
    original_filename?: string | null;
    metadata?: ImportMetadata | null;
}

export interface ImportBatchSummary {
    id: number;
    school_id: number;
    created_by_id: number;

    import_type: string;
    operation: ImportOperation;
    status: ImportStatus;

    original_filename: string | null;

    total_rows: number;
    valid_rows: number;
    invalid_rows: number;
    processed_rows: number;
    successful_rows: number;
    failed_rows: number;
    skipped_rows: number;

    is_archived: boolean;

    created_at: string;
    updated_at: string;
    completed_at: string | null;
}

export interface ImportBatchRead
    extends ImportBatchSummary {
    metadata: ImportMetadata | null;
    error_message: string | null;
    archived_at: string | null;
}

export interface ImportRowCreate {
    row_number: number;
    raw_data: ImportMetadata;
    normalised_data?: ImportMetadata | null;
    status?: ImportRowStatus;
    validation_errors?: ImportMetadata[] | null;
    validation_warnings?: ImportMetadata[] | null;
}

export interface ImportRowUpdate {
    normalised_data?: ImportMetadata | null;
    status?: ImportRowStatus;
    validation_errors?: ImportMetadata[] | null;
    validation_warnings?: ImportMetadata[] | null;
    error_message?: string | null;
    imported_record_id?: number | null;
}

export interface ImportRowRead {
    id: number;
    import_batch_id: number;

    row_number: number;
    raw_data: ImportMetadata;
    normalised_data: ImportMetadata | null;

    status: ImportRowStatus;

    validation_errors: ImportMetadata[] | null;
    validation_warnings: ImportMetadata[] | null;

    error_message: string | null;
    imported_record_id: number | null;

    created_at: string;
    updated_at: string;
    processed_at: string | null;
}

export interface ImportBatchListParams {
    import_type?: string;
    operation?: ImportOperation;
    status?: ImportStatus;
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
    operation?: ImportOperation;
    status?: ImportStatus;
    include_archived?: boolean;
}

export interface ImportRowCountParams {
    status?: ImportRowStatus;
}

/**
 * Count endpoints currently return `{ total: number }`.
 *
 * `count` is retained as an optional compatibility field in case
 * another deployment or older endpoint returns `{ count: number }`.
 */
export interface ImportCountResponse {
    total?: number;
    count?: number;
}