"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
    useCallback,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import {
    AlertCircle,
    Archive,
    ArrowLeft,
    CheckCircle2,
    ChevronLeft,
    ChevronRight,
    CircleX,
    Clock3,
    FileSpreadsheet,
    LoaderCircle,
    PlayCircle,
    RefreshCcw,
    RotateCcw,
    Rows3,
    ShieldCheck,
    TriangleAlert,
    XCircle,
} from "lucide-react";

import ImportStatusBadge from "@/components/imports/ImportStatusBadge";
import {
    archiveImportBatch,
    cancelImportBatch,
    countImportRows,
    getImportBatch,
    getImportBatchProgress,
    listImportRows,
    processImportBatch,
    restoreImportBatch,
    retryImportBatch,
} from "@/lib/importApi";
import {
    IMPORT_ROW_STATUSES,
    type ImportBatchProgress,
    type ImportBatchRead,
    type ImportIssue,
    type ImportMetadata,
    type ImportRowListParams,
    type ImportRowRead,
    type ImportRowStatus,
    type ImportStatus,
} from "@/types/import";

type ActionName =
    | "process"
    | "retry"
    | "cancel"
    | "archive"
    | "restore";

const DEFAULT_PAGE_SIZE = 50;
const PROGRESS_POLL_INTERVAL_MS = 2500;

const PAGE_SIZE_OPTIONS = [
    25,
    50,
    100,
    250,
] as const;

const CANCELLABLE_STATUSES =
    new Set<ImportStatus>([
        "uploaded",
        "parsing",
        "validating",
        "ready",
        "queued",
        "processing",
    ]);

const ACTIVE_STATUSES =
    new Set<ImportStatus>([
        "uploaded",
        "parsing",
        "validating",
        "queued",
        "processing",
    ]);

const RETRYABLE_STATUSES =
    new Set<ImportStatus>([
        "completed_with_errors",
        "failed",
    ]);

const ISSUE_ROW_STATUSES =
    new Set<ImportRowStatus>([
        "invalid",
        "failed",
    ]);

type UnknownRecord =
    Record<string, unknown>;

function humaniseValue(
    value: string,
): string {
    const normalised =
        value.trim();

    if (!normalised) {
        return "Not specified";
    }

    return normalised
        .replace(/[_-]+/g, " ")
        .replace(
            /\b\w/g,
            (character) =>
                character.toUpperCase(),
        );
}

function formatDateTime(
    value: string | null,
): string {
    if (!value) {
        return "Not available";
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime(),
        )
    ) {
        return value;
    }

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            dateStyle: "medium",
            timeStyle: "short",
        },
    ).format(date);
}

function asRecord(
    value: unknown,
): UnknownRecord {
    if (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
    ) {
        return value as UnknownRecord;
    }

    return {};
}

function extractValidationMessage(
    details: unknown,
): string | null {
    if (!Array.isArray(details)) {
        return null;
    }

    const messages =
        details
            .map((detail) => {
                const record =
                    asRecord(detail);

                const location =
                    Array.isArray(
                        record.loc,
                    )
                        ? record.loc
                            .map(String)
                            .filter(
                                (part) =>
                                    part !==
                                    "body" &&
                                    part !==
                                    "query",
                            )
                            .join(".")
                        : "";

                const message =
                    typeof record.msg ===
                        "string"
                        ? record.msg.trim()
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

    return messages.length > 0
        ? messages.join("; ")
        : null;
}

function parseErrorPayload(
    value: unknown,
): string | null {
    if (
        typeof value ===
        "string"
    ) {
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
        record.error !==
        undefined
    ) {
        const nested =
            parseErrorPayload(
                record.error,
            );

        if (nested) {
            return nested;
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
    if (
        error instanceof Error
    ) {
        return (
            parseErrorPayload(
                error.message,
            ) ??
            error.message
        );
    }

    return (
        parseErrorPayload(error) ??
        "The import request could not be completed."
    );
}

function stringifyMetadata(
    value:
        | ImportMetadata
        | null,
): string {
    if (!value) {
        return "Not available";
    }

    try {
        return JSON.stringify(
            value,
            null,
            2,
        );
    } catch {
        return "The row data could not be displayed.";
    }
}

function describeIssue(
    issue: ImportIssue,
): string {
    const fieldCandidates = [
        issue.field,
        issue.column,
        issue.attribute,
        issue.key,
    ];

    const messageCandidates = [
        issue.message,
        issue.detail,
        issue.error,
        issue.reason,
    ];

    const field =
        fieldCandidates.find(
            (
                value,
            ): value is string =>
                typeof value ===
                "string" &&
                value.trim().length >
                0,
        );

    const message =
        messageCandidates.find(
            (
                value,
            ): value is string =>
                typeof value ===
                "string" &&
                value.trim().length >
                0,
        );

    if (
        field &&
        message
    ) {
        return `${field}: ${message}`;
    }

    if (message) {
        return message;
    }

    try {
        return JSON.stringify(
            issue,
        );
    } catch {
        return "Validation issue";
    }
}

function calculatePercentage(
    value: number,
    total: number,
): number {
    if (
        !Number.isFinite(value) ||
        !Number.isFinite(total) ||
        total <= 0
    ) {
        return 0;
    }

    return Math.min(
        100,
        Math.max(
            0,
            Math.round(
                (
                    value /
                    total
                ) *
                100,
            ),
        ),
    );
}

function ProgressBar({
    value,
    total,
}: {
    value: number;
    total: number;
}) {
    const percentage =
        calculatePercentage(
            value,
            total,
        );

    return (
        <div>
            <div className="mb-2 flex items-center justify-between gap-4 text-sm">
                <span className="font-semibold text-slate-700">
                    Processing progress
                </span>

                <span className="font-bold text-slate-950">
                    {percentage}%
                </span>
            </div>

            <div
                className="h-3 overflow-hidden rounded-full bg-slate-200"
                role="progressbar"
                aria-label="Import processing progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percentage}
            >
                <div
                    className="h-full rounded-full bg-blue-600 transition-[width] duration-300"
                    style={{
                        width: `${percentage}%`,
                    }}
                />
            </div>

            <p className="mt-2 text-xs font-medium text-slate-500">
                {Math.max(
                    value,
                    0,
                ).toLocaleString(
                    "en-GB",
                )}{" "}
                of{" "}
                {Math.max(
                    total,
                    0,
                ).toLocaleString(
                    "en-GB",
                )}{" "}
                rows processed
            </p>
        </div>
    );
}

function MetricCard({
    label,
    value,
    icon,
}: {
    label: string;
    value: number;
    icon: ReactNode;
}) {
    return (
        <article
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            aria-label={`${label}: ${Math.max(
                value,
                0,
            ).toLocaleString(
                "en-GB",
            )}`}
        >
            <div className="flex items-center justify-between gap-4">
                <div>
                    <p className="text-sm font-semibold text-slate-500">
                        {label}
                    </p>

                    <p className="mt-2 text-3xl font-bold text-slate-950">
                        {Math.max(
                            value,
                            0,
                        ).toLocaleString(
                            "en-GB",
                        )}
                    </p>
                </div>

                <span
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700"
                    aria-hidden="true"
                >
                    {icon}
                </span>
            </div>
        </article>
    );
}

function RowIssues({
    row,
}: {
    row: ImportRowRead;
}) {
    const validationErrors =
        row.validation_errors ??
        [];

    const validationWarnings =
        row.validation_warnings ??
        [];

    const hasErrors =
        validationErrors.length >
        0;

    const hasWarnings =
        validationWarnings.length >
        0;

    if (
        !row.error_message &&
        !hasErrors &&
        !hasWarnings
    ) {
        return (
            <span className="text-slate-500">
                No additional message
            </span>
        );
    }

    return (
        <div className="space-y-3">
            {row.error_message ? (
                <p className="font-semibold text-red-800">
                    {row.error_message}
                </p>
            ) : null}

            {hasErrors ? (
                <div>
                    <p className="mb-2 text-xs font-bold uppercase tracking-wide text-red-700">
                        Validation errors
                    </p>

                    <ul className="space-y-2">
                        {validationErrors.map(
                            (
                                issue,
                                index,
                            ) => (
                                <li
                                    key={`error-${row.id}-${index}`}
                                    className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-red-900"
                                >
                                    {describeIssue(
                                        issue,
                                    )}
                                </li>
                            ),
                        )}
                    </ul>
                </div>
            ) : null}

            {hasWarnings ? (
                <div>
                    <p className="mb-2 text-xs font-bold uppercase tracking-wide text-amber-700">
                        Validation warnings
                    </p>

                    <ul className="space-y-2">
                        {validationWarnings.map(
                            (
                                issue,
                                index,
                            ) => (
                                <li
                                    key={`warning-${row.id}-${index}`}
                                    className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-950"
                                >
                                    {describeIssue(
                                        issue,
                                    )}
                                </li>
                            ),
                        )}
                    </ul>
                </div>
            ) : null}
        </div>
    );
}

function mergeProgressIntoBatch(
    batch: ImportBatchRead,
    progress: ImportBatchProgress,
): ImportBatchRead {
    return {
        ...batch,
        status:
            progress.status,
        current_stage:
            progress.current_stage,
        total_rows:
            progress.total_rows,
        validated_rows:
            progress.validated_rows,
        processed_rows:
            progress.processed_rows,
        successful_rows:
            progress.successful_rows,
        warning_rows:
            progress.warning_rows,
        failed_rows:
            progress.failed_rows,
        skipped_rows:
            progress.skipped_rows,
        error_message:
            progress.error_message,
        queued_at:
            progress.queued_at,
        started_at:
            progress.started_at,
        completed_at:
            progress.completed_at,
        cancelled_at:
            progress.cancelled_at,
        updated_at:
            progress.updated_at,
        is_archived:
            progress.is_archived,
    };
}

export default function ImportBatchDetailsPage() {
    const params = useParams<{
        batchId:
        | string
        | string[];
    }>();

    const batchId = useMemo(
        () => {
            const rawValue =
                Array.isArray(
                    params.batchId,
                )
                    ? params.batchId[0]
                    : params.batchId;

            const parsed =
                Number(rawValue);

            return (
                Number.isInteger(
                    parsed,
                ) &&
                parsed > 0
            )
                ? parsed
                : null;
        },
        [params.batchId],
    );

    const [
        batch,
        setBatch,
    ] = useState<
        ImportBatchRead | null
    >(null);

    const [
        rows,
        setRows,
    ] = useState<
        ImportRowRead[]
    >([]);

    const [
        rowCount,
        setRowCount,
    ] = useState(0);

    const [
        page,
        setPage,
    ] = useState(1);

    const [
        pageSize,
        setPageSize,
    ] = useState(
        DEFAULT_PAGE_SIZE,
    );

    const [
        rowStatusFilter,
        setRowStatusFilter,
    ] = useState<
        ImportRowStatus | ""
    >("");

    const [
        isLoadingBatch,
        setIsLoadingBatch,
    ] = useState(true);

    const [
        isLoadingRows,
        setIsLoadingRows,
    ] = useState(false);

    const [
        activeAction,
        setActiveAction,
    ] = useState<
        ActionName | null
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

    const totalPages =
        Math.max(
            1,
            Math.ceil(
                rowCount /
                pageSize,
            ),
        );

    const firstVisibleRow =
        rowCount === 0
            ? 0
            : (
                page -
                1
            ) *
            pageSize +
            1;

    const lastVisibleRow =
        Math.min(
            page *
            pageSize,
            rowCount,
        );

    const loadBatch =
        useCallback(
            async (): Promise<void> => {
                if (!batchId) {
                    setBatch(
                        null,
                    );

                    setErrorMessage(
                        "The import batch identifier is invalid.",
                    );

                    setIsLoadingBatch(
                        false,
                    );

                    return;
                }

                setIsLoadingBatch(
                    true,
                );

                try {
                    const response =
                        await getImportBatch(
                            batchId,
                            {
                                includeArchived:
                                    true,
                            },
                        );

                    setBatch(
                        response,
                    );
                } catch (error) {
                    setBatch(
                        null,
                    );

                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                } finally {
                    setIsLoadingBatch(
                        false,
                    );
                }
            },
            [batchId],
        );

    const loadRows =
        useCallback(
            async (): Promise<void> => {
                if (!batchId) {
                    setRows([]);
                    setRowCount(0);
                    return;
                }

                setIsLoadingRows(
                    true,
                );

                try {
                    const filters:
                        ImportRowListParams =
                    {
                        status:
                            rowStatusFilter ||
                            undefined,

                        skip:
                            (
                                page -
                                1
                            ) *
                            pageSize,

                        limit:
                            pageSize,
                    };

                    const [
                        rowResponse,
                        countResponse,
                    ] =
                        await Promise.all(
                            [
                                listImportRows(
                                    batchId,
                                    filters,
                                ),

                                countImportRows(
                                    batchId,
                                    {
                                        status:
                                            rowStatusFilter ||
                                            undefined,
                                    },
                                ),
                            ],
                        );

                    const resolvedTotalPages =
                        Math.max(
                            1,
                            Math.ceil(
                                countResponse /
                                pageSize,
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

                    setRows(
                        rowResponse,
                    );

                    setRowCount(
                        countResponse,
                    );
                } catch (error) {
                    setRows([]);
                    setRowCount(0);

                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                } finally {
                    setIsLoadingRows(
                        false,
                    );
                }
            },
            [
                batchId,
                page,
                pageSize,
                rowStatusFilter,
            ],
        );
    const refreshPage =
        useCallback(
            async (): Promise<void> => {
                setErrorMessage(
                    null,
                );

                await Promise.all([
                    loadBatch(),
                    loadRows(),
                ]);
            },
            [
                loadBatch,
                loadRows,
            ],
        );

    useEffect(() => {
        void loadBatch();
    }, [loadBatch]);

    useEffect(() => {
        void loadRows();
    }, [loadRows]);

    useEffect(() => {
        setPage(1);
    }, [
        pageSize,
        rowStatusFilter,
    ]);

    const batchStatus =
        batch?.status ??
        null;

    const batchIsArchived =
        batch?.is_archived ??
        false;

    useEffect(() => {
        if (
            !batchId ||
            batchStatus ===
            null ||
            batchIsArchived ||
            !ACTIVE_STATUSES.has(
                batchStatus,
            )
        ) {
            return;
        }

        let isCancelled =
            false;

        let requestInFlight =
            false;

        const pollProgress =
            async (): Promise<void> => {
                if (
                    requestInFlight ||
                    isCancelled
                ) {
                    return;
                }

                requestInFlight =
                    true;

                try {
                    const progress =
                        await getImportBatchProgress(
                            batchId,
                        );

                    if (isCancelled) {
                        return;
                    }

                    setBatch(
                        (
                            currentBatch,
                        ) => {
                            if (
                                !currentBatch ||
                                currentBatch.id !==
                                progress.id
                            ) {
                                return currentBatch;
                            }

                            return mergeProgressIntoBatch(
                                currentBatch,
                                progress,
                            );
                        },
                    );

                    if (
                        progress.is_finished
                    ) {
                        await Promise.all([
                            loadBatch(),
                            loadRows(),
                        ]);
                    }
                } catch (error) {
                    if (!isCancelled) {
                        setErrorMessage(
                            getErrorMessage(
                                error,
                            ),
                        );
                    }
                } finally {
                    requestInFlight =
                        false;
                }
            };

        void pollProgress();

        const intervalId =
            window.setInterval(
                () => {
                    void pollProgress();
                },
                PROGRESS_POLL_INTERVAL_MS,
            );

        return () => {
            isCancelled =
                true;

            window.clearInterval(
                intervalId,
            );
        };
    }, [
        batchId,
        batchIsArchived,
        batchStatus,
        loadBatch,
        loadRows,
    ]);

    async function runAction(
        action: ActionName,
        request:
            () => Promise<ImportBatchRead>,
        successText: string,
    ): Promise<void> {
        if (activeAction !== null) {
            return;
        }

        setActiveAction(
            action,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        try {
            const updatedBatch =
                await request();

            setBatch(
                updatedBatch,
            );

            setSuccessMessage(
                successText,
            );

            await Promise.all([
                loadBatch(),
                loadRows(),
            ]);
        } catch (error) {
            setErrorMessage(
                getErrorMessage(
                    error,
                ),
            );
        } finally {
            setActiveAction(
                null,
            );
        }
    }

    async function handleProcess(): Promise<void> {
        if (
            !batch ||
            !canProcess
        ) {
            return;
        }

        const confirmed =
            window.confirm(
                `Process import batch #${batch.id}? Validated rows will be applied to school records.`,
            );

        if (!confirmed) {
            return;
        }

        await runAction(
            "process",
            () =>
                processImportBatch(
                    batch.id,
                ),
            `Import batch #${batch.id} was queued for processing.`,
        );
    }

    async function handleRetry(): Promise<void> {
        if (
            !batch ||
            !canRetry
        ) {
            return;
        }

        const confirmed =
            window.confirm(
                `Retry failed processing rows in import batch #${batch.id}? Successfully imported, updated and skipped rows will remain unchanged.`,
            );

        if (!confirmed) {
            return;
        }

        await runAction(
            "retry",
            () =>
                retryImportBatch(
                    batch.id,
                ),
            `Failed rows for import batch #${batch.id} were queued for retry.`,
        );
    }

    async function handleCancel(): Promise<void> {
        if (
            !batch ||
            !canCancel
        ) {
            return;
        }

        const confirmed =
            window.confirm(
                `Cancel import batch #${batch.id}? Rows already processed may remain unchanged.`,
            );

        if (!confirmed) {
            return;
        }

        await runAction(
            "cancel",
            () =>
                cancelImportBatch(
                    batch.id,
                ),
            `Import batch #${batch.id} was cancelled.`,
        );
    }

    async function handleArchive(): Promise<void> {
        if (
            !batch ||
            !canArchive
        ) {
            return;
        }

        const confirmed =
            window.confirm(
                `Archive import batch #${batch.id}? Its import history will be retained.`,
            );

        if (!confirmed) {
            return;
        }

        await runAction(
            "archive",
            () =>
                archiveImportBatch(
                    batch.id,
                ),
            `Import batch #${batch.id} was archived.`,
        );
    }

    async function handleRestore(): Promise<void> {
        if (
            !batch ||
            !batch.is_archived
        ) {
            return;
        }

        const confirmed =
            window.confirm(
                `Restore import batch #${batch.id}?`,
            );

        if (!confirmed) {
            return;
        }

        await runAction(
            "restore",
            () =>
                restoreImportBatch(
                    batch.id,
                ),
            `Import batch #${batch.id} was restored.`,
        );
    }

    const canProcess =
        batch !== null &&
        batch.status ===
        "ready" &&
        batch.total_rows >
        0 &&
        !batch.is_archived;

    const canRetry =
        batch !== null &&
        batch.failed_rows >
        0 &&
        RETRYABLE_STATUSES.has(
            batch.status,
        ) &&
        !batch.is_archived;

    const canCancel =
        batch !== null &&
        CANCELLABLE_STATUSES.has(
            batch.status,
        ) &&
        !batch.is_archived;

    const canArchive =
        batch !== null &&
        !batch.is_archived &&
        !ACTIVE_STATUSES.has(
            batch.status,
        );

    const showInitialLoading =
        isLoadingBatch &&
        batch === null;

    const showUnavailableState =
        !isLoadingBatch &&
        batch === null &&
        errorMessage !== null;

    const isBusy =
        isLoadingBatch ||
        isLoadingRows ||
        activeAction !==
        null;

    return (
        <main className="min-h-screen bg-slate-50">
            <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
                <div className="mb-5">
                    <Link
                        href="/school-admin/imports"
                        className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                    >
                        <ArrowLeft
                            className="h-4 w-4"
                            aria-hidden="true"
                        />

                        Back to imports
                    </Link>
                </div>

                <header className="mb-6 overflow-hidden rounded-3xl bg-slate-950 px-6 py-7 text-white shadow-xl sm:px-8">
                    <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                        <div className="flex min-w-0 items-start gap-4">
                            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600">
                                <FileSpreadsheet
                                    className="h-7 w-7"
                                    aria-hidden="true"
                                />
                            </span>

                            <div className="min-w-0">
                                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-300">
                                    Import batch
                                </p>

                                <h1 className="mt-1 break-words text-2xl font-bold sm:text-3xl">
                                    {batch
                                        ? batch.original_filename ||
                                        `Batch #${batch.id}`
                                        : batchId
                                            ? `Batch #${batchId}`
                                            : "Import details"}
                                </h1>

                                {batch ? (
                                    <div className="mt-3 flex flex-wrap items-center gap-3">
                                        <ImportStatusBadge
                                            status={
                                                batch.status
                                            }
                                        />

                                        <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-sm font-semibold text-slate-100">
                                            {humaniseValue(
                                                batch.import_type,
                                            )}
                                        </span>

                                        <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-sm font-semibold text-slate-100">
                                            {humaniseValue(
                                                batch.operation,
                                            )}
                                        </span>

                                        {batch.is_archived ? (
                                            <span className="rounded-full border border-amber-300/30 bg-amber-400/15 px-3 py-1 text-sm font-semibold text-amber-100">
                                                Archived
                                            </span>
                                        ) : null}

                                        <span className="text-sm text-slate-300">
                                            Created{" "}
                                            {formatDateTime(
                                                batch.created_at,
                                            )}
                                        </span>
                                    </div>
                                ) : null}
                            </div>
                        </div>

                        <div className="flex flex-wrap gap-3">
                            <button
                                type="button"
                                disabled={
                                    isBusy
                                }
                                onClick={() => {
                                    void refreshPage();
                                }}
                                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 text-sm font-semibold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <RefreshCcw
                                    className={[
                                        "h-4 w-4",
                                        isLoadingBatch ||
                                            isLoadingRows
                                            ? "animate-spin"
                                            : "",
                                    ]
                                        .filter(
                                            Boolean,
                                        )
                                        .join(" ")}
                                    aria-hidden="true"
                                />

                                Refresh
                            </button>

                            {canProcess ? (
                                <button
                                    type="button"
                                    disabled={
                                        activeAction !==
                                        null
                                    }
                                    onClick={() => {
                                        void handleProcess();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-emerald-300/40 bg-emerald-500/20 px-4 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction ===
                                        "process" ? (
                                        <LoaderCircle
                                            className="h-4 w-4 animate-spin"
                                            aria-hidden="true"
                                        />
                                    ) : (
                                        <PlayCircle
                                            className="h-4 w-4"
                                            aria-hidden="true"
                                        />
                                    )}

                                    Process
                                </button>
                            ) : null}

                            {canRetry ? (
                                <button
                                    type="button"
                                    disabled={
                                        activeAction !==
                                        null
                                    }
                                    onClick={() => {
                                        void handleRetry();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-amber-300/40 bg-amber-500/20 px-4 text-sm font-semibold text-amber-100 transition hover:bg-amber-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction ===
                                        "retry" ? (
                                        <LoaderCircle
                                            className="h-4 w-4 animate-spin"
                                            aria-hidden="true"
                                        />
                                    ) : (
                                        <RotateCcw
                                            className="h-4 w-4"
                                            aria-hidden="true"
                                        />
                                    )}

                                    Retry Failed Rows
                                </button>
                            ) : null}

                            {canCancel ? (
                                <button
                                    type="button"
                                    disabled={
                                        activeAction !==
                                        null
                                    }
                                    onClick={() => {
                                        void handleCancel();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-red-300/40 bg-red-500/20 px-4 text-sm font-semibold text-red-100 transition hover:bg-red-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction ===
                                        "cancel" ? (
                                        <LoaderCircle
                                            className="h-4 w-4 animate-spin"
                                            aria-hidden="true"
                                        />
                                    ) : (
                                        <XCircle
                                            className="h-4 w-4"
                                            aria-hidden="true"
                                        />
                                    )}

                                    Cancel
                                </button>
                            ) : null}

                            {batch?.is_archived ? (
                                <button
                                    type="button"
                                    disabled={
                                        activeAction !==
                                        null
                                    }
                                    onClick={() => {
                                        void handleRestore();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 text-sm font-semibold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction ===
                                        "restore" ? (
                                        <LoaderCircle
                                            className="h-4 w-4 animate-spin"
                                            aria-hidden="true"
                                        />
                                    ) : (
                                        <RotateCcw
                                            className="h-4 w-4"
                                            aria-hidden="true"
                                        />
                                    )}

                                    Restore
                                </button>
                            ) : canArchive ? (
                                <button
                                    type="button"
                                    disabled={
                                        activeAction !==
                                        null
                                    }
                                    onClick={() => {
                                        void handleArchive();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 text-sm font-semibold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction ===
                                        "archive" ? (
                                        <LoaderCircle
                                            className="h-4 w-4 animate-spin"
                                            aria-hidden="true"
                                        />
                                    ) : (
                                        <Archive
                                            className="h-4 w-4"
                                            aria-hidden="true"
                                        />
                                    )}

                                    Archive
                                </button>
                            ) : null}
                        </div>
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

                {showInitialLoading ? (
                    <section className="rounded-3xl border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">
                        <LoaderCircle
                            className="mx-auto h-10 w-10 animate-spin text-blue-600"
                            aria-hidden="true"
                        />

                        <h2 className="mt-4 text-lg font-bold text-slate-950">
                            Loading import batch
                        </h2>

                        <p className="mt-2 text-sm text-slate-600">
                            Please wait while the latest import
                            information is retrieved.
                        </p>
                    </section>
                ) : null}

                {showUnavailableState ? (
                    <section className="rounded-3xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
                        <CircleX
                            className="mx-auto h-12 w-12 text-red-500"
                            aria-hidden="true"
                        />

                        <h2 className="mt-4 text-xl font-bold text-slate-950">
                            Import batch unavailable
                        </h2>

                        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">
                            The batch may not exist, may have been removed,
                            or you may not have permission to view it.
                        </p>
                    </section>
                ) : null}

                {batch ? (
                    <>
                        <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
                            <MetricCard
                                label="Total rows"
                                value={
                                    batch.total_rows
                                }
                                icon={
                                    <Rows3
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Validated rows"
                                value={
                                    batch.validated_rows
                                }
                                icon={
                                    <ShieldCheck
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Warnings"
                                value={
                                    batch.warning_rows
                                }
                                icon={
                                    <TriangleAlert
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Processed"
                                value={
                                    batch.processed_rows
                                }
                                icon={
                                    <Clock3
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Successful"
                                value={
                                    batch.successful_rows
                                }
                                icon={
                                    <CheckCircle2
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Failed"
                                value={
                                    batch.failed_rows
                                }
                                icon={
                                    <XCircle
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Skipped"
                                value={
                                    batch.skipped_rows
                                }
                                icon={
                                    <CircleX
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />
                        </section>

                        <section className="mb-6 grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                            <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                                <h2 className="text-lg font-bold text-slate-950">
                                    Batch progress
                                </h2>

                                <p className="mt-1 text-sm text-slate-600">
                                    Progress includes successful, failed
                                    and skipped processing outcomes.
                                </p>

                                <div className="mt-6">
                                    <ProgressBar
                                        value={
                                            batch.processed_rows
                                        }
                                        total={
                                            batch.total_rows
                                        }
                                    />
                                </div>

                                {ACTIVE_STATUSES.has(
                                    batch.status,
                                ) ? (
                                    <div className="mt-6 flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-blue-900">
                                        <LoaderCircle
                                            className="mt-0.5 h-5 w-5 shrink-0 animate-spin"
                                            aria-hidden="true"
                                        />

                                        <div>
                                            <p className="font-bold">
                                                Live progress enabled
                                            </p>

                                            <p className="mt-1 text-sm leading-6">
                                                This page refreshes automatically
                                                while validation or processing is
                                                active.
                                            </p>
                                        </div>
                                    </div>
                                ) : null}

                                {batch.error_message ? (
                                    <div className="mt-6 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-900">
                                        <AlertCircle
                                            className="mt-0.5 h-5 w-5 shrink-0"
                                            aria-hidden="true"
                                        />

                                        <div>
                                            <p className="font-bold">
                                                Batch message
                                            </p>

                                            <p className="mt-1 text-sm leading-6">
                                                {
                                                    batch.error_message
                                                }
                                            </p>
                                        </div>
                                    </div>
                                ) : null}
                            </article>

                            <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                                <h2 className="text-lg font-bold text-slate-950">
                                    Batch information
                                </h2>

                                <dl className="mt-5 space-y-4 text-sm">
                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Batch ID
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            #{batch.id}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Import type
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {humaniseValue(
                                                batch.import_type,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Operation
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {humaniseValue(
                                                batch.operation,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Current stage
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {batch.current_stage
                                                ? humaniseValue(
                                                    batch.current_stage,
                                                )
                                                : "Not specified"}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Created
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {formatDateTime(
                                                batch.created_at,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Queued
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {formatDateTime(
                                                batch.queued_at,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Started
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {formatDateTime(
                                                batch.started_at,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Updated
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {formatDateTime(
                                                batch.updated_at,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Completed
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {formatDateTime(
                                                batch.completed_at,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Cancelled
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {formatDateTime(
                                                batch.cancelled_at,
                                            )}
                                        </dd>
                                    </div>

                                    <div className="flex items-start justify-between gap-4">
                                        <dt className="font-semibold text-slate-500">
                                            Archived
                                        </dt>

                                        <dd className="text-right font-bold text-slate-950">
                                            {formatDateTime(
                                                batch.archived_at,
                                            )}
                                        </dd>
                                    </div>
                                </dl>
                            </article>
                        </section>

                        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
                            <div className="border-b border-slate-200 px-6 py-5">
                                <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
                                    <div>
                                        <h2 className="text-lg font-bold text-slate-950">
                                            Row results
                                        </h2>

                                        <p className="mt-1 text-sm text-slate-600">
                                            Validation and processing results
                                            for individual CSV rows.
                                        </p>
                                    </div>

                                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                                        <label className="block">
                                            <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-600">
                                                Row status
                                            </span>

                                            <select
                                                value={
                                                    rowStatusFilter
                                                }
                                                disabled={
                                                    isLoadingRows
                                                }
                                                aria-label="Filter rows by status"
                                                onChange={(
                                                    event,
                                                ) => {
                                                    setRowStatusFilter(
                                                        event.target
                                                            .value as
                                                        | ImportRowStatus
                                                        | "",
                                                    );
                                                }}
                                                className={[
                                                    "min-h-11 min-w-44 rounded-xl border border-slate-300",
                                                    "bg-white px-3 text-sm font-semibold text-slate-800",
                                                    "outline-none transition focus:border-blue-600",
                                                    "focus:ring-2 focus:ring-blue-600/20",
                                                    "disabled:cursor-not-allowed disabled:bg-slate-100",
                                                    "disabled:text-slate-500",
                                                ].join(" ")}
                                            >
                                                <option value="">
                                                    All statuses
                                                </option>

                                                {IMPORT_ROW_STATUSES.map(
                                                    (
                                                        statusOption,
                                                    ) => (
                                                        <option
                                                            key={
                                                                statusOption
                                                            }
                                                            value={
                                                                statusOption
                                                            }
                                                        >
                                                            {humaniseValue(
                                                                statusOption,
                                                            )}
                                                        </option>
                                                    ),
                                                )}
                                            </select>
                                        </label>

                                        <label className="block">
                                            <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-600">
                                                Rows per page
                                            </span>

                                            <select
                                                value={
                                                    pageSize
                                                }
                                                disabled={
                                                    isLoadingRows
                                                }
                                                aria-label="Rows per page"
                                                onChange={(
                                                    event,
                                                ) => {
                                                    const nextPageSize =
                                                        Number(
                                                            event.target
                                                                .value,
                                                        );

                                                    if (
                                                        PAGE_SIZE_OPTIONS.includes(
                                                            nextPageSize as
                                                            (typeof PAGE_SIZE_OPTIONS)[number],
                                                        )
                                                    ) {
                                                        setPageSize(
                                                            nextPageSize,
                                                        );
                                                    }
                                                }}
                                                className={[
                                                    "min-h-11 rounded-xl border border-slate-300",
                                                    "bg-white px-3 text-sm font-semibold text-slate-800",
                                                    "outline-none transition focus:border-blue-600",
                                                    "focus:ring-2 focus:ring-blue-600/20",
                                                    "disabled:cursor-not-allowed disabled:bg-slate-100",
                                                    "disabled:text-slate-500",
                                                ].join(" ")}
                                            >
                                                {PAGE_SIZE_OPTIONS.map(
                                                    (
                                                        option,
                                                    ) => (
                                                        <option
                                                            key={
                                                                option
                                                            }
                                                            value={
                                                                option
                                                            }
                                                        >
                                                            {
                                                                option
                                                            }
                                                        </option>
                                                    ),
                                                )}
                                            </select>
                                        </label>
                                    </div>
                                </div>
                            </div>

                            {isLoadingRows ? (
                                <div className="px-6 py-14 text-center">
                                    <LoaderCircle
                                        className="mx-auto h-10 w-10 animate-spin text-blue-600"
                                        aria-hidden="true"
                                    />

                                    <h3 className="mt-4 text-lg font-bold text-slate-950">
                                        Loading row results
                                    </h3>
                                </div>
                            ) : rows.length === 0 ? (
                                <div className="px-6 py-14 text-center">
                                    <Clock3
                                        className="mx-auto h-11 w-11 text-slate-400"
                                        aria-hidden="true"
                                    />

                                    <h3 className="mt-4 text-lg font-bold text-slate-950">
                                        No row results available
                                    </h3>

                                    <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">
                                        {rowStatusFilter
                                            ? `No rows currently have the ${humaniseValue(
                                                rowStatusFilter,
                                            ).toLowerCase()} status.`
                                            : "Row-level results will appear after the CSV has been uploaded and validated."}
                                    </p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-slate-200">
                                        <caption className="sr-only">
                                            Import row validation and processing
                                            results
                                        </caption>

                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th
                                                    scope="col"
                                                    className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                                >
                                                    Row
                                                </th>

                                                <th
                                                    scope="col"
                                                    className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                                >
                                                    Status
                                                </th>

                                                <th
                                                    scope="col"
                                                    className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                                >
                                                    Result
                                                </th>

                                                <th
                                                    scope="col"
                                                    className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                                >
                                                    Imported record
                                                </th>

                                                <th
                                                    scope="col"
                                                    className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                                >
                                                    Source data
                                                </th>
                                            </tr>
                                        </thead>

                                        <tbody className="divide-y divide-slate-200 bg-white">
                                            {rows.map(
                                                (row) => (
                                                    <tr
                                                        key={
                                                            row.id
                                                        }
                                                        className={[
                                                            "align-top transition hover:bg-slate-50",
                                                            ISSUE_ROW_STATUSES.has(
                                                                row.status,
                                                            )
                                                                ? "bg-red-50/20"
                                                                : "",
                                                        ]
                                                            .filter(
                                                                Boolean,
                                                            )
                                                            .join(
                                                                " ",
                                                            )}
                                                    >
                                                        <td className="whitespace-nowrap px-6 py-4 text-sm font-bold text-slate-950">
                                                            {
                                                                row.row_number
                                                            }
                                                        </td>

                                                        <td className="whitespace-nowrap px-6 py-4">
                                                            <ImportStatusBadge
                                                                status={
                                                                    row.status
                                                                }
                                                            />
                                                        </td>

                                                        <td className="min-w-[320px] px-6 py-4 text-sm text-slate-700">
                                                            <RowIssues
                                                                row={
                                                                    row
                                                                }
                                                            />
                                                        </td>

                                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-700">
                                                            {row.created_entity_id !==
                                                                null ? (
                                                                <span className="font-bold text-slate-950">
                                                                    #
                                                                    {
                                                                        row.created_entity_id
                                                                    }
                                                                </span>
                                                            ) : (
                                                                <span className="text-slate-500">
                                                                    Not
                                                                    created
                                                                </span>
                                                            )}

                                                            {row.entity_type ? (
                                                                <p className="mt-1 text-xs font-medium text-slate-500">
                                                                    {humaniseValue(
                                                                        row.entity_type,
                                                                    )}
                                                                </p>
                                                            ) : null}

                                                            {row.processed_at ? (
                                                                <p className="mt-1 text-xs text-slate-500">
                                                                    {formatDateTime(
                                                                        row.processed_at,
                                                                    )}
                                                                </p>
                                                            ) : null}

                                                            <p className="mt-1 text-xs text-slate-500">
                                                                Attempts:{" "}
                                                                {
                                                                    row.attempt_count
                                                                }
                                                            </p>
                                                        </td>

                                                        <td className="min-w-[360px] px-6 py-4">
                                                            <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                                                                {stringifyMetadata(
                                                                    row.original_data,
                                                                )}
                                                            </pre>

                                                            {row.normalised_data ? (
                                                                <details className="mt-3">
                                                                    <summary className="cursor-pointer text-sm font-semibold text-blue-700 hover:text-blue-900">
                                                                        View
                                                                        normalised
                                                                        data
                                                                    </summary>

                                                                    <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-100 p-3 text-xs leading-5 text-slate-800">
                                                                        {stringifyMetadata(
                                                                            row.normalised_data,
                                                                        )}
                                                                    </pre>
                                                                </details>
                                                            ) : null}
                                                        </td>
                                                    </tr>
                                                ),
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            <div className="flex flex-col gap-4 border-t border-slate-200 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                                <p className="text-sm font-medium text-slate-600">
                                    {rowCount === 0
                                        ? "No rows"
                                        : `Showing ${firstVisibleRow.toLocaleString(
                                            "en-GB",
                                        )}–${lastVisibleRow.toLocaleString(
                                            "en-GB",
                                        )} of ${rowCount.toLocaleString(
                                            "en-GB",
                                        )}`}
                                </p>

                                <div className="flex items-center gap-3">
                                    <button
                                        type="button"
                                        disabled={
                                            page <= 1 ||
                                            isLoadingRows
                                        }
                                        onClick={() => {
                                            setPage(
                                                (
                                                    current,
                                                ) =>
                                                    Math.max(
                                                        current -
                                                        1,
                                                        1,
                                                    ),
                                            );
                                        }}
                                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        <ChevronLeft
                                            className="h-4 w-4"
                                            aria-hidden="true"
                                        />

                                        Previous
                                    </button>

                                    <span
                                        className="text-sm font-bold text-slate-700"
                                        aria-live="polite"
                                    >
                                        Page {page} of{" "}
                                        {totalPages}
                                    </span>

                                    <button
                                        type="button"
                                        disabled={
                                            page >=
                                            totalPages ||
                                            isLoadingRows
                                        }
                                        onClick={() => {
                                            setPage(
                                                (
                                                    current,
                                                ) =>
                                                    Math.min(
                                                        current +
                                                        1,
                                                        totalPages,
                                                    ),
                                            );
                                        }}
                                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        Next

                                        <ChevronRight
                                            className="h-4 w-4"
                                            aria-hidden="true"
                                        />
                                    </button>
                                </div>
                            </div>
                        </section>
                    </>
                ) : null}
            </div>
        </main>
    );
}
