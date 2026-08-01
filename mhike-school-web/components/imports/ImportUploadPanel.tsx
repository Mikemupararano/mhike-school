"use client";

import {
    useEffect,
    useMemo,
    useRef,
    useState,
    type ChangeEvent,
    type DragEvent,
    type FormEvent,
    type KeyboardEvent,
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

const DEFAULT_ACCEPTED_FILE_TYPES =
    ".csv,text/csv,application/csv,application/vnd.ms-excel";

const DEFAULT_MAXIMUM_FILE_SIZE_MB = 10;

const DEFAULT_IMPORT_TYPES: readonly ImportTypeOption[] = [
    {
        value: "students",
        label: "Students",
        description:
            "Import student identity, year-group and account information.",
    },
    {
        value: "parents",
        label: "Parents",
        description:
            "Import parent or guardian identity and account information.",
    },
    {
        value: "teachers",
        label: "Teachers",
        description:
            "Import teaching staff identity, role and account information.",
    },
    {
        value: "staff",
        label: "Staff",
        description:
            "Import non-teaching and administrative staff information.",
    },
    {
        value: "classes",
        label: "Classes",
        description:
            "Import class groups, forms and year-group structures.",
    },
    {
        value: "subjects",
        label: "Subjects",
        description:
            "Import subjects and curriculum-area information.",
    },
    {
        value: "courses",
        label: "Courses",
        description:
            "Import courses and academic programme information.",
    },
    {
        value: "enrollments",
        label: "Enrolments",
        description:
            "Import student class or course enrolments.",
    },
    {
        value: "teaching_assignments",
        label: "Teaching assignments",
        description:
            "Import teacher, subject and class assignment information.",
    },
    {
        value: "timetables",
        label: "Timetables",
        description:
            "Import timetable periods, lessons and scheduling information.",
    },
    {
        value: "attendance",
        label: "Attendance",
        description:
            "Import student attendance and absence information.",
    },
    {
        value: "marks",
        label: "Marks",
        description:
            "Import assessment marks, grades and result information.",
    },
];

function formatFileSize(
    sizeInBytes: number,
): string {
    if (
        !Number.isFinite(sizeInBytes) ||
        sizeInBytes < 0
    ) {
        return "Unknown size";
    }

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

function formatDateTime(
    value: number,
): string {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Unknown";
    }

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            dateStyle: "medium",
            timeStyle: "short",
        },
    ).format(date);
}

function normaliseImportTypes(
    options: readonly ImportTypeOption[],
): ImportTypeOption[] {
    const seenValues = new Set<string>();
    const resolvedOptions: ImportTypeOption[] = [];

    for (const option of options) {
        const value = option.value.trim();
        const label = option.label.trim();

        if (
            !value ||
            seenValues.has(value)
        ) {
            continue;
        }

        seenValues.add(value);

        resolvedOptions.push({
            value,
            label: label || value,
            description:
                option.description
                    ?.trim() ||
                undefined,
        });
    }

    return resolvedOptions;
}

function isCsvFile(
    file: File,
): boolean {
    const fileName =
        file.name
            .trim()
            .toLowerCase();

    const mimeType =
        file.type
            .trim()
            .toLowerCase();

    return (
        fileName.endsWith(".csv") ||
        mimeType === "text/csv" ||
        mimeType === "application/csv" ||
        mimeType ===
        "application/vnd.ms-excel" ||
        mimeType === ""
    );
}

function getFileValidationError(
    file: File,
    maximumFileSizeBytes: number,
    maximumFileSizeMb: number,
): string | null {
    if (!isCsvFile(file)) {
        return "Please select a valid CSV file.";
    }

    if (file.size === 0) {
        return "The selected CSV file is empty.";
    }

    if (
        file.size >
        maximumFileSizeBytes
    ) {
        return (
            "The selected file is too large. " +
            `The maximum permitted size is ${maximumFileSizeMb} MB.`
        );
    }

    return null;
}

function filesMatch(
    first: File | null,
    second: File | null,
): boolean {
    if (
        first === null ||
        second === null
    ) {
        return first === second;
    }

    return (
        first.name === second.name &&
        first.size === second.size &&
        first.lastModified ===
        second.lastModified
    );
}

export default function ImportUploadPanel({
    title = "Upload CSV data",
    description =
    "Choose an import type and upload a CSV file for validation.",

    acceptedFileTypes =
    DEFAULT_ACCEPTED_FILE_TYPES,

    maximumFileSizeMb =
    DEFAULT_MAXIMUM_FILE_SIZE_MB,

    importTypes =
    DEFAULT_IMPORT_TYPES,

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
    ] = useState(
        defaultImportType.trim(),
    );

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

    const resolvedImportTypes =
        useMemo(
            () =>
                normaliseImportTypes(
                    importTypes,
                ),
            [importTypes],
        );

    const maximumFileSizeBytes =
        useMemo(
            () =>
                Math.max(
                    maximumFileSizeMb,
                    0,
                ) *
                1024 *
                1024,
            [maximumFileSizeMb],
        );

    const selectedImportTypeOption =
        useMemo(
            () =>
                resolvedImportTypes.find(
                    (option) =>
                        option.value ===
                        selectedImportType,
                ) ?? null,
            [
                resolvedImportTypes,
                selectedImportType,
            ],
        );

    const effectiveErrorMessage =
        validationError ??
        errorMessage;

    const interactionDisabled =
        disabled ||
        isUploading;

    const canUpload =
        selectedFile !== null &&
        selectedImportType.trim() !== "" &&
        !interactionDisabled &&
        validationError === null;

    useEffect(() => {
        const normalisedDefault =
            defaultImportType.trim();

        if (
            normalisedDefault &&
            resolvedImportTypes.some(
                (option) =>
                    option.value ===
                    normalisedDefault,
            )
        ) {
            setSelectedImportType(
                normalisedDefault,
            );
        }
    }, [
        defaultImportType,
        resolvedImportTypes,
    ]);

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
        setSelectedFile((currentFile) => {
            if (
                filesMatch(
                    currentFile,
                    file,
                )
            ) {
                return currentFile;
            }

            notifySelectionChange(
                file,
                selectedImportType,
            );

            return file;
        });
    }

    function updateImportType(
        importType: string,
    ): void {
        const normalisedImportType =
            importType.trim();

        setSelectedImportType(
            normalisedImportType,
        );

        setValidationError(null);

        notifySelectionChange(
            selectedFile,
            normalisedImportType,
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

        const fileValidationError =
            getFileValidationError(
                file,
                maximumFileSizeBytes,
                maximumFileSizeMb,
            );

        if (fileValidationError) {
            setValidationError(
                fileValidationError,
            );

            updateSelectedFile(null);

            if (fileInputRef.current) {
                fileInputRef.current.value =
                    "";
            }

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
        event.stopPropagation();

        if (!interactionDisabled) {
            setIsDragging(true);
        }
    }

    function handleDragOver(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();
        event.stopPropagation();

        if (
            !interactionDisabled &&
            event.dataTransfer
        ) {
            event.dataTransfer.dropEffect =
                "copy";
        }
    }

    function handleDragLeave(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();
        event.stopPropagation();

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
        event.stopPropagation();

        setIsDragging(false);

        if (interactionDisabled) {
            return;
        }

        const files =
            event.dataTransfer.files;

        if (
            !files ||
            files.length === 0
        ) {
            validateAndSelectFile(null);
            return;
        }

        if (files.length > 1) {
            setValidationError(
                "Please upload one CSV file at a time.",
            );

            updateSelectedFile(null);
            return;
        }

        validateAndSelectFile(
            files[0] ?? null,
        );
    }

    function openFilePicker(): void {
        if (interactionDisabled) {
            return;
        }

        fileInputRef.current?.click();
    }

    function handleDropZoneKeyDown(
        event:
            KeyboardEvent<HTMLDivElement>,
    ): void {
        if (interactionDisabled) {
            return;
        }

        if (
            event.key === "Enter" ||
            event.key === " "
        ) {
            event.preventDefault();
            openFilePicker();
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

        const normalisedImportType =
            selectedImportType.trim();

        if (!normalisedImportType) {
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

        const fileValidationError =
            getFileValidationError(
                selectedFile,
                maximumFileSizeBytes,
                maximumFileSizeMb,
            );

        if (fileValidationError) {
            setValidationError(
                fileValidationError,
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
                    normalisedImportType,
            });

            clearSelectedFile();
        } catch {
            /*
             * The parent owns API error handling.
             * The selected file remains available so
             * the administrator can retry the upload.
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
            aria-busy={isUploading}
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
                noValidate
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
                            interactionDisabled
                        }
                        aria-label="Import type"
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
                                event.target.value,
                            );
                        }}
                    >
                        <option value="">
                            Select import type
                        </option>

                        {resolvedImportTypes.map(
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
                        interactionDisabled
                    }
                    aria-label="Select CSV file"
                    onChange={
                        handleFileInputChange
                    }
                />
                <div
                    role="button"
                    tabIndex={
                        interactionDisabled
                            ? -1
                            : 0
                    }
                    aria-disabled={
                        interactionDisabled
                    }
                    aria-label="Choose CSV file"
                    className={[
                        "flex min-h-56 flex-col items-center justify-center rounded-2xl",
                        "border-2 border-dashed px-6 py-8 text-center transition",
                        "outline-none focus:ring-4 focus:ring-blue-100",
                        isDragging
                            ? "border-blue-500 bg-blue-50 shadow-inner"
                            : "border-slate-300 bg-slate-50",
                        interactionDisabled
                            ? "cursor-not-allowed opacity-60"
                            : "cursor-pointer hover:border-blue-400 hover:bg-blue-50/60",
                    ].join(" ")}
                    onClick={openFilePicker}
                    onKeyDown={
                        handleDropZoneKeyDown
                    }
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
                    <span
                        className={[
                            "flex h-14 w-14 items-center justify-center rounded-2xl",
                            isDragging
                                ? "bg-blue-600 text-white"
                                : "bg-blue-100 text-blue-700",
                        ].join(" ")}
                    >
                        <Upload
                            className="h-7 w-7"
                            aria-hidden="true"
                        />
                    </span>

                    <p className="mt-4 text-base font-semibold text-slate-950">
                        {isDragging
                            ? "Drop the CSV file now"
                            : "Drop your CSV file here"}
                    </p>

                    <p className="mt-1 text-sm text-slate-600">
                        or click to browse your computer
                    </p>

                    <p className="mt-3 text-xs font-medium text-slate-500">
                        One CSV file, up to{" "}
                        {maximumFileSizeMb} MB
                    </p>
                </div>

                {selectedFile ? (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex items-start gap-3">
                            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                                <FileSpreadsheet
                                    className="h-6 w-6"
                                    aria-hidden="true"
                                />
                            </span>

                            <div className="min-w-0 flex-1">
                                <p className="truncate text-sm font-semibold text-slate-950">
                                    {selectedFile.name}
                                </p>

                                <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                                    <span>
                                        {formatFileSize(
                                            selectedFile.size,
                                        )}
                                    </span>

                                    <span>
                                        Modified{" "}
                                        {formatDateTime(
                                            selectedFile.lastModified,
                                        )}
                                    </span>

                                    {selectedImportTypeOption ? (
                                        <span>
                                            Importing as{" "}
                                            {
                                                selectedImportTypeOption.label
                                            }
                                        </span>
                                    ) : null}
                                </div>
                            </div>

                            <button
                                type="button"
                                disabled={
                                    interactionDisabled
                                }
                                aria-label="Remove selected file"
                                className={[
                                    "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                                    "text-slate-500 transition hover:bg-slate-200",
                                    "hover:text-slate-900 disabled:cursor-not-allowed",
                                    "disabled:opacity-50",
                                ].join(" ")}
                                onClick={(event) => {
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

                        <p className="text-sm font-medium leading-6">
                            {effectiveErrorMessage}
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

                        <p className="text-sm font-medium leading-6">
                            {successMessage}
                        </p>
                    </div>
                ) : null}
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-xs leading-5 text-slate-500">
                        The file will be staged and validated before any
                        school records are created or updated.
                    </p>

                    <button
                        type="submit"
                        disabled={!canUpload}
                        className={[
                            "inline-flex min-h-11 w-full items-center justify-center gap-2",
                            "rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold",
                            "text-white transition hover:bg-slate-800",
                            "focus:outline-none focus:ring-4 focus:ring-slate-300",
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
                </div>
            </form>
        </section>
    );
}
