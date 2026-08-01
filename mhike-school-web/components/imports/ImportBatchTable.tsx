"use client";

import Link from "next/link";
import {
    Archive,
    ChevronLeft,
    ChevronRight,
    FileSpreadsheet,
    Loader2,
    MoreHorizontal,
    RotateCcw,
    XCircle,
} from "lucide-react";

import ImportStatusBadge from "@/components/imports/ImportStatusBadge";

export type ImportBatchTableItem = {
    id: number;
    import_type: string;
    filename?: string | null;
    status: string;

    total_rows?: number | null;

    /**
     * Current backend counters.
     */
    validated_rows?: number | null;
    successful_rows?: number | null;
    warning_rows?: number | null;
    failed_rows?: number | null;
    skipped_rows?: number | null;
    processed_rows?: number | null;

    /**
     * Compatibility counters used by older dashboard mapping code.
     */
    valid_rows?: number | null;
    invalid_rows?: number | null;
    imported_rows?: number | null;

    created_at: string;
    updated_at?: string | null;
    archived_at?: string | null;
};

type ImportBatchTableProps = {
    batches: ImportBatchTableItem[];
    isLoading?: boolean;
    errorMessage?: string | null;
    page?: number;
    pageSize?: number;
    totalItems?: number;
    onPageChange?: (page: number) => void;
    onCancel?: (batch: ImportBatchTableItem) => Promise<void> | void;
    onArchive?: (batch: ImportBatchTableItem) => Promise<void> | void;
    onRestore?: (batch: ImportBatchTableItem) => Promise<void> | void;
    actionBatchId?: number | null;
    detailsBasePath?: string;
    emptyTitle?: string;
    emptyDescription?: string;
    className?: string;
};

const CANCELLABLE_STATUSES = new Set([
    "created",
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

const ARCHIVABLE_STATUSES = new Set([
    "completed",
    "completed_with_errors",
    "partially_completed",
    "failed",
    "cancelled",
]);

function normaliseStatus(status: string): string {
    return status
        .trim()
        .toLowerCase()
        .replace(/[\s-]+/g, "_");
}

function formatImportType(importType: string): string {
    const normalised = importType.trim().replace(/[_-]+/g, " ");

    if (!normalised) {
        return "Import";
    }

    return normalised
        .split(/\s+/)
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function formatDate(value: string | null | undefined): string {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(date);
}

function formatNumber(value: number | null | undefined): string {
    if (
        value === null ||
        value === undefined ||
        !Number.isFinite(value)
    ) {
        return "0";
    }

    return new Intl.NumberFormat("en-GB").format(
        Math.max(0, value),
    );
}

function resolveValidatedRows(
    batch: ImportBatchTableItem,
): number | null | undefined {
    return batch.validated_rows ?? batch.valid_rows;
}

function resolveFailedRows(
    batch: ImportBatchTableItem,
): number | null | undefined {
    return batch.failed_rows ?? batch.invalid_rows;
}

function resolveSuccessfulRows(
    batch: ImportBatchTableItem,
): number | null | undefined {
    return (
        batch.successful_rows ??
        batch.imported_rows ??
        batch.processed_rows
    );
}

function canCancel(status: string): boolean {
    return CANCELLABLE_STATUSES.has(
        normaliseStatus(status),
    );
}

function canArchive(status: string): boolean {
    return ARCHIVABLE_STATUSES.has(
        normaliseStatus(status),
    );
}

function isArchived(batch: ImportBatchTableItem): boolean {
    return (
        normaliseStatus(batch.status) === "archived" ||
        Boolean(batch.archived_at)
    );
}

export default function ImportBatchTable({
    batches,
    isLoading = false,
    errorMessage = null,
    page = 1,
    pageSize = 20,
    totalItems,
    onPageChange,
    onCancel,
    onArchive,
    onRestore,
    actionBatchId = null,
    detailsBasePath = "/school-admin/imports",
    emptyTitle = "No imports found",
    emptyDescription = "Uploaded import batches will appear here.",
    className = "",
}: ImportBatchTableProps) {
    const safePageSize = Math.max(pageSize, 1);
    const resolvedTotalItems = Math.max(
        totalItems ?? batches.length,
        0,
    );

    const totalPages = Math.max(
        1,
        Math.ceil(resolvedTotalItems / safePageSize),
    );

    const currentPage = Math.min(
        Math.max(page, 1),
        totalPages,
    );

    const firstItem =
        resolvedTotalItems === 0
            ? 0
            : (currentPage - 1) * safePageSize + 1;

    const lastItem = Math.min(
        currentPage * safePageSize,
        resolvedTotalItems,
    );

    const previousDisabled =
        currentPage <= 1 ||
        !onPageChange ||
        isLoading;

    const nextDisabled =
        currentPage >= totalPages ||
        !onPageChange ||
        isLoading;

    return (
        <section
            className={[
                "overflow-hidden rounded-2xl border border-slate-200",
                "bg-white shadow-sm",
                className,
            ]
                .filter(Boolean)
                .join(" ")}
            aria-busy={isLoading}
        >
            <div className="flex flex-col gap-2 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="text-lg font-bold text-slate-950">
                        Import history
                    </h2>

                    <p className="mt-1 text-sm text-slate-600">
                        Review uploaded files, row totals and import progress.
                    </p>
                </div>

                <p className="text-sm font-medium text-slate-500">
                    {formatNumber(resolvedTotalItems)}{" "}
                    {resolvedTotalItems === 1 ? "batch" : "batches"}
                </p>
            </div>

            {errorMessage ? (
                <div
                    role="alert"
                    className="border-b border-red-200 bg-red-50 px-5 py-4 text-sm font-medium text-red-800"
                >
                    {errorMessage}
                </div>
            ) : null}

            {isLoading ? (
                <div className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
                    <Loader2
                        className="h-8 w-8 animate-spin text-blue-700"
                        aria-hidden="true"
                    />

                    <p className="mt-4 text-sm font-semibold text-slate-700">
                        Loading import history…
                    </p>
                </div>
            ) : batches.length === 0 ? (
                <div className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
                    <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
                        <FileSpreadsheet
                            className="h-7 w-7"
                            aria-hidden="true"
                        />
                    </span>

                    <h3 className="mt-4 text-base font-bold text-slate-950">
                        {emptyTitle}
                    </h3>

                    <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">
                        {emptyDescription}
                    </p>
                </div>
            ) : (
                <>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200">
                            <caption className="sr-only">
                                Import batch history and available actions
                            </caption>

                            <thead className="bg-slate-50">
                                <tr>
                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        File
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        Import type
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        Status
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-right text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        Rows
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-right text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        Validated
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-right text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        Failed
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-right text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        Successful
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-600"
                                    >
                                        Created
                                    </th>

                                    <th
                                        scope="col"
                                        className="px-5 py-3 text-right"
                                    >
                                        <span className="sr-only">
                                            Actions
                                        </span>
                                    </th>
                                </tr>
                            </thead>

                            <tbody className="divide-y divide-slate-100 bg-white">
                                {batches.map((batch) => {
                                    const archived = isArchived(batch);
                                    const isActionLoading =
                                        actionBatchId === batch.id;

                                    const detailsPath =
                                        `${detailsBasePath}/${batch.id}`;

                                    return (
                                        <tr
                                            key={batch.id}
                                            className={[
                                                "transition hover:bg-slate-50",
                                                archived
                                                    ? "bg-slate-50/60"
                                                    : "",
                                            ]
                                                .filter(Boolean)
                                                .join(" ")}
                                        >
                                            <td className="max-w-72 px-5 py-4">
                                                <Link
                                                    href={detailsPath}
                                                    className="group flex items-center gap-3"
                                                >
                                                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                                                        <FileSpreadsheet
                                                            className="h-5 w-5"
                                                            aria-hidden="true"
                                                        />
                                                    </span>

                                                    <div className="min-w-0">
                                                        <p className="truncate text-sm font-semibold text-slate-950 group-hover:text-blue-700">
                                                            {batch.filename ||
                                                                `Import batch ${batch.id}`}
                                                        </p>

                                                        <p className="mt-1 text-xs text-slate-500">
                                                            Batch #{batch.id}
                                                            {archived
                                                                ? " · Archived"
                                                                : ""}
                                                        </p>
                                                    </div>
                                                </Link>
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4 text-sm font-medium text-slate-700">
                                                {formatImportType(
                                                    batch.import_type,
                                                )}
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4">
                                                <ImportStatusBadge
                                                    status={batch.status}
                                                />
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4 text-right text-sm font-semibold text-slate-700">
                                                {formatNumber(
                                                    batch.total_rows,
                                                )}
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4 text-right text-sm font-semibold text-emerald-700">
                                                {formatNumber(
                                                    resolveValidatedRows(
                                                        batch,
                                                    ),
                                                )}
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4 text-right text-sm font-semibold text-red-700">
                                                {formatNumber(
                                                    resolveFailedRows(batch),
                                                )}
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4 text-right text-sm font-semibold text-blue-700">
                                                {formatNumber(
                                                    resolveSuccessfulRows(
                                                        batch,
                                                    ),
                                                )}
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4 text-sm text-slate-600">
                                                {formatDate(batch.created_at)}
                                            </td>

                                            <td className="whitespace-nowrap px-5 py-4 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <Link
                                                        href={detailsPath}
                                                        className={[
                                                            "inline-flex min-h-9 items-center justify-center",
                                                            "rounded-lg border border-slate-300 bg-white",
                                                            "px-3 text-xs font-semibold text-slate-700",
                                                            "transition hover:bg-slate-100",
                                                        ].join(" ")}
                                                    >
                                                        View
                                                    </Link>

                                                    {isActionLoading ? (
                                                        <span
                                                            className="inline-flex h-9 w-9 items-center justify-center text-slate-500"
                                                            aria-label={`Processing action for import batch ${batch.id}`}
                                                        >
                                                            <Loader2
                                                                className="h-5 w-5 animate-spin"
                                                                aria-hidden="true"
                                                            />
                                                        </span>
                                                    ) : archived &&
                                                        onRestore ? (
                                                        <button
                                                            type="button"
                                                            className={[
                                                                "inline-flex h-9 w-9 items-center justify-center",
                                                                "rounded-lg border border-slate-300 bg-white",
                                                                "text-slate-600 transition hover:bg-slate-100",
                                                                "hover:text-slate-950",
                                                            ].join(" ")}
                                                            aria-label={`Restore import batch ${batch.id}`}
                                                            title="Restore import"
                                                            onClick={() => {
                                                                void onRestore(
                                                                    batch,
                                                                );
                                                            }}
                                                        >
                                                            <RotateCcw
                                                                className="h-4 w-4"
                                                                aria-hidden="true"
                                                            />
                                                        </button>
                                                    ) : canCancel(
                                                        batch.status,
                                                    ) && onCancel ? (
                                                        <button
                                                            type="button"
                                                            className={[
                                                                "inline-flex h-9 w-9 items-center justify-center",
                                                                "rounded-lg border border-red-200 bg-red-50",
                                                                "text-red-700 transition hover:bg-red-100",
                                                            ].join(" ")}
                                                            aria-label={`Cancel import batch ${batch.id}`}
                                                            title="Cancel import"
                                                            onClick={() => {
                                                                void onCancel(
                                                                    batch,
                                                                );
                                                            }}
                                                        >
                                                            <XCircle
                                                                className="h-4 w-4"
                                                                aria-hidden="true"
                                                            />
                                                        </button>
                                                    ) : canArchive(
                                                        batch.status,
                                                    ) && onArchive ? (
                                                        <button
                                                            type="button"
                                                            className={[
                                                                "inline-flex h-9 w-9 items-center justify-center",
                                                                "rounded-lg border border-slate-300 bg-white",
                                                                "text-slate-600 transition hover:bg-slate-100",
                                                                "hover:text-slate-950",
                                                            ].join(" ")}
                                                            aria-label={`Archive import batch ${batch.id}`}
                                                            title="Archive import"
                                                            onClick={() => {
                                                                void onArchive(
                                                                    batch,
                                                                );
                                                            }}
                                                        >
                                                            <Archive
                                                                className="h-4 w-4"
                                                                aria-hidden="true"
                                                            />
                                                        </button>
                                                    ) : (
                                                        <span
                                                            className="inline-flex h-9 w-9 items-center justify-center text-slate-300"
                                                            aria-hidden="true"
                                                        >
                                                            <MoreHorizontal className="h-4 w-4" />
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    <div className="flex flex-col gap-3 border-t border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                        <p className="text-sm text-slate-600">
                            Showing{" "}
                            <span className="font-semibold text-slate-900">
                                {formatNumber(firstItem)}
                            </span>{" "}
                            to{" "}
                            <span className="font-semibold text-slate-900">
                                {formatNumber(lastItem)}
                            </span>{" "}
                            of{" "}
                            <span className="font-semibold text-slate-900">
                                {formatNumber(resolvedTotalItems)}
                            </span>
                        </p>

                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                disabled={previousDisabled}
                                className={[
                                    "inline-flex min-h-9 items-center justify-center gap-1",
                                    "rounded-lg border border-slate-300 bg-white px-3",
                                    "text-sm font-semibold text-slate-700 transition",
                                    "hover:bg-slate-100 disabled:cursor-not-allowed",
                                    "disabled:opacity-40",
                                ].join(" ")}
                                onClick={() => {
                                    onPageChange?.(currentPage - 1);
                                }}
                            >
                                <ChevronLeft
                                    className="h-4 w-4"
                                    aria-hidden="true"
                                />
                                Previous
                            </button>

                            <span
                                className="px-2 text-sm font-semibold text-slate-700"
                                aria-live="polite"
                            >
                                Page {currentPage} of {totalPages}
                            </span>

                            <button
                                type="button"
                                disabled={nextDisabled}
                                className={[
                                    "inline-flex min-h-9 items-center justify-center gap-1",
                                    "rounded-lg border border-slate-300 bg-white px-3",
                                    "text-sm font-semibold text-slate-700 transition",
                                    "hover:bg-slate-100 disabled:cursor-not-allowed",
                                    "disabled:opacity-40",
                                ].join(" ")}
                                onClick={() => {
                                    onPageChange?.(currentPage + 1);
                                }}
                            >
                                Next
                                <ChevronRight
                                    className="h-4 w-4"
                                    aria-hidden="true"
                                />
                            </button>
                        </div>
                    </div>
                </>
            )}
        </section>
    );
}
