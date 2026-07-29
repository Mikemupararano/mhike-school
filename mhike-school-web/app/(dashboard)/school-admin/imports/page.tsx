"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import {
    AlertCircle,
    CheckCircle2,
    CircleX,
    Clock3,
    FileSpreadsheet,
    RefreshCcw,
    Upload,
} from "lucide-react";

import ImportBatchTable, {
    type ImportBatchTableItem,
} from "@/components/imports/ImportBatchTable";
import ImportFilters, {
    type ImportFiltersValue,
} from "@/components/imports/ImportFilters";
import ImportSummaryCard from "@/components/imports/ImportSummaryCard";
import ImportUploadPanel from "@/components/imports/ImportUploadPanel";
import * as importApiModule from "@/lib/importApi";

const PAGE_SIZE = 20;

const DEFAULT_FILTERS: ImportFiltersValue = {
    search: "",
    importType: "",
    status: "",
    archive: "active",
};

type UnknownRecord = Record<string, unknown>;

type UnknownFunction = (
    ...args: unknown[]
) => unknown | Promise<unknown>;

type ImportBatchListResponse = {
    items: ImportBatchTableItem[];
    total: number;
};

type SummaryCounts = {
    visible: number;
    completed: number;
    processing: number;
    failed: number;
};

/*
 * These compatibility props document the contract expected by this page.
 * Icons are React elements, not Lucide component constructors.
 */
type SummaryCardProps = {
    title?: string;
    label?: string;
    value?: number;
    count?: number;
    description?: string;
    icon?: ReactNode;
    tone?: string;
};

type UploadPanelProps = {
    isUploading?: boolean;
    isLoading?: boolean;
    onUpload?: (
        payload: unknown,
        importType?: unknown,
    ) => Promise<void> | void;
    onSubmit?: (
        payload: unknown,
        importType?: unknown,
    ) => Promise<void> | void;
    title?: string;
    description?: string;
    icon?: ReactNode;
};

const SummaryCard =
    ImportSummaryCard as React.ComponentType<SummaryCardProps>;

const UploadPanel =
    ImportUploadPanel as React.ComponentType<UploadPanelProps>;

function normaliseStatus(status: string): string {
    return status
        .trim()
        .toLowerCase()
        .replace(/[\s-]+/g, "_");
}

function asRecord(value: unknown): UnknownRecord {
    if (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
    ) {
        return value as UnknownRecord;
    }

    return {};
}

function asNumber(
    value: unknown,
    fallback = 0,
): number {
    if (
        typeof value === "number" &&
        Number.isFinite(value)
    ) {
        return value;
    }

    if (
        typeof value === "string" &&
        value.trim()
    ) {
        const parsedValue = Number(value);

        if (Number.isFinite(parsedValue)) {
            return parsedValue;
        }
    }

    return fallback;
}

function asString(
    value: unknown,
    fallback = "",
): string {
    return typeof value === "string"
        ? value
        : fallback;
}

function asNullableString(
    value: unknown,
): string | null {
    return typeof value === "string" &&
        value.trim()
        ? value
        : null;
}

function getApiFunction(
    possibleNames: readonly string[],
): UnknownFunction | null {
    const moduleRecord =
        importApiModule as UnknownRecord;

    for (const name of possibleNames) {
        const candidate = moduleRecord[name];

        if (typeof candidate === "function") {
            return candidate as UnknownFunction;
        }
    }

    return null;
}

async function invokeApi(
    possibleNames: readonly string[],
    ...args: unknown[]
): Promise<unknown> {
    const apiFunction =
        getApiFunction(possibleNames);

    if (!apiFunction) {
        throw new Error(
            [
                "The required import API function is unavailable.",
                `Expected one of: ${possibleNames.join(", ")}.`,
            ].join(" "),
        );
    }

    return await apiFunction(...args);
}

function getErrorMessage(
    error: unknown,
): string {
    if (error instanceof Error) {
        return error.message;
    }

    if (typeof error === "string") {
        return error;
    }

    const record = asRecord(error);

    if (typeof record.detail === "string") {
        return record.detail;
    }

    if (typeof record.message === "string") {
        return record.message;
    }

    return "Something went wrong while processing the import request.";
}

function mapBatch(
    value: unknown,
): ImportBatchTableItem | null {
    const batch = asRecord(value);
    const id = asNumber(
        batch.id,
        Number.NaN,
    );

    if (!Number.isFinite(id)) {
        return null;
    }

    const totalRows = asNumber(
        batch.total_rows ??
        batch.totalRows,
        0,
    );

    const validRows = asNumber(
        batch.valid_rows ??
        batch.validRows ??
        batch.validated_rows ??
        batch.validatedRows,
        0,
    );

    const invalidRows = asNumber(
        batch.invalid_rows ??
        batch.invalidRows ??
        batch.failed_rows ??
        batch.failedRows,
        0,
    );

    const importedRows = asNumber(
        batch.imported_rows ??
        batch.importedRows ??
        batch.successful_rows ??
        batch.successfulRows ??
        batch.processed_rows ??
        batch.processedRows,
        0,
    );

    return {
        id,
        import_type: asString(
            batch.import_type ??
            batch.importType,
            "unknown",
        ),
        filename: asNullableString(
            batch.filename ??
            batch.file_name ??
            batch.original_filename ??
            batch.originalFilename,
        ),
        status: asString(
            batch.status,
            "uploaded",
        ),
        total_rows: totalRows,
        valid_rows: validRows,
        invalid_rows: invalidRows,
        imported_rows: importedRows,
        created_at: asString(
            batch.created_at ??
            batch.createdAt,
            new Date().toISOString(),
        ),
        updated_at: asNullableString(
            batch.updated_at ??
            batch.updatedAt,
        ),
        archived_at: asNullableString(
            batch.archived_at ??
            batch.archivedAt,
        ),
    };
}

function mapBatchListResponse(
    value: unknown,
): ImportBatchListResponse {
    if (Array.isArray(value)) {
        const items = value
            .map(mapBatch)
            .filter(
                (
                    batch,
                ): batch is ImportBatchTableItem =>
                    batch !== null,
            );

        return {
            items,
            total: items.length,
        };
    }

    const response = asRecord(value);

    const rawItems =
        response.items ??
        response.results ??
        response.batches ??
        response.data ??
        [];

    const items = Array.isArray(rawItems)
        ? rawItems
            .map(mapBatch)
            .filter(
                (
                    batch,
                ): batch is ImportBatchTableItem =>
                    batch !== null,
            )
        : [];

    return {
        items,
        total: asNumber(
            response.total ??
            response.total_items ??
            response.totalItems ??
            response.count,
            items.length,
        ),
    };
}

function isCompletedStatus(
    status: string,
): boolean {
    return [
        "completed",
        "completed_with_errors",
        "partially_completed",
    ].includes(normaliseStatus(status));
}

function isProcessingStatus(
    status: string,
): boolean {
    return [
        "uploaded",
        "parsing",
        "validating",
        "ready",
        "queued",
        "processing",
        "importing",
        "pending",
        "created",
    ].includes(normaliseStatus(status));
}

function isFailedStatus(
    status: string,
): boolean {
    return [
        "failed",
        "cancelled",
    ].includes(normaliseStatus(status));
}

function extractUploadPayload(
    value: unknown,
    possibleImportType?: unknown,
): {
    file: File;
    importType: string;
} {
    if (value instanceof File) {
        return {
            file: value,
            importType:
                typeof possibleImportType === "string"
                    ? possibleImportType
                    : "",
        };
    }

    const payload = asRecord(value);
    const file = payload.file;

    if (!(file instanceof File)) {
        throw new Error(
            "Please choose a CSV file before uploading.",
        );
    }

    return {
        file,
        importType: asString(
            payload.importType ??
            payload.import_type,
        ),
    };
}

export default function SchoolAdminImportsPage() {
    const [batches, setBatches] = useState<
        ImportBatchTableItem[]
    >([]);

    const [totalItems, setTotalItems] =
        useState(0);

    const [page, setPage] =
        useState(1);

    const [filters, setFilters] =
        useState<ImportFiltersValue>(
            DEFAULT_FILTERS,
        );

    const [isLoading, setIsLoading] =
        useState(true);

    const [isUploading, setIsUploading] =
        useState(false);

    const [
        actionBatchId,
        setActionBatchId,
    ] = useState<number | null>(null);

    const [
        errorMessage,
        setErrorMessage,
    ] = useState<string | null>(null);

    const [
        successMessage,
        setSuccessMessage,
    ] = useState<string | null>(null);

    const loadBatches =
        useCallback(async (): Promise<void> => {
            setIsLoading(true);
            setErrorMessage(null);

            try {
                const query = {
                    page,
                    page_size: PAGE_SIZE,
                    pageSize: PAGE_SIZE,
                    search:
                        filters.search.trim() ||
                        undefined,
                    import_type:
                        filters.importType ||
                        undefined,
                    importType:
                        filters.importType ||
                        undefined,
                    status:
                        filters.status ||
                        undefined,
                    archived:
                        filters.archive === "all"
                            ? undefined
                            : filters.archive ===
                            "archived",
                    include_archived:
                        filters.archive === "all",
                };

                const response =
                    await invokeApi(
                        [
                            "listImportBatches",
                            "getImportBatches",
                            "fetchImportBatches",
                        ],
                        query,
                    );

                const mappedResponse =
                    mapBatchListResponse(
                        response,
                    );

                setBatches(
                    mappedResponse.items,
                );

                setTotalItems(
                    mappedResponse.total,
                );
            } catch (error) {
                setBatches([]);
                setTotalItems(0);
                setErrorMessage(
                    getErrorMessage(error),
                );
            } finally {
                setIsLoading(false);
            }
        }, [
            filters.archive,
            filters.importType,
            filters.search,
            filters.status,
            page,
        ]);

    useEffect(() => {
        void loadBatches();
    }, [loadBatches]);

    useEffect(() => {
        setPage(1);
    }, [
        filters.search,
        filters.importType,
        filters.status,
        filters.archive,
    ]);

    const summary =
        useMemo<SummaryCounts>(() => {
            return batches.reduce<SummaryCounts>(
                (counts, batch) => {
                    counts.visible += 1;

                    if (
                        isCompletedStatus(
                            batch.status,
                        )
                    ) {
                        counts.completed += 1;
                    }

                    if (
                        isProcessingStatus(
                            batch.status,
                        )
                    ) {
                        counts.processing += 1;
                    }

                    if (
                        isFailedStatus(
                            batch.status,
                        )
                    ) {
                        counts.failed += 1;
                    }

                    return counts;
                },
                {
                    visible: 0,
                    completed: 0,
                    processing: 0,
                    failed: 0,
                },
            );
        }, [batches]);

    async function handleUpload(
        value: unknown,
        possibleImportType?: unknown,
    ): Promise<void> {
        setIsUploading(true);
        setErrorMessage(null);
        setSuccessMessage(null);

        try {
            const {
                file,
                importType,
            } = extractUploadPayload(
                value,
                possibleImportType,
            );

            const uploadFunction =
                getApiFunction([
                    "uploadImportFile",
                    "uploadImportBatch",
                    "createImportBatch",
                ]);

            if (!uploadFunction) {
                throw new Error(
                    "The import upload API function is unavailable.",
                );
            }

            /*
             * Current import clients may use either:
             *   upload(file, importType)
             * or:
             *   upload({ file, importType })
             *
             * Function arity is used to select the contract without
             * swallowing a genuine server-side upload failure.
             */
            if (uploadFunction.length >= 2) {
                await uploadFunction(
                    file,
                    importType,
                );
            } else {
                await uploadFunction({
                    file,
                    import_type: importType,
                    importType,
                });
            }

            setSuccessMessage(
                `${file.name} was uploaded successfully.`,
            );

            setPage(1);
            await loadBatches();
        } catch (error) {
            const message =
                getErrorMessage(error);

            setErrorMessage(message);

            /*
             * The upload panel may use the rejected promise to retain
             * the selected file and show its own local error state.
             */
            throw error;
        } finally {
            setIsUploading(false);
        }
    }

    async function runBatchAction(
        batch: ImportBatchTableItem,
        actionNames: readonly string[],
        successText: string,
    ): Promise<void> {
        setActionBatchId(batch.id);
        setErrorMessage(null);
        setSuccessMessage(null);

        try {
            await invokeApi(
                actionNames,
                batch.id,
            );

            setSuccessMessage(
                successText,
            );

            await loadBatches();
        } catch (error) {
            setErrorMessage(
                getErrorMessage(error),
            );
        } finally {
            setActionBatchId(null);
        }
    }

    async function handleCancel(
        batch: ImportBatchTableItem,
    ): Promise<void> {
        const confirmed =
            window.confirm(
                `Cancel import batch #${batch.id}?`,
            );

        if (!confirmed) {
            return;
        }

        await runBatchAction(
            batch,
            ["cancelImportBatch"],
            `Import batch #${batch.id} was cancelled.`,
        );
    }

    async function handleArchive(
        batch: ImportBatchTableItem,
    ): Promise<void> {
        await runBatchAction(
            batch,
            ["archiveImportBatch"],
            `Import batch #${batch.id} was archived.`,
        );
    }

    async function handleRestore(
        batch: ImportBatchTableItem,
    ): Promise<void> {
        await runBatchAction(
            batch,
            [
                "restoreImportBatch",
                "unarchiveImportBatch",
            ],
            `Import batch #${batch.id} was restored.`,
        );
    }

    function handleFiltersChange(
        nextFilters: ImportFiltersValue,
    ): void {
        setSuccessMessage(null);
        setFilters(nextFilters);
    }

    return (
        <main className="min-h-screen bg-slate-50">
            <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
                <header className="mb-6 overflow-hidden rounded-3xl bg-slate-950 px-6 py-7 text-white shadow-xl sm:px-8">
                    <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                        <div className="flex items-start gap-4">
                            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600">
                                <FileSpreadsheet
                                    className="h-7 w-7"
                                    aria-hidden="true"
                                />
                            </span>

                            <div>
                                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-300">
                                    School administration
                                </p>

                                <h1 className="mt-1 text-2xl font-bold sm:text-3xl">
                                    Data imports
                                </h1>

                                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300 sm:text-base">
                                    Upload CSV files,
                                    validate records and
                                    monitor every import
                                    batch from one place.
                                </p>
                            </div>
                        </div>

                        <button
                            type="button"
                            disabled={isLoading}
                            className={[
                                "inline-flex min-h-11 items-center justify-center",
                                "gap-2 rounded-xl border border-white/20",
                                "bg-white/10 px-5 text-sm font-semibold",
                                "text-white transition hover:bg-white/20",
                                "disabled:cursor-not-allowed disabled:opacity-50",
                            ].join(" ")}
                            onClick={() => {
                                void loadBatches();
                            }}
                        >
                            <RefreshCcw
                                className={[
                                    "h-4 w-4",
                                    isLoading
                                        ? "animate-spin"
                                        : "",
                                ]
                                    .filter(Boolean)
                                    .join(" ")}
                                aria-hidden="true"
                            />

                            Refresh imports
                        </button>
                    </div>
                </header>

                {errorMessage ? (
                    <div
                        role="alert"
                        className="mb-5 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-red-900"
                    >
                        <AlertCircle
                            className="mt-0.5 h-5 w-5 shrink-0"
                            aria-hidden="true"
                        />

                        <div>
                            <p className="font-bold">
                                Import request failed
                            </p>

                            <p className="mt-1 text-sm">
                                {errorMessage}
                            </p>
                        </div>
                    </div>
                ) : null}

                {successMessage ? (
                    <div
                        role="status"
                        className="mb-5 flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-emerald-900"
                    >
                        <CheckCircle2
                            className="mt-0.5 h-5 w-5 shrink-0"
                            aria-hidden="true"
                        />

                        <p className="text-sm font-semibold">
                            {successMessage}
                        </p>
                    </div>
                ) : null}

                <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <SummaryCard
                        title="Visible batches"
                        label="Visible batches"
                        value={summary.visible}
                        count={summary.visible}
                        description="Batches on the current page"
                        icon={
                            <FileSpreadsheet
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        }
                        tone="blue"
                    />

                    <SummaryCard
                        title="Completed"
                        label="Completed"
                        value={summary.completed}
                        count={summary.completed}
                        description="Completed successfully or with row errors"
                        icon={
                            <CheckCircle2
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        }
                        tone="green"
                    />

                    <SummaryCard
                        title="In progress"
                        label="In progress"
                        value={summary.processing}
                        count={summary.processing}
                        description="Uploaded, validating, queued or processing"
                        icon={
                            <Clock3
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        }
                        tone="amber"
                    />

                    <SummaryCard
                        title="Failed or cancelled"
                        label="Failed or cancelled"
                        value={summary.failed}
                        count={summary.failed}
                        description="Batches requiring attention"
                        icon={
                            <CircleX
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        }
                        tone="red"
                    />
                </section>

                <section className="mb-6">
                    <UploadPanel
                        isUploading={isUploading}
                        isLoading={isUploading}
                        onUpload={handleUpload}
                        onSubmit={handleUpload}
                        title="Upload CSV data"
                        description="Choose an import type and upload a CSV file for validation."
                        icon={
                            <Upload
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        }
                    />
                </section>

                <section className="mb-6">
                    <ImportFilters
                        value={filters}
                        onChange={
                            handleFiltersChange
                        }
                        isLoading={isLoading}
                        onRefresh={
                            loadBatches
                        }
                    />
                </section>

                <ImportBatchTable
                    batches={batches}
                    isLoading={isLoading}
                    errorMessage={null}
                    page={page}
                    pageSize={PAGE_SIZE}
                    totalItems={totalItems}
                    onPageChange={setPage}
                    onCancel={handleCancel}
                    onArchive={handleArchive}
                    onRestore={handleRestore}
                    actionBatchId={
                        actionBatchId
                    }
                    detailsBasePath="/school-admin/imports"
                    emptyTitle="No import batches found"
                    emptyDescription="Upload a CSV file or adjust the filters to view import batches."
                />
            </div>
        </main>
    );
}