import {
    apiGet,
    apiPost,
    apiPostForm,
} from "@/lib/api";

import type {
    ImportBatchCountParams,
    ImportBatchCreate,
    ImportBatchListParams,
    ImportBatchProgress,
    ImportBatchRead,
    ImportBatchSummary,
    ImportCountResponse,
    ImportRowCountParams,
    ImportRowListParams,
    ImportRowRead,
} from "@/types/import";

const AUTH_TOKEN_STORAGE_KEY = "mhike_token";
const MAX_CSV_FILE_SIZE_BYTES = 10 * 1024 * 1024;

type QueryValue =
    | string
    | number
    | boolean
    | null
    | undefined;

export interface UploadImportCsvOptions {
    replaceExisting?: boolean;
}

export interface ImportBatchProgressOptions {
    includeArchived?: boolean;
}

export interface ImportBatchReadOptions {
    includeArchived?: boolean;
}

export interface ImportBatchActionOptions {
    reason?: string | null;
}

/**
 * Resolve the authentication token used for import requests.
 *
 * An explicitly supplied token takes priority. Browser calls otherwise use
 * the session token created by the MHike School login flow.
 */
function resolveAuthToken(token?: string): string {
    const explicitToken = token?.trim();

    if (explicitToken) {
        return explicitToken;
    }

    if (typeof window !== "undefined") {
        const storedToken = window.sessionStorage
            .getItem(AUTH_TOKEN_STORAGE_KEY)
            ?.trim();

        if (storedToken) {
            return storedToken;
        }
    }

    throw new Error(
        "You are not authenticated. Please sign in again before using data imports.",
    );
}

function appendQueryParam(
    params: URLSearchParams,
    key: string,
    value: QueryValue,
): void {
    if (value === undefined || value === null) {
        return;
    }

    if (typeof value === "string") {
        const trimmedValue = value.trim();

        if (!trimmedValue) {
            return;
        }

        params.set(key, trimmedValue);
        return;
    }

    params.set(key, String(value));
}

function buildQueryString(
    values: Record<string, QueryValue>,
): string {
    const params = new URLSearchParams();

    for (const [key, value] of Object.entries(values)) {
        appendQueryParam(params, key, value);
    }

    const query = params.toString();

    return query ? `?${query}` : "";
}

/**
 * Support the current backend count response:
 *
 *     { "total": 0 }
 *
 * and the older compatibility response:
 *
 *     { "count": 0 }
 *
 * A raw numeric response is also accepted.
 */
function normaliseCountResponse(
    response: ImportCountResponse | number,
): number {
    const count =
        typeof response === "number"
            ? response
            : response.total ?? response.count;

    if (
        typeof count !== "number" ||
        !Number.isFinite(count) ||
        !Number.isInteger(count) ||
        count < 0
    ) {
        throw new Error(
            "The import service returned an invalid count response.",
        );
    }

    return count;
}

function assertPositiveInteger(
    value: number,
    fieldName: string,
): void {
    if (!Number.isInteger(value) || value <= 0) {
        throw new Error(
            `${fieldName} must be a positive integer.`,
        );
    }
}

function validatePaginationValue(
    value: number | undefined,
    fieldName: string,
    minimum: number,
    maximum?: number,
): void {
    if (value === undefined) {
        return;
    }

    if (!Number.isInteger(value) || value < minimum) {
        throw new Error(
            `${fieldName} must be an integer greater than or equal to ${minimum}.`,
        );
    }

    if (maximum !== undefined && value > maximum) {
        throw new Error(
            `${fieldName} must be less than or equal to ${maximum}.`,
        );
    }
}

function validateBatchListFilters(
    filters: ImportBatchListParams,
): void {
    validatePaginationValue(
        filters.skip,
        "Skip",
        0,
    );

    validatePaginationValue(
        filters.limit,
        "Limit",
        1,
        200,
    );
}

function validateRowListFilters(
    filters: ImportRowListParams,
): void {
    validatePaginationValue(
        filters.skip,
        "Skip",
        0,
    );

    validatePaginationValue(
        filters.limit,
        "Limit",
        1,
        500,
    );
}

function validateCsvFile(file: File): void {
    if (
        typeof File === "undefined" ||
        !(file instanceof File)
    ) {
        throw new Error(
            "Please select a CSV file to upload.",
        );
    }

    const fileName = file.name.trim().toLowerCase();

    if (!fileName.endsWith(".csv")) {
        throw new Error(
            "Only CSV files can be uploaded.",
        );
    }

    if (file.size === 0) {
        throw new Error(
            "The selected CSV file is empty.",
        );
    }

    if (file.size > MAX_CSV_FILE_SIZE_BYTES) {
        throw new Error(
            "The selected CSV file is larger than the 10 MB upload limit.",
        );
    }
}

function normaliseRequiredText(
    value: string | null | undefined,
    fieldName: string,
): string {
    const normalisedValue = value?.trim();

    if (!normalisedValue) {
        throw new Error(`${fieldName} is required.`);
    }

    return normalisedValue;
}

function createReasonFormData(
    reason?: string | null,
): FormData {
    const formData = new FormData();
    const normalisedReason = reason?.trim();

    if (normalisedReason) {
        formData.append("reason", normalisedReason);
    }

    return formData;
}

export async function createImportBatch(
    payload: ImportBatchCreate,
    token?: string,
): Promise<ImportBatchRead> {
    const importType = normaliseRequiredText(
        payload.import_type,
        "Import type",
    );

    const originalFilename = normaliseRequiredText(
        payload.original_filename,
        "Original filename",
    );

    return apiPost<ImportBatchRead>(
        "/import-batches",
        {
            ...payload,
            import_type: importType,
            original_filename: originalFilename,
        },
        resolveAuthToken(token),
    );
}

export async function listImportBatches(
    filters: ImportBatchListParams = {},
    token?: string,
): Promise<ImportBatchSummary[]> {
    validateBatchListFilters(filters);

    const query = buildQueryString({
        import_type: filters.import_type,
        status: filters.status,
        include_archived: filters.include_archived,

        // Backend uses offset rather than skip.
        offset: filters.skip,
        limit: filters.limit,
    });

    return apiGet<ImportBatchSummary[]>(
        `/import-batches${query}`,
        resolveAuthToken(token),
    );
}

export async function countImportBatches(
    filters: ImportBatchCountParams = {},
    token?: string,
): Promise<number> {
    const query = buildQueryString({
        import_type: filters.import_type,
        status: filters.status,
        include_archived: filters.include_archived,
    });

    const response = await apiGet<
        ImportCountResponse | number
    >(
        `/import-batches/count${query}`,
        resolveAuthToken(token),
    );

    return normaliseCountResponse(response);
}

export async function getImportBatch(
    batchId: number,
    options: ImportBatchReadOptions = {},
    token?: string,
): Promise<ImportBatchRead> {
    assertPositiveInteger(batchId, "Batch ID");

    const query = buildQueryString({
        include_archived: options.includeArchived,
    });

    return apiGet<ImportBatchRead>(
        `/import-batches/${batchId}${query}`,
        resolveAuthToken(token),
    );
}

/**
 * Return lightweight progress data for an import batch.
 *
 * This endpoint is suitable for polling while validation or processing is
 * active because it does not load the batch's individual rows.
 */
export async function getImportBatchProgress(
    batchId: number,
    options: ImportBatchProgressOptions = {},
    token?: string,
): Promise<ImportBatchProgress> {
    assertPositiveInteger(batchId, "Batch ID");

    const query = buildQueryString({
        include_archived: options.includeArchived,
    });

    return apiGet<ImportBatchProgress>(
        `/import-batches/${batchId}/progress${query}`,
        resolveAuthToken(token),
    );
}

export async function uploadImportCsv(
    batchId: number,
    file: File,
    options: UploadImportCsvOptions = {},
    token?: string,
): Promise<ImportBatchRead> {
    assertPositiveInteger(batchId, "Batch ID");
    validateCsvFile(file);

    const formData = new FormData();

    formData.append(
        "file",
        file,
        file.name,
    );

    formData.append(
        "replace_existing",
        String(options.replaceExisting ?? false),
    );

    return apiPostForm<ImportBatchRead>(
        `/import-batches/${batchId}/upload`,
        formData,
        resolveAuthToken(token),
    );
}

/**
 * Queue a validated import batch for background processing.
 */
export async function processImportBatch(
    batchId: number,
    token?: string,
): Promise<ImportBatchRead> {
    assertPositiveInteger(batchId, "Batch ID");

    return apiPost<ImportBatchRead>(
        `/import-batches/${batchId}/process`,
        undefined,
        resolveAuthToken(token),
    );
}

export async function listImportRows(
    batchId: number,
    filters: ImportRowListParams = {},
    token?: string,
): Promise<ImportRowRead[]> {
    assertPositiveInteger(batchId, "Batch ID");
    validateRowListFilters(filters);

    const query = buildQueryString({
        status: filters.status,

        // Backend uses offset rather than skip.
        offset: filters.skip,
        limit: filters.limit,
    });

    return apiGet<ImportRowRead[]>(
        `/import-batches/${batchId}/rows${query}`,
        resolveAuthToken(token),
    );
}

export async function countImportRows(
    batchId: number,
    filters: ImportRowCountParams = {},
    token?: string,
): Promise<number> {
    assertPositiveInteger(batchId, "Batch ID");

    const query = buildQueryString({
        status: filters.status,
    });

    const response = await apiGet<
        ImportCountResponse | number
    >(
        `/import-batches/${batchId}/rows/count${query}`,
        resolveAuthToken(token),
    );

    return normaliseCountResponse(response);
}

export async function getImportRow(
    batchId: number,
    rowId: number,
    token?: string,
): Promise<ImportRowRead> {
    assertPositiveInteger(batchId, "Batch ID");
    assertPositiveInteger(rowId, "Row ID");

    return apiGet<ImportRowRead>(
        `/import-batches/${batchId}/rows/${rowId}`,
        resolveAuthToken(token),
    );
}

export async function cancelImportBatch(
    batchId: number,
    options: ImportBatchActionOptions = {},
    token?: string,
): Promise<ImportBatchRead> {
    assertPositiveInteger(batchId, "Batch ID");

    return apiPostForm<ImportBatchRead>(
        `/import-batches/${batchId}/cancel`,
        createReasonFormData(options.reason),
        resolveAuthToken(token),
    );
}

export async function archiveImportBatch(
    batchId: number,
    options: ImportBatchActionOptions = {},
    token?: string,
): Promise<ImportBatchRead> {
    assertPositiveInteger(batchId, "Batch ID");

    return apiPostForm<ImportBatchRead>(
        `/import-batches/${batchId}/archive`,
        createReasonFormData(options.reason),
        resolveAuthToken(token),
    );
}

export async function restoreImportBatch(
    batchId: number,
    token?: string,
): Promise<ImportBatchRead> {
    assertPositiveInteger(batchId, "Batch ID");

    return apiPost<ImportBatchRead>(
        `/import-batches/${batchId}/restore`,
        undefined,
        resolveAuthToken(token),
    );
}