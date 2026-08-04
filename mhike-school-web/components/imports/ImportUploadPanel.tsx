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
    ChevronDown,
    Download,
    Eye,
    FileSpreadsheet,
    Info,
    Loader2,
    RefreshCw,
    Upload,
    X,
} from "lucide-react";

import {
    downloadImportTemplate,
    getImportTemplateMetadata,
    listImportTemplates,
    previewImportTemplate,
} from "@/lib/importApi";

import type {
    ImportFieldMetadataRead,
    ImportTemplateMetadataRead,
    ImportTemplateSummaryRead,
    ImportTemplateValue,
} from "@/types/import";

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

    /**
     * Optional compatibility override.
     *
     * When omitted, supported import types are loaded from the backend's
     * metadata-driven template discovery endpoint.
     */
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
    const seenValues =
        new Set<string>();

    const resolvedOptions:
        ImportTypeOption[] = [];

    for (const option of options) {
        const value =
            option.value
                .trim()
                .toLowerCase();

        const label =
            option.label.trim();

        if (
            !value ||
            seenValues.has(value)
        ) {
            continue;
        }

        seenValues.add(value);

        resolvedOptions.push({
            value,
            label:
                label ||
                value.replace(
                    /_/g,
                    " ",
                ),
            description:
                option.description
                    ?.trim() ||
                undefined,
        });
    }

    return resolvedOptions.sort(
        (first, second) =>
            first.label.localeCompare(
                second.label,
            ),
    );
}

function templateSummariesToOptions(
    templates:
        readonly ImportTemplateSummaryRead[],
): ImportTypeOption[] {
    return normaliseImportTypes(
        templates.map(
            (template) => ({
                value:
                    template.import_type,
                label:
                    template.display_name,
                description:
                    template.description,
            }),
        ),
    );
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
        mimeType ===
        "application/csv" ||
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

function getErrorMessage(
    error: unknown,
    fallback: string,
): string {
    if (error instanceof Error) {
        const message =
            error.message.trim();

        if (message) {
            return message;
        }
    }

    if (
        typeof error ===
        "string"
    ) {
        const message =
            error.trim();

        if (message) {
            return message;
        }
    }

    return fallback;
}

function formatTemplateValue(
    value: ImportTemplateValue,
): string {
    if (
        value === null ||
        value === ""
    ) {
        return "—";
    }

    if (
        typeof value ===
        "string"
    ) {
        return value;
    }

    if (
        typeof value ===
        "number" ||
        typeof value ===
        "boolean"
    ) {
        return String(value);
    }

    try {
        return JSON.stringify(
            value,
        );
    } catch {
        return String(value);
    }
}

function formatValidationRule(
    field:
        ImportFieldMetadataRead,
): string {
    const parts: string[] = [];

    if (
        field.accepted_values.length >
        0
    ) {
        parts.push(
            `Accepted: ${field.accepted_values
                .map(formatTemplateValue)
                .join(", ")}`,
        );
    }

    for (
        const rule
        of field.validation_rules
    ) {
        if (
            rule.name ===
            "accepted_values"
        ) {
            continue;
        }

        const label =
            rule.name
                .replace(/_/g, " ")
                .replace(
                    /\b\w/g,
                    (character) =>
                        character.toUpperCase(),
                );

        parts.push(
            `${label}: ${formatTemplateValue(
                rule.value,
            )}`,
        );
    }

    return parts.join(" · ");
}

function triggerBlobDownload(
    blob: Blob,
    filename: string,
): void {
    const objectUrl =
        URL.createObjectURL(blob);

    const anchor =
        document.createElement("a");

    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.style.display = "none";

    document.body.appendChild(
        anchor,
    );

    anchor.click();
    anchor.remove();

    window.setTimeout(
        () => {
            URL.revokeObjectURL(
                objectUrl,
            );
        },
        0,
    );
}

export default function ImportUploadPanel({
    title = "Upload CSV data",
    description =
    "Choose an import type, review its template requirements and upload a CSV file for validation.",

    acceptedFileTypes =
    DEFAULT_ACCEPTED_FILE_TYPES,

    maximumFileSizeMb =
    DEFAULT_MAXIMUM_FILE_SIZE_MB,

    importTypes,
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

    const metadataRequestIdRef =
        useRef(0);

    const previewRequestIdRef =
        useRef(0);

    const [
        selectedFile,
        setSelectedFile,
    ] = useState<File | null>(
        null,
    );

    const [
        selectedImportType,
        setSelectedImportType,
    ] = useState(
        defaultImportType
            .trim()
            .toLowerCase(),
    );

    const [
        discoveredTemplates,
        setDiscoveredTemplates,
    ] = useState<
        ImportTemplateSummaryRead[]
    >([]);

    const [
        templateMetadata,
        setTemplateMetadata,
    ] = useState<
        ImportTemplateMetadataRead | null
    >(null);

    const [
        csvPreview,
        setCsvPreview,
    ] = useState<string | null>(
        null,
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

    const [
        templateError,
        setTemplateError,
    ] = useState<string | null>(
        null,
    );

    const [
        isLoadingTemplates,
        setIsLoadingTemplates,
    ] = useState(
        importTypes === undefined,
    );

    const [
        isLoadingMetadata,
        setIsLoadingMetadata,
    ] = useState(false);

    const [
        isLoadingPreview,
        setIsLoadingPreview,
    ] = useState(false);

    const [
        isDownloadingTemplate,
        setIsDownloadingTemplate,
    ] = useState(false);

    const [
        isTemplateDetailsOpen,
        setIsTemplateDetailsOpen,
    ] = useState(true);

    const [
        isPreviewOpen,
        setIsPreviewOpen,
    ] = useState(false);

    const externalImportTypes =
        useMemo(
            () =>
                importTypes
                    ? normaliseImportTypes(
                        importTypes,
                    )
                    : null,
            [importTypes],
        );

    const discoveredImportTypes =
        useMemo(
            () =>
                templateSummariesToOptions(
                    discoveredTemplates,
                ),
            [discoveredTemplates],
        );

    const resolvedImportTypes =
        externalImportTypes ??
        discoveredImportTypes;

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

    const selectedTemplateSummary =
        useMemo(
            () =>
                discoveredTemplates.find(
                    (template) =>
                        template.import_type ===
                        selectedImportType,
                ) ?? null,
            [
                discoveredTemplates,
                selectedImportType,
            ],
        );

    const effectiveErrorMessage =
        validationError ??
        errorMessage;

    const interactionDisabled =
        disabled ||
        isUploading ||
        isLoadingTemplates;

    const canUpload =
        selectedFile !== null &&
        selectedImportType !== "" &&
        !interactionDisabled &&
        validationError === null;

    const canUseTemplateActions =
        selectedImportType !== "" &&
        !disabled &&
        !isLoadingTemplates;

    useEffect(() => {
        if (importTypes !== undefined) {
            setIsLoadingTemplates(
                false,
            );

            return;
        }

        let isActive = true;

        async function loadTemplates(): Promise<void> {
            setIsLoadingTemplates(
                true,
            );

            setTemplateError(
                null,
            );

            try {
                const response =
                    await listImportTemplates();

                if (!isActive) {
                    return;
                }

                setDiscoveredTemplates(
                    response.items,
                );
            } catch (error) {
                if (!isActive) {
                    return;
                }

                setDiscoveredTemplates(
                    [],
                );

                setTemplateError(
                    getErrorMessage(
                        error,
                        "The available import templates could not be loaded.",
                    ),
                );
            } finally {
                if (isActive) {
                    setIsLoadingTemplates(
                        false,
                    );
                }
            }
        }

        void loadTemplates();

        return () => {
            isActive = false;
        };
    }, [importTypes]);

    useEffect(() => {
        const normalisedDefault =
            defaultImportType
                .trim()
                .toLowerCase();

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

            return;
        }

        if (
            selectedImportType &&
            !resolvedImportTypes.some(
                (option) =>
                    option.value ===
                    selectedImportType,
            )
        ) {
            setSelectedImportType(
                "",
            );
        }
    }, [
        defaultImportType,
        resolvedImportTypes,
        selectedImportType,
    ]);

    useEffect(() => {
        const importType =
            selectedImportType;

        metadataRequestIdRef.current +=
            1;

        const requestId =
            metadataRequestIdRef.current;

        setTemplateMetadata(
            null,
        );

        setCsvPreview(
            null,
        );

        setIsPreviewOpen(
            false,
        );

        setTemplateError(
            null,
        );

        if (!importType) {
            setIsLoadingMetadata(
                false,
            );

            return;
        }

        async function loadMetadata(): Promise<void> {
            setIsLoadingMetadata(
                true,
            );

            try {
                const metadata =
                    await getImportTemplateMetadata(
                        importType,
                    );

                if (
                    requestId !==
                    metadataRequestIdRef.current
                ) {
                    return;
                }

                setTemplateMetadata(
                    metadata,
                );
            } catch (error) {
                if (
                    requestId !==
                    metadataRequestIdRef.current
                ) {
                    return;
                }

                setTemplateError(
                    getErrorMessage(
                        error,
                        "The template metadata could not be loaded.",
                    ),
                );
            } finally {
                if (
                    requestId ===
                    metadataRequestIdRef.current
                ) {
                    setIsLoadingMetadata(
                        false,
                    );
                }
            }
        }

        void loadMetadata();
    }, [selectedImportType]);
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
        setSelectedFile(
            (currentFile) => {
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
            },
        );
    }

    function updateImportType(
        importType: string,
    ): void {
        const normalisedImportType =
            importType
                .trim()
                .toLowerCase();

        setSelectedImportType(
            normalisedImportType,
        );

        setValidationError(
            null,
        );

        setTemplateError(
            null,
        );

        setIsTemplateDetailsOpen(
            true,
        );

        notifySelectionChange(
            selectedFile,
            normalisedImportType,
        );
    }

    function validateAndSelectFile(
        file: File | null,
    ): void {
        setValidationError(
            null,
        );

        if (!file) {
            updateSelectedFile(
                null,
            );

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

            updateSelectedFile(
                null,
            );

            if (
                fileInputRef.current
            ) {
                fileInputRef.current.value =
                    "";
            }

            return;
        }

        updateSelectedFile(
            file,
        );
    }

    function handleFileInputChange(
        event:
            ChangeEvent<HTMLInputElement>,
    ): void {
        const file =
            event.target.files?.[0] ??
            null;

        validateAndSelectFile(
            file,
        );
    }

    function handleDragEnter(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();
        event.stopPropagation();

        if (!interactionDisabled) {
            setIsDragging(
                true,
            );
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
            setIsDragging(
                false,
            );
        }
    }

    function handleDrop(
        event:
            DragEvent<HTMLDivElement>,
    ): void {
        event.preventDefault();
        event.stopPropagation();

        setIsDragging(
            false,
        );

        if (interactionDisabled) {
            return;
        }

        const files =
            event.dataTransfer.files;

        if (
            !files ||
            files.length === 0
        ) {
            validateAndSelectFile(
                null,
            );

            return;
        }

        if (files.length > 1) {
            setValidationError(
                "Please upload one CSV file at a time.",
            );

            updateSelectedFile(
                null,
            );

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
            event.key ===
            "Enter" ||
            event.key ===
            " "
        ) {
            event.preventDefault();

            openFilePicker();
        }
    }

    function clearSelectedFile(): void {
        setValidationError(
            null,
        );

        updateSelectedFile(
            null,
        );

        if (fileInputRef.current) {
            fileInputRef.current.value =
                "";
        }
    }

    async function handlePreviewTemplate(): Promise<void> {
        if (
            !selectedImportType ||
            isLoadingPreview
        ) {
            return;
        }

        previewRequestIdRef.current +=
            1;

        const requestId =
            previewRequestIdRef.current;

        setIsLoadingPreview(
            true,
        );

        setTemplateError(
            null,
        );

        try {
            const preview =
                await previewImportTemplate(
                    selectedImportType,
                    {
                        includeSampleRow:
                            true,
                    },
                );

            if (
                requestId !==
                previewRequestIdRef.current
            ) {
                return;
            }

            setCsvPreview(
                preview.csv_content,
            );

            setIsPreviewOpen(
                true,
            );
        } catch (error) {
            if (
                requestId !==
                previewRequestIdRef.current
            ) {
                return;
            }

            setTemplateError(
                getErrorMessage(
                    error,
                    "The CSV template preview could not be loaded.",
                ),
            );
        } finally {
            if (
                requestId ===
                previewRequestIdRef.current
            ) {
                setIsLoadingPreview(
                    false,
                );
            }
        }
    }

    async function handleDownloadTemplate(): Promise<void> {
        if (
            !selectedImportType ||
            isDownloadingTemplate
        ) {
            return;
        }

        setIsDownloadingTemplate(
            true,
        );

        setTemplateError(
            null,
        );

        try {
            const blob =
                await downloadImportTemplate(
                    selectedImportType,
                    {
                        includeSampleRow:
                            true,
                    },
                );

            const filename =
                `${selectedImportType}_import_template.csv`;

            triggerBlobDownload(
                blob,
                filename,
            );
        } catch (error) {
            setTemplateError(
                getErrorMessage(
                    error,
                    "The CSV template could not be downloaded.",
                ),
            );
        } finally {
            setIsDownloadingTemplate(
                false,
            );
        }
    }

    async function handleSubmit(
        event:
            FormEvent<HTMLFormElement>,
    ): Promise<void> {
        event.preventDefault();

        setValidationError(
            null,
        );

        const normalisedImportType =
            selectedImportType
                .trim()
                .toLowerCase();

        if (!normalisedImportType) {
            setValidationError(
                "Please select an import type before uploading the CSV file.",
            );

            return;
        }

        if (
            !resolvedImportTypes.some(
                (option) =>
                    option.value ===
                    normalisedImportType,
            )
        ) {
            setValidationError(
                "The selected import type is not currently supported.",
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
                file:
                    selectedFile,
                importType:
                    normalisedImportType,
            });

            clearSelectedFile();
        } catch {
            /*
             * The parent owns API error handling.
             * Keep the selected file available so the administrator can retry
             * without selecting the file again.
             */
        }
    }

    function renderFieldList(
        fields:
            readonly ImportFieldMetadataRead[],
        emptyMessage: string,
    ) {
        if (fields.length === 0) {
            return (
                <p className="text-sm text-slate-500">
                    {emptyMessage}
                </p>
            );
        }

        return (
            <div className="space-y-3">
                {fields.map(
                    (field) => {
                        const validationSummary =
                            formatValidationRule(
                                field,
                            );

                        return (
                            <article
                                key={
                                    field.name
                                }
                                className="rounded-xl border border-slate-200 bg-white p-4"
                            >
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                    <div className="min-w-0">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <h4 className="font-semibold text-slate-950">
                                                {
                                                    field.label
                                                }
                                            </h4>

                                            <code className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                                                {
                                                    field.column_name
                                                }
                                            </code>

                                            <span
                                                className={[
                                                    "rounded-full px-2 py-1 text-xs font-semibold",
                                                    field.required
                                                        ? "bg-red-100 text-red-700"
                                                        : "bg-slate-100 text-slate-600",
                                                ].join(
                                                    " ",
                                                )}
                                            >
                                                {field.required
                                                    ? "Required"
                                                    : "Optional"}
                                            </span>
                                        </div>

                                        {field.description ? (
                                            <p className="mt-2 text-sm leading-6 text-slate-600">
                                                {
                                                    field.description
                                                }
                                            </p>
                                        ) : null}
                                    </div>

                                    <div className="shrink-0 text-left sm:text-right">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                            Type
                                        </p>

                                        <p className="mt-1 text-sm font-medium text-slate-800">
                                            {
                                                field.data_type
                                            }
                                        </p>
                                    </div>
                                </div>

                                <div className="mt-3 grid gap-3 text-xs text-slate-600 sm:grid-cols-2">
                                    <div>
                                        <span className="font-semibold text-slate-700">
                                            Example:
                                        </span>{" "}
                                        <span>
                                            {formatTemplateValue(
                                                field.example,
                                            )}
                                        </span>
                                    </div>

                                    <div>
                                        <span className="font-semibold text-slate-700">
                                            Default:
                                        </span>{" "}
                                        <span>
                                            {formatTemplateValue(
                                                field.default,
                                            )}
                                        </span>
                                    </div>
                                </div>

                                {validationSummary ? (
                                    <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
                                        {
                                            validationSummary
                                        }
                                    </p>
                                ) : null}
                            </article>
                        );
                    },
                )}
            </div>
        );
    }

    return (
        <section
            className={[
                "rounded-2xl border border-slate-200 bg-white p-6 shadow-sm",
                className,
            ]
                .filter(Boolean)
                .join(" ")}
            aria-busy={
                isUploading ||
                isLoadingTemplates ||
                isLoadingMetadata
            }
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
                onSubmit={
                    handleSubmit
                }
                noValidate
            >
                <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-slate-900">
                        Import type
                    </span>

                    <div className="relative">
                        <select
                            value={
                                selectedImportType
                            }
                            disabled={
                                interactionDisabled
                            }
                            aria-label="Import type"
                            className={[
                                "min-h-11 w-full appearance-none rounded-xl border border-slate-300",
                                "bg-white px-3 py-2 pr-10 text-sm text-slate-950 shadow-sm",
                                "outline-none transition focus:border-blue-500",
                                "focus:ring-2 focus:ring-blue-200",
                                "disabled:cursor-not-allowed disabled:bg-slate-100",
                                "disabled:text-slate-500",
                            ].join(" ")}
                            onChange={(
                                event,
                            ) => {
                                updateImportType(
                                    event.target
                                        .value,
                                );
                            }}
                        >
                            <option value="">
                                {isLoadingTemplates
                                    ? "Loading import types…"
                                    : "Select import type"}
                            </option>

                            {resolvedImportTypes.map(
                                (
                                    option,
                                ) => (
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

                        <ChevronDown
                            className="pointer-events-none absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500"
                            aria-hidden="true"
                        />
                    </div>

                    {selectedImportTypeOption
                        ?.description ? (
                        <span className="mt-2 block text-xs leading-5 text-slate-500">
                            {
                                selectedImportTypeOption.description
                            }
                        </span>
                    ) : null}
                </label>

                {templateError ? (
                    <div
                        role="alert"
                        className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900"
                    >
                        <AlertCircle
                            className="mt-0.5 h-5 w-5 shrink-0"
                            aria-hidden="true"
                        />

                        <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium leading-6">
                                {
                                    templateError
                                }
                            </p>
                        </div>

                        {importTypes ===
                            undefined ? (
                            <button
                                type="button"
                                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-amber-800 transition hover:bg-amber-100"
                                aria-label="Reload import templates"
                                onClick={() => {
                                    window.location.reload();
                                }}
                            >
                                <RefreshCw
                                    className="h-4 w-4"
                                    aria-hidden="true"
                                />
                            </button>
                        ) : null}
                    </div>
                ) : null}

                {selectedImportType ? (
                    <div className="rounded-2xl border border-blue-200 bg-blue-50/60">
                        <button
                            type="button"
                            className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                            aria-expanded={
                                isTemplateDetailsOpen
                            }
                            onClick={() => {
                                setIsTemplateDetailsOpen(
                                    (
                                        current,
                                    ) =>
                                        !current,
                                );
                            }}
                        >
                            <span className="flex min-w-0 items-start gap-3">
                                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
                                    <Info
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                </span>

                                <span className="min-w-0">
                                    <span className="block text-sm font-semibold text-slate-950">
                                        CSV template
                                        requirements
                                    </span>

                                    <span className="mt-1 block text-xs leading-5 text-slate-600">
                                        Review the
                                        expected
                                        columns before
                                        uploading.
                                    </span>
                                </span>
                            </span>

                            <ChevronDown
                                className={[
                                    "h-5 w-5 shrink-0 text-slate-500 transition-transform",
                                    isTemplateDetailsOpen
                                        ? "rotate-180"
                                        : "",
                                ].join(
                                    " ",
                                )}
                                aria-hidden="true"
                            />
                        </button>
                        {isTemplateDetailsOpen ? (
                            <div className="border-t border-blue-200 px-5 py-5">
                                {isLoadingMetadata ? (
                                    <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-white p-4 text-sm text-slate-700">
                                        <Loader2
                                            className="h-5 w-5 animate-spin text-blue-700"
                                            aria-hidden="true"
                                        />

                                        Loading template
                                        requirements…
                                    </div>
                                ) : templateMetadata ? (
                                    <div className="space-y-5">
                                        <div className="grid gap-3 sm:grid-cols-3">
                                            <div className="rounded-xl border border-blue-200 bg-white p-4">
                                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                    Required
                                                    fields
                                                </p>

                                                <p className="mt-2 text-2xl font-bold text-slate-950">
                                                    {
                                                        templateMetadata
                                                            .required_fields
                                                            .length
                                                    }
                                                </p>
                                            </div>

                                            <div className="rounded-xl border border-blue-200 bg-white p-4">
                                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                    Optional
                                                    fields
                                                </p>

                                                <p className="mt-2 text-2xl font-bold text-slate-950">
                                                    {
                                                        templateMetadata
                                                            .optional_fields
                                                            .length
                                                    }
                                                </p>
                                            </div>

                                            <div className="rounded-xl border border-blue-200 bg-white p-4">
                                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                                    Total
                                                    columns
                                                </p>

                                                <p className="mt-2 text-2xl font-bold text-slate-950">
                                                    {
                                                        templateMetadata
                                                            .fields
                                                            .length
                                                    }
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex flex-col gap-3 sm:flex-row">
                                            <button
                                                type="button"
                                                disabled={
                                                    !canUseTemplateActions ||
                                                    isLoadingPreview
                                                }
                                                className={[
                                                    "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl",
                                                    "border border-blue-300 bg-white px-4 py-2 text-sm font-semibold",
                                                    "text-blue-800 transition hover:bg-blue-100",
                                                    "focus:outline-none focus:ring-4 focus:ring-blue-100",
                                                    "disabled:cursor-not-allowed disabled:opacity-50",
                                                ].join(
                                                    " ",
                                                )}
                                                onClick={() => {
                                                    void handlePreviewTemplate();
                                                }}
                                            >
                                                {isLoadingPreview ? (
                                                    <Loader2
                                                        className="h-4 w-4 animate-spin"
                                                        aria-hidden="true"
                                                    />
                                                ) : (
                                                    <Eye
                                                        className="h-4 w-4"
                                                        aria-hidden="true"
                                                    />
                                                )}

                                                Preview
                                                template
                                            </button>

                                            <button
                                                type="button"
                                                disabled={
                                                    !canUseTemplateActions ||
                                                    isDownloadingTemplate
                                                }
                                                className={[
                                                    "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl",
                                                    "bg-blue-700 px-4 py-2 text-sm font-semibold text-white",
                                                    "transition hover:bg-blue-800",
                                                    "focus:outline-none focus:ring-4 focus:ring-blue-200",
                                                    "disabled:cursor-not-allowed disabled:bg-blue-300",
                                                ].join(
                                                    " ",
                                                )}
                                                onClick={() => {
                                                    void handleDownloadTemplate();
                                                }}
                                            >
                                                {isDownloadingTemplate ? (
                                                    <Loader2
                                                        className="h-4 w-4 animate-spin"
                                                        aria-hidden="true"
                                                    />
                                                ) : (
                                                    <Download
                                                        className="h-4 w-4"
                                                        aria-hidden="true"
                                                    />
                                                )}

                                                Download CSV
                                                template
                                            </button>
                                        </div>

                                        {selectedTemplateSummary ? (
                                            <p className="text-xs leading-5 text-slate-500">
                                                {
                                                    selectedTemplateSummary.description
                                                }
                                            </p>
                                        ) : null}

                                        <div>
                                            <h3 className="text-sm font-bold text-slate-950">
                                                Required
                                                fields
                                            </h3>

                                            <div className="mt-3">
                                                {renderFieldList(
                                                    templateMetadata.required_fields,
                                                    "This import type has no required fields.",
                                                )}
                                            </div>
                                        </div>

                                        <div>
                                            <h3 className="text-sm font-bold text-slate-950">
                                                Optional
                                                fields
                                            </h3>

                                            <div className="mt-3">
                                                {renderFieldList(
                                                    templateMetadata.optional_fields,
                                                    "This import type has no optional fields.",
                                                )}
                                            </div>
                                        </div>

                                        <div>
                                            <h3 className="text-sm font-bold text-slate-950">
                                                CSV column
                                                order
                                            </h3>

                                            <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white p-4">
                                                <div className="flex min-w-max flex-wrap gap-2">
                                                    {templateMetadata.csv_headers.map(
                                                        (
                                                            header,
                                                            index,
                                                        ) => (
                                                            <span
                                                                key={
                                                                    header
                                                                }
                                                                className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700"
                                                            >
                                                                <span className="text-slate-400">
                                                                    {index +
                                                                        1}
                                                                    .
                                                                </span>

                                                                {
                                                                    header
                                                                }
                                                            </span>
                                                        ),
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        <div>
                                            <h3 className="text-sm font-bold text-slate-950">
                                                Sample row
                                            </h3>

                                            <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white">
                                                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                                                    <thead className="bg-slate-50">
                                                        <tr>
                                                            {templateMetadata.csv_headers.map(
                                                                (
                                                                    header,
                                                                ) => (
                                                                    <th
                                                                        key={
                                                                            header
                                                                        }
                                                                        scope="col"
                                                                        className="whitespace-nowrap px-3 py-3 font-semibold text-slate-700"
                                                                    >
                                                                        {
                                                                            header
                                                                        }
                                                                    </th>
                                                                ),
                                                            )}
                                                        </tr>
                                                    </thead>

                                                    <tbody>
                                                        <tr className="divide-x divide-slate-200">
                                                            {templateMetadata.csv_headers.map(
                                                                (
                                                                    header,
                                                                ) => (
                                                                    <td
                                                                        key={
                                                                            header
                                                                        }
                                                                        className="whitespace-nowrap px-3 py-3 text-slate-600"
                                                                    >
                                                                        {formatTemplateValue(
                                                                            templateMetadata
                                                                                .sample_row[
                                                                            header
                                                                            ] ??
                                                                            null,
                                                                        )}
                                                                    </td>
                                                                ),
                                                            )}
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">
                                        Template
                                        metadata is not
                                        currently
                                        available for
                                        this import
                                        type.
                                    </div>
                                )}
                            </div>
                        ) : null}
                    </div>
                ) : null}

                {isPreviewOpen &&
                    csvPreview !== null ? (
                    <div className="rounded-2xl border border-slate-200 bg-slate-950">
                        <div className="flex items-center justify-between gap-4 border-b border-slate-700 px-4 py-3">
                            <div>
                                <h3 className="text-sm font-semibold text-white">
                                    CSV template
                                    preview
                                </h3>

                                <p className="mt-1 text-xs text-slate-400">
                                    Includes headers
                                    and a sample row.
                                </p>
                            </div>

                            <button
                                type="button"
                                aria-label="Close CSV template preview"
                                className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-300 transition hover:bg-slate-800 hover:text-white"
                                onClick={() => {
                                    setIsPreviewOpen(
                                        false,
                                    );
                                }}
                            >
                                <X
                                    className="h-5 w-5"
                                    aria-hidden="true"
                                />
                            </button>
                        </div>

                        <pre className="max-h-80 overflow-auto whitespace-pre p-4 text-xs leading-6 text-emerald-300">
                            {csvPreview}
                        </pre>
                    </div>
                ) : null}

                <input
                    ref={
                        fileInputRef
                    }
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
                    onClick={
                        openFilePicker
                    }
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
                    onDrop={
                        handleDrop
                    }
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
                        or click to browse your
                        computer
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
                                    {
                                        selectedFile.name
                                    }
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

                        <p className="text-sm font-medium leading-6">
                            {
                                successMessage
                            }
                        </p>
                    </div>
                ) : null}

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-xs leading-5 text-slate-500">
                        The file will be staged
                        and validated before any
                        school records are created
                        or updated.
                    </p>

                    <button
                        type="submit"
                        disabled={
                            !canUpload
                        }
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
