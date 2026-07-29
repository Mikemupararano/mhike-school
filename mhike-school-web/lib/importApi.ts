import {
    apiGet,
    apiPost,
    apiPostForm,
} from "@/lib/api";

import type {
    ImportBatchCountParams,
    ImportBatchCreate,
    ImportBatchListParams,
    ImportBatchRead,
    ImportBatchSummary,
    ImportCountResponse,
    ImportRowCountParams,
    ImportRowListParams,
    ImportRowRead,
} from "@/types/import";

type QueryValue =
    | string
    | number
    | boolean
    | null
    | undefined;

function appendQueryParam(
    params: URLSearchParams,
    key: string,
    value: QueryValue,
): void {
    if (value === undefined || value === null) {
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

function normaliseCountResponse(
    response: ImportCountResponse | number,
): number {
    return typeof response === "number"
        ? response
        : response.count;
}

export async function createImportBatch(
    payload: ImportBatchCreate,
    token?: string,
): Promise<ImportBatchRead> {
    return apiPost<ImportBatchRead>(
        "/import-batches",
        payload,
        token,
    );
}

export async function listImportBatches(
    filters: ImportBatchListParams = {},
    token?: string,
): Promise<ImportBatchSummary[]> {
    const query = buildQueryString({
        import_type: filters.import_type,
        operation: filters.operation,
        status: filters.status,
        include_archived: filters.include_archived,
        skip: filters.skip,
        limit: filters.limit,
    });

    return apiGet<ImportBatchSummary[]>(
        `/import-batches${query}`,
        token,
    );
}

export async function countImportBatches(
    filters: ImportBatchCountParams = {},
    token?: string,
): Promise<number> {
    const query = buildQueryString({
        import_type: filters.import_type,
        operation: filters.operation,
        status: filters.status,
        include_archived: filters.include_archived,
    });

    const response = await apiGet<
        ImportCountResponse | number
    >(
        `/import-batches/count${query}`,
        token,
    );

    return normaliseCountResponse(response);
}

export async function getImportBatch(
    batchId: number,
    token?: string,
): Promise<ImportBatchRead> {
    return apiGet<ImportBatchRead>(
        `/import-batches/${batchId}`,
        token,
    );
}

export async function uploadImportCsv(
    batchId: number,
    file: File,
    token?: string,
): Promise<ImportBatchRead> {
    const formData = new FormData();

    formData.append("file", file, file.name);

    return apiPostForm<ImportBatchRead>(
        `/import-batches/${batchId}/upload`,
        formData,
        token,
    );
}

export async function listImportRows(
    batchId: number,
    filters: ImportRowListParams = {},
    token?: string,
): Promise<ImportRowRead[]> {
    const query = buildQueryString({
        status: filters.status,
        skip: filters.skip,
        limit: filters.limit,
    });

    return apiGet<ImportRowRead[]>(
        `/import-batches/${batchId}/rows${query}`,
        token,
    );
}

export async function countImportRows(
    batchId: number,
    filters: ImportRowCountParams = {},
    token?: string,
): Promise<number> {
    const query = buildQueryString({
        status: filters.status,
    });

    const response = await apiGet<
        ImportCountResponse | number
    >(
        `/import-batches/${batchId}/rows/count${query}`,
        token,
    );

    return normaliseCountResponse(response);
}

export async function getImportRow(
    batchId: number,
    rowId: number,
    token?: string,
): Promise<ImportRowRead> {
    return apiGet<ImportRowRead>(
        `/import-batches/${batchId}/rows/${rowId}`,
        token,
    );
}

export async function cancelImportBatch(
    batchId: number,
    token?: string,
): Promise<ImportBatchRead> {
    return apiPost<ImportBatchRead>(
        `/import-batches/${batchId}/cancel`,
        undefined,
        token,
    );
}

export async function archiveImportBatch(
    batchId: number,
    token?: string,
): Promise<ImportBatchRead> {
    return apiPost<ImportBatchRead>(
        `/import-batches/${batchId}/archive`,
        undefined,
        token,
    );
}

export async function restoreImportBatch(
    batchId: number,
    token?: string,
): Promise<ImportBatchRead> {
    return apiPost<ImportBatchRead>(
        `/import-batches/${batchId}/restore`,
        undefined,
        token,
    );
}