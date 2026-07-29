"use client";

import {
    Archive,
    Filter,
    RefreshCcw,
    Search,
    X,
} from "lucide-react";

export type ImportArchiveFilter =
    | "active"
    | "archived"
    | "all";

export type ImportFiltersValue = {
    search: string;
    importType: string;
    status: string;
    archive: ImportArchiveFilter;
};

export type ImportFilterOption = {
    value: string;
    label: string;
};

type ImportFiltersProps = {
    value: ImportFiltersValue;
    onChange: (value: ImportFiltersValue) => void;
    importTypeOptions?: ImportFilterOption[];
    statusOptions?: ImportFilterOption[];
    isLoading?: boolean;
    onRefresh?: () => Promise<void> | void;
    className?: string;
};

const DEFAULT_IMPORT_TYPE_OPTIONS: ImportFilterOption[] = [
    { value: "", label: "All import types" },
    { value: "students", label: "Students" },
    { value: "staff", label: "Staff" },
    { value: "parents", label: "Parents" },
    { value: "classes", label: "Classes" },
    { value: "subjects", label: "Subjects" },
    { value: "teaching_assignments", label: "Teaching assignments" },
];

const DEFAULT_STATUS_OPTIONS: ImportFilterOption[] = [
    { value: "", label: "All statuses" },
    { value: "created", label: "Created" },
    { value: "pending", label: "Pending" },
    { value: "uploaded", label: "Uploaded" },
    { value: "validating", label: "Validating" },
    { value: "validated", label: "Validated" },
    { value: "processing", label: "Processing" },
    { value: "importing", label: "Importing" },
    { value: "completed", label: "Completed" },
    { value: "partially_completed", label: "Partially completed" },
    { value: "failed", label: "Failed" },
    { value: "cancelled", label: "Cancelled" },
    { value: "archived", label: "Archived" },
];

function hasActiveFilters(value: ImportFiltersValue): boolean {
    return Boolean(
        value.search.trim() ||
        value.importType ||
        value.status ||
        value.archive !== "active",
    );
}

export default function ImportFilters({
    value,
    onChange,
    importTypeOptions = DEFAULT_IMPORT_TYPE_OPTIONS,
    statusOptions = DEFAULT_STATUS_OPTIONS,
    isLoading = false,
    onRefresh,
    className = "",
}: ImportFiltersProps) {
    const activeFilters = hasActiveFilters(value);

    function updateValue(
        changes: Partial<ImportFiltersValue>,
    ): void {
        onChange({
            ...value,
            ...changes,
        });
    }

    function clearFilters(): void {
        onChange({
            search: "",
            importType: "",
            status: "",
            archive: "active",
        });
    }

    return (
        <section
            className={[
                "rounded-2xl border border-slate-200 bg-white",
                "p-4 shadow-sm",
                className,
            ]
                .filter(Boolean)
                .join(" ")}
        >
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
                        <Filter className="h-5 w-5" aria-hidden="true" />
                    </span>

                    <div>
                        <h2 className="text-base font-bold text-slate-950">
                            Filter imports
                        </h2>

                        <p className="text-sm text-slate-600">
                            Search and narrow the import history.
                        </p>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {activeFilters ? (
                        <button
                            type="button"
                            className={[
                                "inline-flex min-h-10 items-center justify-center gap-2",
                                "rounded-xl border border-slate-300 bg-white px-4",
                                "text-sm font-semibold text-slate-700 transition",
                                "hover:bg-slate-100",
                            ].join(" ")}
                            onClick={clearFilters}
                        >
                            <X className="h-4 w-4" aria-hidden="true" />
                            Clear filters
                        </button>
                    ) : null}

                    {onRefresh ? (
                        <button
                            type="button"
                            disabled={isLoading}
                            className={[
                                "inline-flex min-h-10 items-center justify-center gap-2",
                                "rounded-xl bg-slate-900 px-4",
                                "text-sm font-semibold text-white transition",
                                "hover:bg-slate-800",
                                "disabled:cursor-not-allowed disabled:opacity-50",
                            ].join(" ")}
                            onClick={() => {
                                void onRefresh();
                            }}
                        >
                            <RefreshCcw
                                className={[
                                    "h-4 w-4",
                                    isLoading ? "animate-spin" : "",
                                ].join(" ")}
                                aria-hidden="true"
                            />
                            Refresh
                        </button>
                    ) : null}
                </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-[minmax(16rem,2fr)_repeat(3,minmax(10rem,1fr))]">
                <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-700">
                        Search
                    </span>

                    <span className="relative block">
                        <Search
                            className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
                            aria-hidden="true"
                        />

                        <input
                            type="search"
                            value={value.search}
                            placeholder="Search by file name or batch ID"
                            className={[
                                "min-h-11 w-full rounded-xl border border-slate-300",
                                "bg-white py-2 pl-10 pr-10 text-sm text-slate-950",
                                "outline-none transition",
                                "placeholder:text-slate-400",
                                "focus:border-blue-600 focus:ring-4 focus:ring-blue-100",
                            ].join(" ")}
                            onChange={(event) => {
                                updateValue({
                                    search: event.target.value,
                                });
                            }}
                        />

                        {value.search ? (
                            <button
                                type="button"
                                className={[
                                    "absolute right-2 top-1/2 flex h-7 w-7",
                                    "-translate-y-1/2 items-center justify-center",
                                    "rounded-lg text-slate-500 transition",
                                    "hover:bg-slate-100 hover:text-slate-900",
                                ].join(" ")}
                                aria-label="Clear search"
                                onClick={() => {
                                    updateValue({ search: "" });
                                }}
                            >
                                <X className="h-4 w-4" aria-hidden="true" />
                            </button>
                        ) : null}
                    </span>
                </label>

                <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-700">
                        Import type
                    </span>

                    <select
                        value={value.importType}
                        className={[
                            "min-h-11 w-full rounded-xl border border-slate-300",
                            "bg-white px-3 py-2 text-sm text-slate-950",
                            "outline-none transition",
                            "focus:border-blue-600 focus:ring-4 focus:ring-blue-100",
                        ].join(" ")}
                        onChange={(event) => {
                            updateValue({
                                importType: event.target.value,
                            });
                        }}
                    >
                        {importTypeOptions.map((option) => (
                            <option
                                key={option.value || "all-import-types"}
                                value={option.value}
                            >
                                {option.label}
                            </option>
                        ))}
                    </select>
                </label>

                <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-700">
                        Status
                    </span>

                    <select
                        value={value.status}
                        className={[
                            "min-h-11 w-full rounded-xl border border-slate-300",
                            "bg-white px-3 py-2 text-sm text-slate-950",
                            "outline-none transition",
                            "focus:border-blue-600 focus:ring-4 focus:ring-blue-100",
                        ].join(" ")}
                        onChange={(event) => {
                            updateValue({
                                status: event.target.value,
                            });
                        }}
                    >
                        {statusOptions.map((option) => (
                            <option
                                key={option.value || "all-statuses"}
                                value={option.value}
                            >
                                {option.label}
                            </option>
                        ))}
                    </select>
                </label>

                <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-700">
                        Records
                    </span>

                    <span className="relative block">
                        <Archive
                            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                            aria-hidden="true"
                        />

                        <select
                            value={value.archive}
                            className={[
                                "min-h-11 w-full appearance-none rounded-xl",
                                "border border-slate-300 bg-white py-2 pl-10 pr-8",
                                "text-sm text-slate-950 outline-none transition",
                                "focus:border-blue-600 focus:ring-4 focus:ring-blue-100",
                            ].join(" ")}
                            onChange={(event) => {
                                updateValue({
                                    archive:
                                        event.target.value as ImportArchiveFilter,
                                });
                            }}
                        >
                            <option value="active">Active records</option>
                            <option value="archived">Archived records</option>
                            <option value="all">All records</option>
                        </select>
                    </span>
                </label>
            </div>

            {activeFilters ? (
                <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                    {value.search.trim() ? (
                        <FilterChip
                            label={`Search: ${value.search.trim()}`}
                            onRemove={() => {
                                updateValue({ search: "" });
                            }}
                        />
                    ) : null}

                    {value.importType ? (
                        <FilterChip
                            label={
                                importTypeOptions.find(
                                    (option) =>
                                        option.value === value.importType,
                                )?.label || value.importType
                            }
                            onRemove={() => {
                                updateValue({ importType: "" });
                            }}
                        />
                    ) : null}

                    {value.status ? (
                        <FilterChip
                            label={
                                statusOptions.find(
                                    (option) => option.value === value.status,
                                )?.label || value.status
                            }
                            onRemove={() => {
                                updateValue({ status: "" });
                            }}
                        />
                    ) : null}

                    {value.archive !== "active" ? (
                        <FilterChip
                            label={
                                value.archive === "archived"
                                    ? "Archived records"
                                    : "All records"
                            }
                            onRemove={() => {
                                updateValue({ archive: "active" });
                            }}
                        />
                    ) : null}
                </div>
            ) : null}
        </section>
    );
}

type FilterChipProps = {
    label: string;
    onRemove: () => void;
};

function FilterChip({
    label,
    onRemove,
}: FilterChipProps) {
    return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 py-1 pl-3 pr-1 text-xs font-semibold text-blue-800">
            <span className="max-w-56 truncate">{label}</span>

            <button
                type="button"
                className="flex h-6 w-6 items-center justify-center rounded-full transition hover:bg-blue-100"
                aria-label={`Remove ${label} filter`}
                onClick={onRemove}
            >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
        </span>
    );
}