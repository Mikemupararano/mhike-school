"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useState,
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
    ImportStatus,
} from "@/types/import";

const PAGE_SIZE = 20;
const BULK_FETCH_PAGE_SIZE = 200;
const DEFAULT_UPLOAD_IMPORT_TYPE = "students";

const DEFAULT_FILTERS: ImportFiltersValue = {
    search: "",
    importType: "",
    status: "",
    archive: "active",
};

const COMPLETED_STATUSES = new Set([
    "completed",
    "completed_with_errors",
    "partially_completed",
]);

const PROCESSING_STATUSES = new Set([
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
]);

const FAILED_STATUSES = new Set([
    "failed",
    "cancelled",
]);

type SummaryCounts = {
    visible: number;
    completed: number;
    processing: number;
    failed: number;
};

function normaliseStatus(
    status: string,
): string {
    return status
        .trim()
        .toLowerCase()
        .replace(/[\s-]+/g, "_");
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

    if (
        typeof error === "object" &&
        error !== null
    ) {
        const record =
            error as Record<
                string,
                unknown
            >;

        if (
            typeof record.detail ===
            "string"
        ) {
            return record.detail;
        }

        if (
            Array.isArray(
                record.detail,
            )
        ) {
            const messages =
                record.detail
                    .map((item) => {
                        if (
                            typeof item !==
                            "object" ||
                            item === null
                        ) {
                            return null;
                        }

                        const detail =
                            item as Record<
                                string,
                                unknown
                            >;

                        const message =
                            typeof detail.msg ===
                                "string"
                                ? detail.msg
                                : null;

                        const location =
                            Array.isArray(
                                detail.loc,
                            )
                                ? detail.loc
                                    .map(String)
                                    .filter(
                                        (
                                            part,
                                        ) =>
                                            part !==
                                            "body" &&
                                            part !==
                                            "query",
                                    )
                                    .join(".")
                                : "";

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

            if (
                messages.length > 0
            ) {
                return messages.join(
                    "; ",
                );
            }
        }

        if (
            typeof record.message ===
            "string"
        ) {
            return record.message;
        }

        if (
            typeof record.error ===
            "object" &&
            record.error !== null
        ) {
            const nested =
                record.error as Record<
                    string,
                    unknown
                >;

            if (
                typeof nested.message ===
                "string"
            ) {
                return nested.message;
            }
        }
    }

    return "Something went wrong while processing the import request.";
}

function asOptionalFilterValue<
    T extends string,
>(
    value: string,
): T | undefined {
    const normalised =
        value.trim();

    return normalised
        ? (normalised as T)
        : undefined;
}

function mapBatch(
    batch:
        | ImportBatchSummary
        | ImportBatchRead,
): ImportBatchTableItem {
    if (
        !Number.isInteger(batch.id) ||
        batch.id <= 0
    ) {
        throw new Error(
            "The import service returned a batch with an invalid ID.",
        );
    }

    const isFullBatch =
        "updated_at" in batch;

    const updatedAt =
        isFullBatch
            ? batch.updated_at
            : null;

    const archivedAt =
        isFullBatch
            ? batch.archived_at
            : batch.is_archived
                ? batch.completed_at ??
                batch.created_at
                : null;

    const validatedRows =
        batch.validated_rows ?? 0;

    const processedRows =
        batch.processed_rows ?? 0;

    return {
        id: batch.id,
        import_type:
            batch.import_type,
        filename:
            batch.original_filename,
        status: batch.status,

        total_rows:
            batch.total_rows,

        validated_rows:
            validatedRows,

        successful_rows:
            batch.successful_rows,

        warning_rows:
            batch.warning_rows,

        failed_rows:
            batch.failed_rows,

        skipped_rows:
            batch.skipped_rows,

        processed_rows:
            processedRows,

        // Compatibility fields for older table versions.
        valid_rows:
            validatedRows,

        invalid_rows:
            batch.failed_rows,

        imported_rows:
            batch.successful_rows,

        created_at:
            batch.created_at,

        updated_at:
            updatedAt,

        archived_at:
            archivedAt,
    };
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

function matchesArchiveFilter(
    batch: ImportBatchTableItem,
    archive:
        ImportFiltersValue["archive"],
): boolean {
    const archived =
        batch.archived_at !== null &&
        batch.archived_at !==
        undefined;

    if (archive === "archived") {
        return archived;
    }

    if (archive === "active") {
        return !archived;
    }

    return true;
}

async function fetchAllImportBatches(
    baseFilters:
        Omit<
            ImportBatchListParams,
            "skip" | "limit"
        >,
    totalItems: number,
): Promise<ImportBatchSummary[]> {
    if (totalItems <= 0) {
        return [];
    }

    const totalPages =
        Math.ceil(
            totalItems /
            BULK_FETCH_PAGE_SIZE,
        );

    const requests =
        Array.from(
            {
                length:
                    totalPages,
            },
            (_, index) =>
                listImportBatches({
                    ...baseFilters,
                    skip:
                        index *
                        BULK_FETCH_PAGE_SIZE,
                    limit:
                        BULK_FETCH_PAGE_SIZE,
                }),
        );

    const pages =
        await Promise.all(
            requests,
        );

    return pages.flat();
}

export default function SchoolAdminImportsPage() {
    const [
        batches,
        setBatches,
    ] = useState<
        ImportBatchTableItem[]
    >([]);

    const [
        totalItems,
        setTotalItems,
    ] = useState(0);

    const [
        page,
        setPage,
    ] = useState(1);

    const [
        filters,
        setFilters,
    ] =
        useState<ImportFiltersValue>(
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
    ] = useState<
        number | null
    >(null);

    const [
        errorMessage,
        setErrorMessage,
    ] = useState<
        string | null
    >(null);

    const [
        successMessage,
        setSuccessMessage,
    ] = useState<
        string | null
    >(null);

    const loadBatches =
        useCallback(
            async (): Promise<void> => {
                setIsLoading(true);
                setErrorMessage(null);

                try {
                    const importType =
                        asOptionalFilterValue<
                            string
                        >(
                            filters.importType,
                        );

                    const importStatus =
                        asOptionalFilterValue<
                            ImportStatus
                        >(
                            filters.status,
                        );

                    const includeArchived =
                        filters.archive !==
                        "active";

                    const baseFilters:
                        Omit<
                            ImportBatchListParams,
                            "skip" | "limit"
                        > = {
                        import_type:
                            importType,

                        status:
                            importStatus,

                        include_archived:
                            includeArchived,
                    };

                    const countFilters:
                        ImportBatchCountParams =
                    {
                        import_type:
                            importType,

                        status:
                            importStatus,

                        include_archived:
                            includeArchived,
                    };

                    const requiresClientFiltering =
                        filters.search
                            .trim()
                            .length >
                        0 ||
                        filters.archive ===
                        "archived";

                    if (
                        requiresClientFiltering
                    ) {
                        const serverCount =
                            await countImportBatches(
                                countFilters,
                            );

                        const allResponses =
                            await fetchAllImportBatches(
                                baseFilters,
                                serverCount,
                            );

                        const filtered =
                            allResponses
                                .map(
                                    mapBatch,
                                )
                                .filter(
                                    (
                                        batch,
                                    ) =>
                                        matchesArchiveFilter(
                                            batch,
                                            filters.archive,
                                        ),
                                )
                                .filter(
                                    (
                                        batch,
                                    ) =>
                                        matchesSearch(
                                            batch,
                                            filters.search,
                                        ),
                                );

                        const filteredTotal =
                            filtered.length;

                        const resolvedTotalPages =
                            Math.max(
                                1,
                                Math.ceil(
                                    filteredTotal /
                                    PAGE_SIZE,
                                ),
                            );

                        const resolvedPage =
                            Math.min(
                                page,
                                resolvedTotalPages,
                            );

                        if (
                            resolvedPage !==
                            page
                        ) {
                            setPage(
                                resolvedPage,
                            );
                        }

                        const start =
                            (
                                resolvedPage -
                                1
                            ) *
                            PAGE_SIZE;

                        setBatches(
                            filtered.slice(
                                start,
                                start +
                                PAGE_SIZE,
                            ),
                        );

                        setTotalItems(
                            filteredTotal,
                        );

                        return;
                    }

                    const listFilters:
                        ImportBatchListParams =
                    {
                        ...baseFilters,

                        skip:
                            (
                                page -
                                1
                            ) *
                            PAGE_SIZE,

                        limit:
                            PAGE_SIZE,
                    };

                    const [
                        batchResponse,
                        countResponse,
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

                    const resolvedTotalPages =
                        Math.max(
                            1,
                            Math.ceil(
                                countResponse /
                                PAGE_SIZE,
                            ),
                        );

                    if (
                        page >
                        resolvedTotalPages
                    ) {
                        setPage(
                            resolvedTotalPages,
                        );

                        return;
                    }

                    setBatches(
                        batchResponse.map(
                            mapBatch,
                        ),
                    );

                    setTotalItems(
                        countResponse,
                    );
                } catch (error) {
                    setBatches([]);
                    setTotalItems(0);

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
                filters.search,
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

    const summary =
        useMemo<SummaryCounts>(
            () =>
                batches.reduce<SummaryCounts>(
                    (
                        counts,
                        batch,
                    ) => {
                        const status =
                            normaliseStatus(
                                batch.status,
                            );

                        counts.visible +=
                            1;

                        if (
                            COMPLETED_STATUSES.has(
                                status,
                            )
                        ) {
                            counts.completed +=
                                1;
                        }

                        if (
                            PROCESSING_STATUSES.has(
                                status,
                            )
                        ) {
                            counts.processing +=
                                1;
                        }

                        if (
                            FAILED_STATUSES.has(
                                status,
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
            [batches],
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

            const filename =
                payload.file.name.trim();

            if (!filename) {
                throw new Error(
                    "The selected CSV file does not have a valid filename.",
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
                    filename,
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
                `${filename} was uploaded successfully as import batch #${createdBatch.id}.`,
            );

            setPage(1);

            await loadBatches();
        } catch (error) {
            const originalMessage =
                getErrorMessage(
                    error,
                );

            setErrorMessage(
                createdBatchId !==
                    null
                    ? (
                        `${originalMessage} ` +
                        `Import batch #${createdBatchId} was created, ` +
                        "but its CSV upload did not complete."
                    )
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
        setActionBatchId(
            batchId,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        try {
            await action(
                batchId,
            );

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
                `Cancel import batch #${batch.id}? Rows already processed may remain unchanged.`,
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
        const confirmed =
            window.confirm(
                `Archive import batch #${batch.id}? Its history will be retained.`,
            );

        if (!confirmed) {
            return;
        }

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
        const confirmed =
            window.confirm(
                `Restore import batch #${batch.id}?`,
            );

        if (!confirmed) {
            return;
        }

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
        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        setFilters(
            nextFilters,
        );
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
                                    Upload CSV files, validate records
                                    and monitor every import batch from
                                    one place.
                                </p>
                            </div>
                        </div>

                        <button
                            type="button"
                            disabled={
                                isLoading ||
                                isUploading ||
                                actionBatchId !==
                                null
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
                    <ImportSummaryCard
                        title="Visible batches"
                        value={
                            summary.visible
                        }
                        description="Batches shown on the current page"
                        icon={
                            <FileSpreadsheet
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        }
                        tone="blue"
                    />

                    <ImportSummaryCard
                        title="Completed"
                        value={
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

                    <ImportSummaryCard
                        title="In progress"
                        value={
                            summary.processing
                        }
                        description="Uploaded, validating, ready, queued or processing"
                        icon={
                            <Clock3
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        }
                        tone="amber"
                    />

                    <ImportSummaryCard
                        title="Failed or cancelled"
                        value={
                            summary.failed
                        }
                        description="Batches requiring administrator attention"
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
                            isLoading ||
                            actionBatchId !==
                            null
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
                        value={
                            filters
                        }
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
                        batches
                    }
                    isLoading={
                        isLoading
                    }
                    errorMessage={
                        null
                    }
                    page={
                        page
                    }
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
