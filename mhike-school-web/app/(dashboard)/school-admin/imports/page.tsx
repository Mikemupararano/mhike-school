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
} from "lucide-react";

import ImportBatchTable, {
    type ImportBatchTableItem,
} from "@/components/imports/ImportBatchTable";
import ImportFilters, {
    type ImportFiltersValue,
} from "@/components/imports/ImportFilters";
import ImportSummaryCard from "@/components/imports/ImportSummaryCard";
import ImportUploadPanel, {
    type ImportUploadPayload,
} from "@/components/imports/ImportUploadPanel";
import {
    archiveImportBatch,
    cancelImportBatch,
    countImportBatches,
    createImportBatch,
    listImportBatches,
    restoreImportBatch,
    uploadImportCsv,
} from "@/lib/importApi";

import type {
    ImportBatchCountParams,
    ImportBatchCreate,
    ImportBatchListParams,
    ImportBatchRead,
    ImportBatchSummary,
} from "@/types/import";

const PAGE_SIZE = 20;
const DEFAULT_UPLOAD_IMPORT_TYPE = "students";

const DEFAULT_FILTERS: ImportFiltersValue = {
    search: "",
    importType: "",
    status: "",
    archive: "active",
};

type UnknownRecord = Record<string, unknown>;

type SummaryCounts = {
    visible: number;
    completed: number;
    processing: number;
    failed: number;
};

type SummaryCardProps = {
    title?: string;
    label?: string;
    value?: number;
    count?: number;
    description?: string;
    icon?: ReactNode;
    tone?: string;
};

const SummaryCard =
    ImportSummaryCard as React.ComponentType<SummaryCardProps>;

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

function asString(
    value: unknown,
    fallback = "",
): string {
    return typeof value === "string"
        ? value
        : fallback;
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
        const parsed = Number(value);

        if (Number.isFinite(parsed)) {
            return parsed;
        }
    }

    return fallback;
}

function asNullableString(
    value: unknown,
): string | null {
    if (
        typeof value === "string" &&
        value.trim()
    ) {
        return value;
    }

    return null;
}

function asOptionalFilterValue<
    T extends string,
>(
    value: string,
): T | undefined {
    const normalisedValue =
        value.trim();

    return normalisedValue
        ? normalisedValue as T
        : undefined;
}

function extractValidationMessage(
    details: unknown,
): string | null {
    if (!Array.isArray(details)) {
        return null;
    }

    const messages = details
        .map((detail) => {
            const record =
                asRecord(detail);

            const location =
                Array.isArray(record.loc)
                    ? record.loc
                        .map(
                            (part) =>
                                String(part),
                        )
                        .filter(
                            (part) =>
                                part !== "body" &&
                                part !== "query",
                        )
                        .join(".")
                    : "";

            const message =
                asString(record.msg);

            if (!message) {
                return null;
            }

            return location
                ? `${location}: ${message}`
                : message;
        })
        .filter(
            (
                message,
            ): message is string =>
                Boolean(message),
        );

    return messages.length > 0
        ? messages.join("; ")
        : null;
}

function parseErrorPayload(
    value: unknown,
): string | null {
    if (typeof value === "string") {
        const trimmed =
            value.trim();

        if (!trimmed) {
            return null;
        }

        try {
            return parseErrorPayload(
                JSON.parse(
                    trimmed,
                ) as unknown,
            );
        } catch {
            return trimmed;
        }
    }

    const record =
        asRecord(value);

    if (
        record.error !== undefined
    ) {
        const nestedMessage =
            parseErrorPayload(
                record.error,
            );

        if (nestedMessage) {
            return nestedMessage;
        }
    }

    const validationMessage =
        extractValidationMessage(
            record.details ??
            record.detail,
        );

    if (validationMessage) {
        return validationMessage;
    }

    if (
        typeof record.detail ===
        "string"
    ) {
        return record.detail;
    }

    if (
        typeof record.message ===
        "string"
    ) {
        return record.message;
    }

    return null;
}

function getErrorMessage(
    error: unknown,
): string {
    if (error instanceof Error) {
        return (
            parseErrorPayload(
                error.message,
            ) ??
            error.message
        );
    }

    return (
        parseErrorPayload(error) ??
        "Something went wrong while processing the import request."
    );
}

function mapBatch(
    value:
        | ImportBatchSummary
        | ImportBatchRead,
): ImportBatchTableItem {
    const batch =
        value as unknown as UnknownRecord;

    const id = asNumber(
        batch.id,
        Number.NaN,
    );

    if (
        !Number.isInteger(id) ||
        id <= 0
    ) {
        throw new Error(
            "The import service returned a batch with an invalid ID.",
        );
    }

    const isArchived =
        batch.is_archived === true;

    const archivedAt =
        asNullableString(
            batch.archived_at,
        ) ??
        (
            isArchived
                ? asNullableString(
                    batch.updated_at,
                )
                : null
        );

    return {
        id,

        import_type:
            asString(
                batch.import_type,
                "unknown",
            ),

        filename:
            asNullableString(
                batch.original_filename ??
                batch.filename,
            ),

        status:
            asString(
                batch.status,
                "pending",
            ),

        total_rows:
            asNumber(
                batch.total_rows,
            ),

        valid_rows:
            asNumber(
                batch.valid_rows,
            ),

        invalid_rows:
            asNumber(
                batch.invalid_rows ??
                batch.failed_rows,
            ),

        imported_rows:
            asNumber(
                batch.successful_rows ??
                batch.imported_rows ??
                batch.processed_rows,
            ),

        created_at:
            asString(
                batch.created_at,
                new Date()
                    .toISOString(),
            ),

        updated_at:
            asNullableString(
                batch.updated_at,
            ),

        archived_at:
            archivedAt,
    };
}

function isCompletedStatus(
    status: string,
): boolean {
    return [
        "completed",
        "completed_with_errors",
        "partially_completed",
    ].includes(
        normaliseStatus(status),
    );
}

function isProcessingStatus(
    status: string,
): boolean {
    return [
        "pending",
        "uploading",
        "uploaded",
        "staged",
        "parsing",
        "validating",
        "validated",
        "ready",
        "queued",
        "processing",
        "importing",
    ].includes(
        normaliseStatus(status),
    );
}

function isFailedStatus(
    status: string,
): boolean {
    return [
        "failed",
        "cancelled",
    ].includes(
        normaliseStatus(status),
    );
}

function matchesSearch(
    batch: ImportBatchTableItem,
    search: string,
): boolean {
    const query =
        search
            .trim()
            .toLowerCase();

    if (!query) {
        return true;
    }

    return [
        String(batch.id),
        batch.import_type,
        batch.filename ?? "",
        batch.status,
    ].some((value) =>
        value
            .toLowerCase()
            .includes(query),
    );
}

export default function SchoolAdminImportsPage() {
    const [
        batches,
        setBatches,
    ] = useState<
        ImportBatchTableItem[]
    >([]);

    const [
        serverTotalItems,
        setServerTotalItems,
    ] = useState(0);

    const [
        page,
        setPage,
    ] = useState(1);

    const [
        filters,
        setFilters,
    ] = useState<ImportFiltersValue>(
        DEFAULT_FILTERS,
    );

    const [
        isLoading,
        setIsLoading,
    ] = useState(true);

    const [
        isUploading,
        setIsUploading,
    ] = useState(false);

    const [
        actionBatchId,
        setActionBatchId,
    ] = useState<number | null>(
        null,
    );

    const [
        errorMessage,
        setErrorMessage,
    ] = useState<string | null>(
        null,
    );

    const [
        successMessage,
        setSuccessMessage,
    ] = useState<string | null>(
        null,
    );

    const loadBatches =
        useCallback(
            async (): Promise<void> => {
                setIsLoading(true);
                setErrorMessage(null);

                try {
                    const includeArchived =
                        filters.archive !==
                        "active";

                    const importType =
                        asOptionalFilterValue<
                            NonNullable<
                                ImportBatchListParams[
                                "import_type"
                                ]
                            >
                        >(
                            filters.importType,
                        );

                    const status =
                        asOptionalFilterValue<
                            NonNullable<
                                ImportBatchListParams[
                                "status"
                                ]
                            >
                        >(
                            filters.status,
                        );

                    const listFilters:
                        ImportBatchListParams =
                    {
                        import_type:
                            importType,

                        status,

                        include_archived:
                            includeArchived,

                        skip:
                            (
                                page -
                                1
                            ) *
                            PAGE_SIZE,

                        limit:
                            PAGE_SIZE,
                    };

                    const countFilters:
                        ImportBatchCountParams =
                    {
                        import_type:
                            importType,

                        status,

                        include_archived:
                            includeArchived,
                    };

                    const [
                        batchResponse,
                        totalResponse,
                    ] =
                        await Promise.all(
                            [
                                listImportBatches(
                                    listFilters,
                                ),

                                countImportBatches(
                                    countFilters,
                                ),
                            ],
                        );

                    const mappedBatches =
                        batchResponse.map(
                            mapBatch,
                        );

                    const archiveFiltered =
                        filters.archive ===
                            "archived"
                            ? mappedBatches.filter(
                                (batch) =>
                                    batch.archived_at !==
                                    null,
                            )
                            : filters.archive ===
                                "active"
                                ? mappedBatches.filter(
                                    (batch) =>
                                        batch.archived_at ===
                                        null,
                                )
                                : mappedBatches;

                    setBatches(
                        archiveFiltered,
                    );

                    setServerTotalItems(
                        totalResponse,
                    );
                } catch (error) {
                    setBatches([]);
                    setServerTotalItems(
                        0,
                    );

                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                } finally {
                    setIsLoading(
                        false,
                    );
                }
            },
            [
                filters.archive,
                filters.importType,
                filters.status,
                page,
            ],
        );

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

    const visibleBatches =
        useMemo(
            () =>
                batches.filter(
                    (batch) =>
                        matchesSearch(
                            batch,
                            filters.search,
                        ),
                ),
            [
                batches,
                filters.search,
            ],
        );

    const totalItems =
        filters.search.trim() ||
            filters.archive ===
            "archived"
            ? visibleBatches.length
            : serverTotalItems;

    const summary =
        useMemo<SummaryCounts>(
            () =>
                visibleBatches.reduce<SummaryCounts>(
                    (
                        counts,
                        batch,
                    ) => {
                        counts.visible +=
                            1;

                        if (
                            isCompletedStatus(
                                batch.status,
                            )
                        ) {
                            counts.completed +=
                                1;
                        }

                        if (
                            isProcessingStatus(
                                batch.status,
                            )
                        ) {
                            counts.processing +=
                                1;
                        }

                        if (
                            isFailedStatus(
                                batch.status,
                            )
                        ) {
                            counts.failed +=
                                1;
                        }

                        return counts;
                    },
                    {
                        visible: 0,
                        completed: 0,
                        processing: 0,
                        failed: 0,
                    },
                ),
            [visibleBatches],
        );

    async function handleUpload(
        payload: ImportUploadPayload,
    ): Promise<void> {
        setIsUploading(true);
        setErrorMessage(null);
        setSuccessMessage(null);

        let createdBatchId:
            number | null =
            null;

        try {
            const importType =
                payload.importType.trim();

            if (!importType) {
                throw new Error(
                    "Please select an import type before uploading the CSV file.",
                );
            }

            const createPayload:
                ImportBatchCreate =
            {
                import_type:
                    importType,

                operation:
                    "create",

                original_filename:
                    payload.file.name,
            };

            const createdBatch =
                await createImportBatch(
                    createPayload,
                );

            createdBatchId =
                createdBatch.id;

            await uploadImportCsv(
                createdBatch.id,
                payload.file,
            );

            setSuccessMessage(
                `${payload.file.name} was uploaded successfully as import batch #${createdBatch.id}.`,
            );

            setPage(1);

            await loadBatches();
        } catch (error) {
            const originalMessage =
                getErrorMessage(error);

            setErrorMessage(
                createdBatchId !==
                    null
                    ? `${originalMessage} Import batch #${createdBatchId} was created, but its CSV upload did not complete.`
                    : originalMessage,
            );

            throw error;
        } finally {
            setIsUploading(
                false,
            );
        }
    }

    async function runBatchAction(
        batchId: number,
        action: (
            id: number,
        ) => Promise<ImportBatchRead>,
        successText: string,
    ): Promise<void> {
        setActionBatchId(batchId);
        setErrorMessage(null);
        setSuccessMessage(null);

        try {
            await action(batchId);

            setSuccessMessage(
                successText,
            );

            await loadBatches();
        } catch (error) {
            setErrorMessage(
                getErrorMessage(
                    error,
                ),
            );
        } finally {
            setActionBatchId(
                null,
            );
        }
    }

    async function handleCancel(
        batch:
            ImportBatchTableItem,
    ): Promise<void> {
        const confirmed =
            window.confirm(
                `Cancel import batch #${batch.id}?`,
            );

        if (!confirmed) {
            return;
        }

        await runBatchAction(
            batch.id,
            cancelImportBatch,
            `Import batch #${batch.id} was cancelled.`,
        );
    }

    async function handleArchive(
        batch:
            ImportBatchTableItem,
    ): Promise<void> {
        await runBatchAction(
            batch.id,
            archiveImportBatch,
            `Import batch #${batch.id} was archived.`,
        );
    }

    async function handleRestore(
        batch:
            ImportBatchTableItem,
    ): Promise<void> {
        await runBatchAction(
            batch.id,
            restoreImportBatch,
            `Import batch #${batch.id} was restored.`,
        );
    }

    function handleFiltersChange(
        nextFilters:
            ImportFiltersValue,
    ): void {
        setErrorMessage(null);
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
                            disabled={
                                isLoading ||
                                isUploading
                            }
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

                            <p className="mt-1 text-sm leading-6">
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
                        value={
                            summary.visible
                        }
                        count={
                            summary.visible
                        }
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
                        value={
                            summary.completed
                        }
                        count={
                            summary.completed
                        }
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
                        value={
                            summary.processing
                        }
                        count={
                            summary.processing
                        }
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
                        value={
                            summary.failed
                        }
                        count={
                            summary.failed
                        }
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
                    <ImportUploadPanel
                        defaultImportType={
                            DEFAULT_UPLOAD_IMPORT_TYPE
                        }
                        isUploading={
                            isUploading
                        }
                        disabled={
                            isLoading
                        }
                        errorMessage={
                            null
                        }
                        successMessage={
                            null
                        }
                        onSelectionChange={() => {
                            setErrorMessage(
                                null,
                            );

                            setSuccessMessage(
                                null,
                            );
                        }}
                        onUpload={
                            handleUpload
                        }
                    />
                </section>

                <section className="mb-6">
                    <ImportFilters
                        value={filters}
                        onChange={
                            handleFiltersChange
                        }
                        isLoading={
                            isLoading
                        }
                        onRefresh={
                            loadBatches
                        }
                    />
                </section>

                <ImportBatchTable
                    batches={
                        visibleBatches
                    }
                    isLoading={
                        isLoading
                    }
                    errorMessage={null}
                    page={page}
                    pageSize={
                        PAGE_SIZE
                    }
                    totalItems={
                        totalItems
                    }
                    onPageChange={
                        setPage
                    }
                    onCancel={
                        handleCancel
                    }
                    onArchive={
                        handleArchive
                    }
                    onRestore={
                        handleRestore
                    }
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