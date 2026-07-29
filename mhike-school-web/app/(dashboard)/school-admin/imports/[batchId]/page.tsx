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
    listImportRows,
    restoreImportBatch,
} from "@/lib/importApi";
import {
    IMPORT_ROW_STATUSES,
    type ImportBatchRead,
    type ImportMetadata,
    type ImportRowRead,
    type ImportRowStatus,
} from "@/types/import";

type ActionName =
    | "cancel"
    | "archive"
    | "restore";

const DEFAULT_PAGE_SIZE = 50;

const PAGE_SIZE_OPTIONS = [
    25,
    50,
    100,
    250,
] as const;

const CANCELLABLE_STATUSES = new Set([
    "pending",
    "uploading",
    "staged",
    "validating",
    "validated",
    "processing",
]);

const ACTIVE_STATUSES = new Set([
    "pending",
    "uploading",
    "staged",
    "validating",
    "processing",
]);

const ISSUE_ROW_STATUSES = new Set<ImportRowStatus>([
    "invalid",
    "failed",
]);

function humaniseValue(value: string): string {
    const normalised = value.trim();

    if (!normalised) {
        return "Not specified";
    }

    return normalised
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (character) =>
            character.toUpperCase(),
        );
}

function formatDateTime(value: string | null): string {
    if (!value) {
        return "Not available";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

function getErrorMessage(error: unknown): string {
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
        const record = error as Record<string, unknown>;

        if (typeof record.detail === "string") {
            return record.detail;
        }

        if (typeof record.message === "string") {
            return record.message;
        }

        if (
            typeof record.error === "object" &&
            record.error !== null
        ) {
            const nestedError =
                record.error as Record<string, unknown>;

            if (typeof nestedError.message === "string") {
                return nestedError.message;
            }
        }
    }

    return "The import request could not be completed.";
}

function stringifyMetadata(
    value: ImportMetadata | null,
): string {
    if (!value) {
        return "Not available";
    }

    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return "The row data could not be displayed.";
    }
}

function describeIssue(
    issue: ImportMetadata,
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

    const field = fieldCandidates.find(
        (value): value is string =>
            typeof value === "string" &&
            value.trim().length > 0,
    );

    const message = messageCandidates.find(
        (value): value is string =>
            typeof value === "string" &&
            value.trim().length > 0,
    );

    if (field && message) {
        return `${field}: ${message}`;
    }

    if (message) {
        return message;
    }

    try {
        return JSON.stringify(issue);
    } catch {
        return "Validation issue";
    }
}

function ProgressBar({
    value,
    total,
}: {
    value: number;
    total: number;
}) {
    const percentage =
        total > 0
            ? Math.min(
                Math.max((value / total) * 100, 0),
                100,
            )
            : 0;

    return (
        <div>
            <div className="mb-2 flex items-center justify-between gap-4 text-sm">
                <span className="font-semibold text-slate-700">
                    Processing progress
                </span>

                <span className="font-bold text-slate-950">
                    {Math.round(percentage)}%
                </span>
            </div>

            <div
                className="h-3 overflow-hidden rounded-full bg-slate-200"
                role="progressbar"
                aria-label="Import processing progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(percentage)}
            >
                <div
                    className="h-full rounded-full bg-blue-600 transition-[width] duration-300"
                    style={{
                        width: `${percentage}%`,
                    }}
                />
            </div>

            <p className="mt-2 text-xs font-medium text-slate-500">
                {value.toLocaleString("en-GB")} of{" "}
                {total.toLocaleString("en-GB")} rows processed
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
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-4">
                <div>
                    <p className="text-sm font-semibold text-slate-500">
                        {label}
                    </p>

                    <p className="mt-2 text-3xl font-bold text-slate-950">
                        {value.toLocaleString("en-GB")}
                    </p>
                </div>

                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
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
        row.validation_errors ?? [];

    const validationWarnings =
        row.validation_warnings ?? [];

    const hasErrors =
        validationErrors.length > 0;

    const hasWarnings =
        validationWarnings.length > 0;

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
                            (issue, index) => (
                                <li
                                    key={`error-${row.id}-${index}`}
                                    className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-red-900"
                                >
                                    {describeIssue(issue)}
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
                            (issue, index) => (
                                <li
                                    key={`warning-${row.id}-${index}`}
                                    className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-950"
                                >
                                    {describeIssue(issue)}
                                </li>
                            ),
                        )}
                    </ul>
                </div>
            ) : null}
        </div>
    );
}

export default function ImportBatchDetailsPage() {
    const params = useParams<{
        batchId: string | string[];
    }>();

    const batchId = useMemo(() => {
        const rawValue = Array.isArray(params.batchId)
            ? params.batchId[0]
            : params.batchId;

        const parsed = Number(rawValue);

        return Number.isInteger(parsed) && parsed > 0
            ? parsed
            : null;
    }, [params.batchId]);

    const [batch, setBatch] =
        useState<ImportBatchRead | null>(null);

    const [rows, setRows] =
        useState<ImportRowRead[]>([]);

    const [rowCount, setRowCount] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] =
        useState(DEFAULT_PAGE_SIZE);

    const [rowStatusFilter, setRowStatusFilter] =
        useState<ImportRowStatus | "">("");

    const [isLoadingBatch, setIsLoadingBatch] =
        useState(true);

    const [isLoadingRows, setIsLoadingRows] =
        useState(false);

    const [activeAction, setActiveAction] =
        useState<ActionName | null>(null);

    const [errorMessage, setErrorMessage] =
        useState<string | null>(null);

    const [successMessage, setSuccessMessage] =
        useState<string | null>(null);

    const totalPages = Math.max(
        1,
        Math.ceil(rowCount / pageSize),
    );

    const firstVisibleRow =
        rowCount === 0
            ? 0
            : (page - 1) * pageSize + 1;

    const lastVisibleRow = Math.min(
        page * pageSize,
        rowCount,
    );

    const loadBatch = useCallback(async () => {
        if (!batchId) {
            setBatch(null);
            setErrorMessage(
                "The import batch identifier is invalid.",
            );
            setIsLoadingBatch(false);
            return;
        }

        setIsLoadingBatch(true);
        setErrorMessage(null);

        try {
            const response =
                await getImportBatch(batchId);

            setBatch(response);
        } catch (error) {
            setBatch(null);
            setErrorMessage(getErrorMessage(error));
        } finally {
            setIsLoadingBatch(false);
        }
    }, [batchId]);

    const loadRows = useCallback(async () => {
        if (!batchId) {
            setRows([]);
            setRowCount(0);
            return;
        }

        setIsLoadingRows(true);

        try {
            const filters = {
                status:
                    rowStatusFilter || undefined,
                skip: (page - 1) * pageSize,
                limit: pageSize,
            };

            const countFilters = {
                status:
                    rowStatusFilter || undefined,
            };

            const [rowResponse, countResponse] =
                await Promise.all([
                    listImportRows(
                        batchId,
                        filters,
                    ),
                    countImportRows(
                        batchId,
                        countFilters,
                    ),
                ]);

            setRows(rowResponse);
            setRowCount(countResponse);

            const resolvedTotalPages = Math.max(
                1,
                Math.ceil(
                    countResponse / pageSize,
                ),
            );

            if (page > resolvedTotalPages) {
                setPage(resolvedTotalPages);
            }
        } catch (error) {
            setRows([]);
            setRowCount(0);
            setErrorMessage(getErrorMessage(error));
        } finally {
            setIsLoadingRows(false);
        }
    }, [
        batchId,
        page,
        pageSize,
        rowStatusFilter,
    ]);

    const refreshPage = useCallback(async () => {
        setSuccessMessage(null);

        await Promise.all([
            loadBatch(),
            loadRows(),
        ]);
    }, [loadBatch, loadRows]);

    useEffect(() => {
        void loadBatch();
    }, [loadBatch]);

    useEffect(() => {
        void loadRows();
    }, [loadRows]);

    useEffect(() => {
        setPage(1);
    }, [pageSize, rowStatusFilter]);

    async function runAction(
        action: ActionName,
        request: () => Promise<ImportBatchRead>,
        successText: string,
    ): Promise<void> {
        setActiveAction(action);
        setErrorMessage(null);
        setSuccessMessage(null);

        try {
            const updatedBatch = await request();

            setBatch(updatedBatch);
            setSuccessMessage(successText);

            await loadRows();
        } catch (error) {
            setErrorMessage(getErrorMessage(error));
        } finally {
            setActiveAction(null);
        }
    }

    async function handleCancel(): Promise<void> {
        if (!batch) {
            return;
        }

        const confirmed = window.confirm(
            `Cancel import batch #${batch.id}? Rows already processed may remain unchanged.`,
        );

        if (!confirmed) {
            return;
        }

        await runAction(
            "cancel",
            () => cancelImportBatch(batch.id),
            `Import batch #${batch.id} was cancelled.`,
        );
    }

    async function handleArchive(): Promise<void> {
        if (!batch) {
            return;
        }

        const confirmed = window.confirm(
            `Archive import batch #${batch.id}?`,
        );

        if (!confirmed) {
            return;
        }

        await runAction(
            "archive",
            () => archiveImportBatch(batch.id),
            `Import batch #${batch.id} was archived.`,
        );
    }

    async function handleRestore(): Promise<void> {
        if (!batch) {
            return;
        }

        await runAction(
            "restore",
            () => restoreImportBatch(batch.id),
            `Import batch #${batch.id} was restored.`,
        );
    }

    const canCancel =
        batch !== null &&
        CANCELLABLE_STATUSES.has(batch.status) &&
        !batch.is_archived;

    const canArchive =
        batch !== null &&
        !batch.is_archived &&
        !ACTIVE_STATUSES.has(batch.status);

    const showInitialLoading =
        isLoadingBatch && !batch;

    const showUnavailableState =
        !isLoadingBatch &&
        !batch &&
        errorMessage !== null;

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
                                        ? batch.original_filename ??
                                        `Batch #${batch.id}`
                                        : batchId
                                            ? `Batch #${batchId}`
                                            : "Import details"}
                                </h1>

                                {batch ? (
                                    <div className="mt-3 flex flex-wrap items-center gap-3">
                                        <ImportStatusBadge
                                            status={batch.status}
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
                                    isLoadingBatch ||
                                    isLoadingRows ||
                                    activeAction !== null
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
                                    ].join(" ")}
                                    aria-hidden="true"
                                />
                                Refresh
                            </button>

                            {canCancel ? (
                                <button
                                    type="button"
                                    disabled={
                                        activeAction !== null
                                    }
                                    onClick={() => {
                                        void handleCancel();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-red-300/40 bg-red-500/20 px-4 text-sm font-semibold text-red-100 transition hover:bg-red-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction === "cancel" ? (
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
                                        activeAction !== null
                                    }
                                    onClick={() => {
                                        void handleRestore();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 text-sm font-semibold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction === "restore" ? (
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
                                        activeAction !== null
                                    }
                                    onClick={() => {
                                        void handleArchive();
                                    }}
                                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 text-sm font-semibold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {activeAction === "archive" ? (
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
                            The batch may not exist, or you may not
                            have permission to view it.
                        </p>
                    </section>
                ) : null}

                {batch ? (
                    <>
                        <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
                            <MetricCard
                                label="Total rows"
                                value={batch.total_rows}
                                icon={
                                    <Rows3
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Valid rows"
                                value={batch.valid_rows}
                                icon={
                                    <ShieldCheck
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Invalid rows"
                                value={batch.invalid_rows}
                                icon={
                                    <TriangleAlert
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Processed"
                                value={batch.processed_rows}
                                icon={
                                    <Clock3
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Successful"
                                value={batch.successful_rows}
                                icon={
                                    <CheckCircle2
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Failed"
                                value={batch.failed_rows}
                                icon={
                                    <XCircle
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                }
                            />

                            <MetricCard
                                label="Skipped"
                                value={batch.skipped_rows}
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
                                    Progress includes all successfully
                                    processed, failed and skipped rows.
                                </p>

                                <div className="mt-6">
                                    <ProgressBar
                                        value={
                                            batch.processed_rows
                                        }
                                        total={batch.total_rows}
                                    />
                                </div>

                                {batch.error_message ? (
                                    <div className="mt-6 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-900">
                                        <AlertCircle
                                            className="mt-0.5 h-5 w-5 shrink-0"
                                            aria-hidden="true"
                                        />

                                        <div>
                                            <p className="font-bold">
                                                Batch error
                                            </p>

                                            <p className="mt-1 text-sm leading-6">
                                                {batch.error_message}
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
                                            Validation and processing
                                            results for individual CSV
                                            rows.
                                        </p>
                                    </div>

                                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                                        <label className="block">
                                            <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-600">
                                                Row status
                                            </span>

                                            <select
                                                value={rowStatusFilter}
                                                onChange={(event) => {
                                                    setRowStatusFilter(
                                                        event.target
                                                            .value as
                                                        | ImportRowStatus
                                                        | "",
                                                    );
                                                }}
                                                className="min-h-11 min-w-44 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
                                            >
                                                <option value="">
                                                    All statuses
                                                </option>

                                                {IMPORT_ROW_STATUSES.map(
                                                    (statusOption) => (
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
                                                value={pageSize}
                                                onChange={(event) => {
                                                    setPageSize(
                                                        Number(
                                                            event.target
                                                                .value,
                                                        ),
                                                    );
                                                }}
                                                className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
                                            >
                                                {PAGE_SIZE_OPTIONS.map(
                                                    (option) => (
                                                        <option
                                                            key={option}
                                                            value={option}
                                                        >
                                                            {option}
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
                                            : "Row-level results will appear after the CSV has been uploaded and processed."}
                                    </p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-slate-200">
                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600">
                                                    Row
                                                </th>

                                                <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600">
                                                    Status
                                                </th>

                                                <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600">
                                                    Result
                                                </th>

                                                <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600">
                                                    Imported record
                                                </th>

                                                <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600">
                                                    Source data
                                                </th>
                                            </tr>
                                        </thead>

                                        <tbody className="divide-y divide-slate-200 bg-white">
                                            {rows.map((row) => (
                                                <tr
                                                    key={row.id}
                                                    className={[
                                                        "align-top hover:bg-slate-50",
                                                        ISSUE_ROW_STATUSES.has(
                                                            row.status,
                                                        )
                                                            ? "bg-red-50/20"
                                                            : "",
                                                    ].join(" ")}
                                                >
                                                    <td className="whitespace-nowrap px-6 py-4 text-sm font-bold text-slate-950">
                                                        {row.row_number}
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
                                                            row={row}
                                                        />
                                                    </td>

                                                    <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-700">
                                                        {row.imported_record_id !==
                                                            null ? (
                                                            <span className="font-bold text-slate-950">
                                                                #
                                                                {
                                                                    row.imported_record_id
                                                                }
                                                            </span>
                                                        ) : (
                                                            <span className="text-slate-500">
                                                                Not created
                                                            </span>
                                                        )}

                                                        {row.processed_at ? (
                                                            <p className="mt-1 text-xs text-slate-500">
                                                                {formatDateTime(
                                                                    row.processed_at,
                                                                )}
                                                            </p>
                                                        ) : null}
                                                    </td>

                                                    <td className="min-w-[360px] px-6 py-4">
                                                        <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                                                            {stringifyMetadata(
                                                                row.raw_data,
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
                                            ))}
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
                                            setPage((current) =>
                                                Math.max(
                                                    current - 1,
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

                                    <span className="text-sm font-bold text-slate-700">
                                        Page {page} of {totalPages}
                                    </span>

                                    <button
                                        type="button"
                                        disabled={
                                            page >= totalPages ||
                                            isLoadingRows
                                        }
                                        onClick={() => {
                                            setPage((current) =>
                                                Math.min(
                                                    current + 1,
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