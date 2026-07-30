"use client";

import {
    useMemo,
    useRef,
    useState,
    type ChangeEvent,
    type DragEvent,
    type FormEvent,
} from "react";
import {
    AlertCircle,
    CheckCircle2,
    FileSpreadsheet,
    Loader2,
    Upload,
    X,
} from "lucide-react";

export type ImportUploadPayload = {
    file: File;
    importType: string;
};

export type ImportTypeOption = {
    value: string;
    label: string;
    description?: string;
};

type ImportUploadPanelProps = {
    title?: string;
    description?: string;

    acceptedFileTypes?: string;
    maximumFileSizeMb?: number;

    importTypes?: readonly ImportTypeOption[];
    defaultImportType?: string;

    disabled?: boolean;
    isUploading?: boolean;

    errorMessage?: string | null;
    successMessage?: string | null;

    onUpload: (
        payload: ImportUploadPayload,
    ) => Promise<void> | void;

    onSelectionChange?: (
        payload: {
            file: File | null;
            importType: string;
        },
    ) => void;

    className?: string;
};

const DEFAULT_IMPORT_TYPES: readonly ImportTypeOption[] = [
    {
        value: "students",
        label: "Students",
        description:
            "Import student identity, year-group and form information.",
    },
    {
        value: "parents",
        label: "Parents",
        description:
            "Import parent or guardian account information.",
    },
    {
        value: "teachers",
        label: "Teachers",
        description:
            "Import teaching staff and account information.",
    },
    {
        value: "enrollments",
        label: "Enrolments",
        description:
            "Import student class or course enrolments.",
    },
];

function formatFileSize(
    sizeInBytes: number,
): string {
    if (sizeInBytes < 1024) {
        return `${sizeInBytes} B`;
    }

    const sizeInKilobytes =
        sizeInBytes / 1024;

    if (sizeInKilobytes < 1024) {
        return `${sizeInKilobytes.toFixed(1)} KB`;
    }

    const sizeInMegabytes =
        sizeInKilobytes / 1024;

    return `${sizeInMegabytes.toFixed(1)} MB`;
}

function isCsvFile(file: File): boolean {
    const fileName =
        file.name
            .trim()
            .toLowerCase();

    return (
        fileName.endsWith(".csv") ||
        file.type === "text/csv" ||
        file.type === "application/csv" ||
        file.type ===
        "application/vnd.ms-excel"
    );
}

export default function ImportUploadPanel({
    title = "Upload CSV data",
    description =
    "Choose an import type and upload a CSV file for validation.",

    acceptedFileTypes =
    ".csv,text/csv,application/csv,application/vnd.ms-excel",

    maximumFileSizeMb = 10,

    importTypes = DEFAULT_IMPORT_TYPES,
    defaultImportType = "",

    disabled = false,
    isUploading = false,

    errorMessage = null,
    successMessage = null,

    onUpload,
    onSelectionChange,

    className = "",
}: ImportUploadPanelProps) {
    const fileInputRef =
        useRef<HTMLInputElement | null>(
            null,
        );

    const [
        selectedFile,
        setSelectedFile,
    ] = useState<File | null>(null);

    const [
        selectedImportType,
        setSelectedImportType,
    ] = useState(defaultImportType);

    const [
        isDragging,
        setIsDragging,
    ] = useState(false);

    const [
        validationError,
        setValidationError,
    ] = useState<string | null>(
        null,
    );

    const maximumFileSizeBytes =
        maximumFileSizeMb *
        1024 *
        1024;

    const effectiveErrorMessage =
        validationError ??
        errorMessage;

    const selectedImportTypeOption =
        useMemo(
            () =>
                importTypes.find(
                    (option) =>
                        option.value ===
                        selectedImportType,
                ) ?? null,
            [
                importTypes,
                selectedImportType,
            ],
        );

    const canUpload =
        useMemo(
            () =>
                selectedFile !== null &&
                selectedImportType.trim() !==
                "" &&
                !disabled &&
                !isUploading &&
                validationError === null,
            [
                disabled,
                isUploading,
                selectedFile,
                selectedImportType,
                validationError,
            ],
        );

    function notifySelectionChange(
        file: File | null,
        importType: string,
    ): void {
        onSelectionChange?.({
            file,
            importType,
        });
    }

    function updateSelectedFile(
        file: File | null,
    ): void {
        setSelectedFile(file);

        notifySelectionChange(
            file,
            selectedImportType,
        );
    }

    function updateImportType(
        importType: string,
    ): void {
        setSelectedImportType(
            importType,
        );

        setValidationError(null);

        notifySelectionChange(
            selectedFile,
            importType,
        );
    }

    function validateAndSelectFile(
        file: File | null,
    ): void {
        setValidationError(null);

        if (!file) {
            updateSelectedFile(null);
            return;
        }

        if (!isCsvFile(file)) {
            setValidationError(
                "Please select a valid CSV file.",
            );

            updateSelectedFile(null);
            return;
        }

        if (file.size === 0) {
            setValidationError(
                "The selected CSV file is empty.",
            );

            updateSelectedFile(null);
            return;
        }

        if (
            file.size >
            maximumFileSizeBytes
        ) {
            setValidationError(
                `The file is too large. The maximum size is ${maximumFileSizeMb} MB.`,
            );

            updateSelectedFile(null);
            return;
        }

        updateSelectedFile(file);
    }

    function handleFileInputChange(
        event:
            ChangeEvent<HTMLInputElement>,
    ): void {
        const file =
            event.target.files?.[0] ??
            null;

        validateAndSelectFile(file);
    }

    function handleDragEnter(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();

        if (
            !disabled &&
            !isUploading
        ) {
            setIsDragging(true);
        }
    }

    function handleDragOver(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();
    }

    function handleDragLeave(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();

        if (
            event.currentTarget ===
            event.target
        ) {
            setIsDragging(false);
        }
    }

    function handleDrop(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();
        setIsDragging(false);

        if (
            disabled ||
            isUploading
        ) {
            return;
        }

        const file =
            event.dataTransfer
                .files?.[0] ??
            null;

        validateAndSelectFile(file);
    }

    function openFilePicker(): void {
        if (
            !disabled &&
            !isUploading
        ) {
            fileInputRef.current?.click();
        }
    }

    function clearSelectedFile(): void {
        setValidationError(null);

        updateSelectedFile(null);

        if (fileInputRef.current) {
            fileInputRef.current.value =
                "";
        }
    }

    async function handleSubmit(
        event:
            FormEvent<HTMLFormElement>,
    ): Promise<void> {
        event.preventDefault();

        setValidationError(null);

        if (!selectedImportType) {
            setValidationError(
                "Please select an import type before uploading the CSV file.",
            );

            return;
        }

        if (!selectedFile) {
            setValidationError(
                "Please choose a CSV file before uploading.",
            );

            return;
        }

        if (!canUpload) {
            return;
        }

        try {
            await onUpload({
                file: selectedFile,
                importType:
                    selectedImportType,
            });

            clearSelectedFile();
        } catch {
            /*
             * The parent owns server/API error handling.
             * The selected file is retained so the
             * administrator can retry.
             */
        }
    }

    return (
        <section
            className={[
                "rounded-2xl border border-slate-200 bg-white p-6 shadow-sm",
                className,
            ]
                .filter(Boolean)
                .join(" ")}
        >
            <div>
                <h2 className="text-xl font-bold text-slate-950">
                    {title}
                </h2>

                <p className="mt-1 text-sm leading-6 text-slate-600">
                    {description}
                </p>
            </div>

            <form
                className="mt-6 space-y-5"
                onSubmit={handleSubmit}
            >
                <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-900">
                        Import type
                    </span>

                    <select
                        value={
                            selectedImportType
                        }
                        disabled={
                            disabled ||
                            isUploading
                        }
                        className={[
                            "min-h-11 w-full rounded-xl border border-slate-300",
                            "bg-white px-3 py-2 text-sm text-slate-950 shadow-sm",
                            "outline-none transition focus:border-blue-500",
                            "focus:ring-2 focus:ring-blue-200",
                            "disabled:cursor-not-allowed disabled:bg-slate-100",
                            "disabled:text-slate-500",
                        ].join(" ")}
                        onChange={(event) => {
                            updateImportType(
                                event.target
                                    .value,
                            );
                        }}
                    >
                        <option value="">
                            Select import type
                        </option>

                        {importTypes.map(
                            (option) => (
                                <option
                                    key={
                                        option.value
                                    }
                                    value={
                                        option.value
                                    }
                                >
                                    {
                                        option.label
                                    }
                                </option>
                            ),
                        )}
                    </select>

                    {selectedImportTypeOption
                        ?.description ? (
                        <span className="mt-2 block text-xs leading-5 text-slate-500">
                            {
                                selectedImportTypeOption.description
                            }
                        </span>
                    ) : null}
                </label>

                <input
                    ref={fileInputRef}
                    type="file"
                    accept={
                        acceptedFileTypes
                    }
                    className="sr-only"
                    disabled={
                        disabled ||
                        isUploading
                    }
                    onChange={
                        handleFileInputChange
                    }
                />

                <div
                    role="button"
                    tabIndex={
                        disabled ||
                            isUploading
                            ? -1
                            : 0
                    }
                    aria-disabled={
                        disabled ||
                        isUploading
                    }
                    aria-label="Choose CSV file"
                    className={[
                        "flex min-h-56 flex-col items-center justify-center rounded-2xl",
                        "border-2 border-dashed px-6 py-8 text-center transition",
                        isDragging
                            ? "border-blue-500 bg-blue-50"
                            : "border-slate-300 bg-slate-50",
                        disabled ||
                            isUploading
                            ? "cursor-not-allowed opacity-60"
                            : "cursor-pointer hover:border-blue-400 hover:bg-blue-50/60",
                    ].join(" ")}
                    onClick={
                        openFilePicker
                    }
                    onKeyDown={(
                        event,
                    ) => {
                        if (
                            event.key ===
                            "Enter" ||
                            event.key ===
                            " "
                        ) {
                            event.preventDefault();

                            openFilePicker();
                        }
                    }}
                    onDragEnter={
                        handleDragEnter
                    }
                    onDragOver={
                        handleDragOver
                    }
                    onDragLeave={
                        handleDragLeave
                    }
                    onDrop={handleDrop}
                >
                    <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100 text-blue-700">
                        <Upload
                            className="h-7 w-7"
                            aria-hidden="true"
                        />
                    </span>

                    <p className="mt-4 text-base font-semibold text-slate-950">
                        Drop your CSV file here
                    </p>

                    <p className="mt-1 text-sm text-slate-600">
                        or click to browse
                        your computer
                    </p>

                    <p className="mt-3 text-xs font-medium text-slate-500">
                        CSV files only, up
                        to{" "}
                        {
                            maximumFileSizeMb
                        }{" "}
                        MB
                    </p>
                </div>

                {selectedFile ? (
                    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                            <FileSpreadsheet
                                className="h-6 w-6"
                                aria-hidden="true"
                            />
                        </span>

                        <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-slate-950">
                                {
                                    selectedFile.name
                                }
                            </p>

                            <p className="mt-1 text-xs text-slate-500">
                                {formatFileSize(
                                    selectedFile.size,
                                )}
                            </p>
                        </div>

                        <button
                            type="button"
                            disabled={
                                disabled ||
                                isUploading
                            }
                            aria-label="Remove selected file"
                            className={[
                                "inline-flex h-9 w-9 items-center justify-center rounded-lg",
                                "text-slate-500 transition hover:bg-slate-200",
                                "hover:text-slate-900 disabled:cursor-not-allowed",
                                "disabled:opacity-50",
                            ].join(" ")}
                            onClick={(
                                event,
                            ) => {
                                event.stopPropagation();

                                clearSelectedFile();
                            }}
                        >
                            <X
                                className="h-5 w-5"
                                aria-hidden="true"
                            />
                        </button>
                    </div>
                ) : null}

                {effectiveErrorMessage ? (
                    <div
                        role="alert"
                        className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
                    >
                        <AlertCircle
                            className="mt-0.5 h-5 w-5 shrink-0"
                            aria-hidden="true"
                        />

                        <p className="text-sm font-medium">
                            {
                                effectiveErrorMessage
                            }
                        </p>
                    </div>
                ) : null}

                {successMessage ? (
                    <div
                        role="status"
                        className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800"
                    >
                        <CheckCircle2
                            className="mt-0.5 h-5 w-5 shrink-0"
                            aria-hidden="true"
                        />

                        <p className="text-sm font-medium">
                            {successMessage}
                        </p>
                    </div>
                ) : null}

                <button
                    type="submit"
                    disabled={!canUpload}
                    className={[
                        "inline-flex min-h-11 w-full items-center justify-center gap-2",
                        "rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold",
                        "text-white transition hover:bg-slate-800",
                        "disabled:cursor-not-allowed disabled:bg-slate-300",
                        "sm:w-auto",
                    ].join(" ")}
                >
                    {isUploading ? (
                        <>
                            <Loader2
                                className="h-5 w-5 animate-spin"
                                aria-hidden="true"
                            />

                            Uploading…
                        </>
                    ) : (
                        <>
                            <Upload
                                className="h-5 w-5"
                                aria-hidden="true"
                            />

                            Upload CSV
                        </>
                    )}
                </button>
            </form>
        </section>
    );
}