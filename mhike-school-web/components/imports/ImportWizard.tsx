"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useState,
    type ChangeEvent,
} from "react";
import { useRouter } from "next/navigation";
import {
    AlertCircle,
    ArrowLeft,
    ArrowRight,
    Check,
    CheckCircle2,
    Download,
    FileSpreadsheet,
    Loader2,
    RotateCcw,
    Upload,
} from "lucide-react";

import {
    createImportBatch,
    downloadImportTemplate,
    getImportTemplateMetadata,
    listImportTemplates,
    MAX_CSV_FILE_SIZE_BYTES,
    updateImportBatch,
    uploadImportCsv,
} from "@/lib/importApi";
import type {
    ImportBatchRead,
    ImportTemplateListRead,
    ImportTemplateMetadataRead,
    ImportTemplateSummaryRead,
    ImportTemplateValue,
} from "@/types/import";

const WIZARD_STEPS = [
    {
        id: "type",
        label: "Import type",
        description: "Choose the data you want to import.",
    },
    {
        id: "template",
        label: "Template",
        description: "Review the required CSV structure.",
    },
    {
        id: "upload",
        label: "Upload",
        description: "Select the CSV file to import.",
    },
    {
        id: "mapping",
        label: "Column mapping",
        description: "Match CSV columns to import fields.",
    },
    {
        id: "options",
        label: "Options",
        description: "Configure how records should be handled.",
    },
    {
        id: "review",
        label: "Review",
        description: "Confirm the import configuration.",
    },
] as const;

type ColumnMapping = Record<string, string>;

type WizardImportOptions = {
    skip_duplicate_rows: boolean;
    update_existing_records: boolean;
    send_account_notifications: boolean;
};

export type ImportWizardProps = {
    defaultImportType?: string;
    disabled?: boolean;
    className?: string;

    /**
     * Called after the CSV has been uploaded and validation has been queued.
     */
    onCompleted?: (
        batch: ImportBatchRead,
    ) => void | Promise<void>;

    /**
     * Called whenever a new batch is created by the wizard.
     */
    onBatchCreated?: (
        batch: ImportBatchRead,
    ) => void | Promise<void>;

    /**
     * By default the wizard opens the existing batch-details page after
     * upload. Set this to false when the parent component handles navigation.
     */
    navigateToBatchOnComplete?: boolean;
};

const DEFAULT_IMPORT_OPTIONS: WizardImportOptions = {
    skip_duplicate_rows: true,
    update_existing_records: false,
    send_account_notifications: false,
};

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
            error as Record<string, unknown>;

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
    }

    return "The import wizard could not complete the requested action.";
}

function normaliseHeader(
    value: string,
): string {
    return value
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
}

function parseCsvHeaderLine(
    line: string,
): string[] {
    const values: string[] = [];

    let currentValue = "";
    let insideQuotes = false;

    for (
        let index = 0;
        index < line.length;
        index += 1
    ) {
        const character =
            line[index];

        if (character === "\"") {
            const nextCharacter =
                line[index + 1];

            if (
                insideQuotes &&
                nextCharacter === "\""
            ) {
                currentValue += "\"";
                index += 1;
                continue;
            }

            insideQuotes = !insideQuotes;
            continue;
        }

        if (
            character === "," &&
            !insideQuotes
        ) {
            values.push(
                currentValue.trim(),
            );

            currentValue = "";
            continue;
        }

        currentValue += character;
    }

    values.push(
        currentValue.trim(),
    );

    return values.map(
        (value) =>
            value.replace(
                /^\uFEFF/,
                "",
            ),
    );
}

async function readCsvHeaders(
    file: File,
): Promise<string[]> {
    const text =
        await file.text();

    const firstNonEmptyLine =
        text
            .split(/\r?\n/)
            .find(
                (line) =>
                    line.trim().length >
                    0,
            );

    if (!firstNonEmptyLine) {
        throw new Error(
            "The selected CSV file does not contain a header row.",
        );
    }

    const headers =
        parseCsvHeaderLine(
            firstNonEmptyLine,
        );

    if (
        headers.length === 0 ||
        headers.every(
            (header) =>
                header.trim().length ===
                0,
        )
    ) {
        throw new Error(
            "The selected CSV file does not contain valid column headers.",
        );
    }

    const normalisedHeaders =
        headers.map(
            normaliseHeader,
        );

    const duplicates =
        normalisedHeaders.filter(
            (header, index) =>
                header &&
                normalisedHeaders.indexOf(
                    header,
                ) !== index,
        );

    if (duplicates.length > 0) {
        throw new Error(
            "The selected CSV contains duplicate column headers after normalisation.",
        );
    }

    return headers;
}

function validateSelectedFile(
    file: File,
): string | null {
    const fileName =
        file.name
            .trim()
            .toLowerCase();

    const mimeType =
        file.type
            .trim()
            .toLowerCase();

    const isCsv =
        fileName.endsWith(".csv") ||
        mimeType === "text/csv" ||
        mimeType === "application/csv" ||
        mimeType ===
        "application/vnd.ms-excel" ||
        mimeType === "";

    if (!isCsv) {
        return "Please select a valid CSV file.";
    }

    if (file.size === 0) {
        return "The selected CSV file is empty.";
    }

    if (
        file.size >
        MAX_CSV_FILE_SIZE_BYTES
    ) {
        return "The selected CSV file exceeds the 10 MB upload limit.";
    }

    return null;
}

function buildAutomaticMapping(
    headers: string[],
    metadata: ImportTemplateMetadataRead,
): ColumnMapping {
    const mapping: ColumnMapping = {};

    for (const header of headers) {
        const normalised =
            normaliseHeader(
                header,
            );

        const matchingField =
            metadata.fields.find(
                (field) =>
                    normaliseHeader(
                        field.column_name,
                    ) === normalised ||
                    normaliseHeader(
                        field.name,
                    ) === normalised,
            );

        mapping[header] =
            matchingField?.column_name ??
            "";
    }

    return mapping;
}

function formatFileSize(
    sizeInBytes: number,
): string {
    if (sizeInBytes < 1024) {
        return `${sizeInBytes} B`;
    }

    const kilobytes =
        sizeInBytes / 1024;

    if (kilobytes < 1024) {
        return `${kilobytes.toFixed(1)} KB`;
    }

    return `${(
        kilobytes / 1024
    ).toFixed(1)} MB`;
}

function templateValueRecord(
    options: WizardImportOptions,
): Record<
    string,
    ImportTemplateValue
> {
    return {
        skip_duplicate_rows:
            options.skip_duplicate_rows,
        update_existing_records:
            options.update_existing_records,
        send_account_notifications:
            options.send_account_notifications,
    };
}

export default function ImportWizard({
    defaultImportType = "students",
    disabled = false,
    className = "",
    onCompleted,
    onBatchCreated,
    navigateToBatchOnComplete = true,
}: ImportWizardProps) {
    const router =
        useRouter();

    const [
        currentStepIndex,
        setCurrentStepIndex,
    ] = useState(0);

    const [
        templateList,
        setTemplateList,
    ] =
        useState<ImportTemplateListRead | null>(
            null,
        );

    const [
        selectedImportType,
        setSelectedImportType,
    ] = useState(
        defaultImportType.trim(),
    );

    const [
        templateMetadata,
        setTemplateMetadata,
    ] =
        useState<ImportTemplateMetadataRead | null>(
            null,
        );

    const [
        selectedFile,
        setSelectedFile,
    ] = useState<File | null>(
        null,
    );

    const [
        uploadedHeaders,
        setUploadedHeaders,
    ] = useState<string[]>(
        [],
    );

    const [
        columnMapping,
        setColumnMapping,
    ] = useState<ColumnMapping>(
        {},
    );

    const [
        importOptions,
        setImportOptions,
    ] =
        useState<WizardImportOptions>(
            DEFAULT_IMPORT_OPTIONS,
        );

    const [
        batch,
        setBatch,
    ] =
        useState<ImportBatchRead | null>(
            null,
        );

    const [
        isLoadingTemplates,
        setIsLoadingTemplates,
    ] = useState(true);

    const [
        isLoadingMetadata,
        setIsLoadingMetadata,
    ] = useState(false);

    const [
        isWorking,
        setIsWorking,
    ] = useState(false);

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

    const currentStep =
        WIZARD_STEPS[
        currentStepIndex
        ];

    const templates =
        useMemo(
            () =>
                templateList?.items ??
                [],
            [templateList],
        );

    const selectedTemplateSummary =
        useMemo(
            () =>
                templates.find(
                    (template) =>
                        template.import_type ===
                        selectedImportType,
                ) ?? null,
            [
                templates,
                selectedImportType,
            ],
        );

    const mappedTargetColumns =
        useMemo(
            () =>
                Object.values(
                    columnMapping,
                ).filter(Boolean),
            [columnMapping],
        );

    const duplicateTargetColumns =
        useMemo(() => {
            const seen =
                new Set<string>();

            const duplicates =
                new Set<string>();

            for (
                const target
                of mappedTargetColumns
            ) {
                if (seen.has(target)) {
                    duplicates.add(
                        target,
                    );
                }

                seen.add(target);
            }

            return duplicates;
        }, [
            mappedTargetColumns,
        ]);

    const missingRequiredFields =
        useMemo(() => {
            if (!templateMetadata) {
                return [];
            }

            const mapped =
                new Set(
                    mappedTargetColumns,
                );

            return templateMetadata
                .required_fields
                .filter(
                    (field) =>
                        !mapped.has(
                            field.column_name,
                        ),
                );
        }, [
            mappedTargetColumns,
            templateMetadata,
        ]);

    const mappingIsValid =
        uploadedHeaders.length > 0 &&
        duplicateTargetColumns.size ===
        0 &&
        missingRequiredFields.length ===
        0;

    const loadTemplates =
        useCallback(
            async (): Promise<void> => {
                setIsLoadingTemplates(
                    true,
                );
                setErrorMessage(null);

                try {
                    const response =
                        await listImportTemplates();

                    setTemplateList(
                        response,
                    );

                    const currentTypeExists =
                        response.items.some(
                            (item) =>
                                item.import_type ===
                                selectedImportType,
                        );

                    if (
                        !currentTypeExists &&
                        response.items.length >
                        0
                    ) {
                        setSelectedImportType(
                            response.items[0]
                                .import_type,
                        );
                    }
                } catch (error) {
                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                } finally {
                    setIsLoadingTemplates(
                        false,
                    );
                }
            },
            [selectedImportType],
        );

    useEffect(() => {
        void loadTemplates();
    }, [loadTemplates]);

    useEffect(() => {
        if (!selectedImportType) {
            setTemplateMetadata(
                null,
            );
            return;
        }

        let cancelled = false;

        const loadMetadata =
            async (): Promise<void> => {
                setIsLoadingMetadata(
                    true,
                );
                setErrorMessage(null);

                try {
                    const response =
                        await getImportTemplateMetadata(
                            selectedImportType,
                        );

                    if (!cancelled) {
                        setTemplateMetadata(
                            response,
                        );
                    }
                } catch (error) {
                    if (!cancelled) {
                        setTemplateMetadata(
                            null,
                        );

                        setErrorMessage(
                            getErrorMessage(
                                error,
                            ),
                        );
                    }
                } finally {
                    if (!cancelled) {
                        setIsLoadingMetadata(
                            false,
                        );
                    }
                }
            };

        void loadMetadata();

        return () => {
            cancelled = true;
        };
    }, [selectedImportType]);

    const resetWizard =
        useCallback((): void => {
            setCurrentStepIndex(0);
            setSelectedImportType(
                defaultImportType.trim(),
            );
            setSelectedFile(null);
            setUploadedHeaders([]);
            setColumnMapping({});
            setImportOptions(
                DEFAULT_IMPORT_OPTIONS,
            );
            setBatch(null);
            setErrorMessage(null);
            setSuccessMessage(null);
        }, [defaultImportType]);

    const handleImportTypeChange =
        useCallback(
            (
                importType: string,
            ): void => {
                setSelectedImportType(
                    importType,
                );
                setSelectedFile(null);
                setUploadedHeaders([]);
                setColumnMapping({});
                setBatch(null);
                setErrorMessage(null);
                setSuccessMessage(null);
            },
            [],
        );

    const handleFileChange =
        useCallback(
            async (
                event: ChangeEvent<HTMLInputElement>,
            ): Promise<void> => {
                const file =
                    event.target.files?.[0] ??
                    null;

                setErrorMessage(null);
                setSuccessMessage(null);
                setBatch(null);

                if (!file) {
                    setSelectedFile(null);
                    setUploadedHeaders([]);
                    setColumnMapping({});
                    return;
                }

                const validationError =
                    validateSelectedFile(
                        file,
                    );

                if (validationError) {
                    event.target.value = "";
                    setSelectedFile(null);
                    setUploadedHeaders([]);
                    setColumnMapping({});
                    setErrorMessage(
                        validationError,
                    );
                    return;
                }

                try {
                    const headers =
                        await readCsvHeaders(
                            file,
                        );

                    setSelectedFile(
                        file,
                    );
                    setUploadedHeaders(
                        headers,
                    );

                    if (templateMetadata) {
                        setColumnMapping(
                            buildAutomaticMapping(
                                headers,
                                templateMetadata,
                            ),
                        );
                    }
                } catch (error) {
                    event.target.value = "";
                    setSelectedFile(null);
                    setUploadedHeaders([]);
                    setColumnMapping({});
                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                }
            },
            [templateMetadata],
        );

    const ensureBatchCreated =
        useCallback(
            async (): Promise<ImportBatchRead> => {
                if (batch) {
                    return batch;
                }

                if (!selectedFile) {
                    throw new Error(
                        "Select a CSV file before continuing.",
                    );
                }

                if (!selectedImportType) {
                    throw new Error(
                        "Select an import type before continuing.",
                    );
                }

                const createdBatch =
                    await createImportBatch({
                        import_type:
                            selectedImportType,
                        original_filename:
                            selectedFile.name,
                        file_format:
                            "csv",
                        mime_type:
                            selectedFile.type ||
                            "text/csv",
                        file_size_bytes:
                            selectedFile.size,
                    });

                setBatch(
                    createdBatch,
                );

                await onBatchCreated?.(
                    createdBatch,
                );

                return createdBatch;
            },
            [
                batch,
                onBatchCreated,
                selectedFile,
                selectedImportType,
            ],
        );

    const persistMapping =
        useCallback(
            async (
                targetBatch:
                    ImportBatchRead,
            ): Promise<ImportBatchRead> => {
                const updated =
                    await updateImportBatch(
                        targetBatch.id,
                        {
                            column_mapping: {
                                uploaded_headers:
                                    uploadedHeaders,
                                normalised_headers:
                                    uploadedHeaders.map(
                                        normaliseHeader,
                                    ),
                                mapping:
                                    columnMapping,
                                mapping_completed:
                                    mappingIsValid,
                            },
                        },
                    );

                setBatch(
                    updated,
                );

                return updated;
            },
            [
                columnMapping,
                mappingIsValid,
                uploadedHeaders,
            ],
        );

    const persistOptions =
        useCallback(
            async (
                targetBatch:
                    ImportBatchRead,
            ): Promise<ImportBatchRead> => {
                const updated =
                    await updateImportBatch(
                        targetBatch.id,
                        {
                            import_options:
                                templateValueRecord(
                                    importOptions,
                                ),
                        },
                    );

                setBatch(
                    updated,
                );

                return updated;
            },
            [importOptions],
        );

    const goBack =
        useCallback((): void => {
            if (
                currentStepIndex ===
                0 ||
                isWorking
            ) {
                return;
            }

            setErrorMessage(null);
            setSuccessMessage(null);

            setCurrentStepIndex(
                (current) =>
                    Math.max(
                        0,
                        current - 1,
                    ),
            );
        }, [
            currentStepIndex,
            isWorking,
        ]);

    const goNext =
        useCallback(
            async (): Promise<void> => {
                if (
                    disabled ||
                    isWorking
                ) {
                    return;
                }

                setErrorMessage(null);
                setSuccessMessage(null);

                try {
                    setIsWorking(true);

                    if (
                        currentStep.id ===
                        "upload"
                    ) {
                        await ensureBatchCreated();
                    }

                    if (
                        currentStep.id ===
                        "mapping"
                    ) {
                        if (!mappingIsValid) {
                            throw new Error(
                                "Complete the required column mappings before continuing.",
                            );
                        }

                        const targetBatch =
                            await ensureBatchCreated();

                        await persistMapping(
                            targetBatch,
                        );
                    }

                    if (
                        currentStep.id ===
                        "options"
                    ) {
                        const targetBatch =
                            await ensureBatchCreated();

                        await persistOptions(
                            targetBatch,
                        );
                    }

                    setCurrentStepIndex(
                        (current) =>
                            Math.min(
                                WIZARD_STEPS.length -
                                1,
                                current + 1,
                            ),
                    );
                } catch (error) {
                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                } finally {
                    setIsWorking(false);
                }
            },
            [
                currentStep.id,
                disabled,
                ensureBatchCreated,
                isWorking,
                mappingIsValid,
                persistMapping,
                persistOptions,
            ],
        );

    const completeImport =
        useCallback(
            async (): Promise<void> => {
                if (
                    disabled ||
                    isWorking
                ) {
                    return;
                }

                if (!selectedFile) {
                    setErrorMessage(
                        "Select a CSV file before starting the import.",
                    );
                    return;
                }

                setIsWorking(true);
                setErrorMessage(null);
                setSuccessMessage(null);

                try {
                    let targetBatch =
                        await ensureBatchCreated();

                    targetBatch =
                        await persistMapping(
                            targetBatch,
                        );

                    targetBatch =
                        await persistOptions(
                            targetBatch,
                        );

                    const uploadedBatch =
                        await uploadImportCsv(
                            targetBatch.id,
                            selectedFile,
                        );

                    setBatch(
                        uploadedBatch,
                    );

                    setSuccessMessage(
                        "The CSV file was uploaded successfully and validation has been queued.",
                    );

                    await onCompleted?.(
                        uploadedBatch,
                    );

                    if (
                        navigateToBatchOnComplete
                    ) {
                        router.push(
                            `/school-admin/imports/${uploadedBatch.id}`,
                        );
                    }
                } catch (error) {
                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                } finally {
                    setIsWorking(false);
                }
            },
            [
                disabled,
                ensureBatchCreated,
                isWorking,
                navigateToBatchOnComplete,
                onCompleted,
                persistMapping,
                persistOptions,
                router,
                selectedFile,
            ],
        );

    const downloadTemplate =
        useCallback(
            async (): Promise<void> => {
                if (
                    !selectedImportType ||
                    isWorking
                ) {
                    return;
                }

                setIsWorking(true);
                setErrorMessage(null);

                try {
                    const blob =
                        await downloadImportTemplate(
                            selectedImportType,
                        );

                    const url =
                        URL.createObjectURL(
                            blob,
                        );

                    const anchor =
                        document.createElement(
                            "a",
                        );

                    anchor.href = url;
                    anchor.download =
                        `${selectedImportType}_import_template.csv`;

                    document.body.appendChild(
                        anchor,
                    );

                    anchor.click();
                    anchor.remove();

                    URL.revokeObjectURL(
                        url,
                    );
                } catch (error) {
                    setErrorMessage(
                        getErrorMessage(
                            error,
                        ),
                    );
                } finally {
                    setIsWorking(false);
                }
            },
            [
                isWorking,
                selectedImportType,
            ],
        );

    const canContinue =
        useMemo(() => {
            if (
                disabled ||
                isWorking
            ) {
                return false;
            }

            switch (
            currentStep.id
            ) {
                case "type":
                    return (
                        selectedImportType.length >
                        0
                    );

                case "template":
                    return (
                        templateMetadata !==
                        null
                    );

                case "upload":
                    return (
                        selectedFile !==
                        null &&
                        uploadedHeaders.length >
                        0
                    );

                case "mapping":
                    return mappingIsValid;

                case "options":
                    return true;

                case "review":
                    return (
                        selectedFile !==
                        null &&
                        mappingIsValid
                    );

                default:
                    return false;
            }
        }, [
            currentStep.id,
            disabled,
            isWorking,
            mappingIsValid,
            selectedFile,
            selectedImportType,
            templateMetadata,
            uploadedHeaders.length,
        ]);

    const renderTypeStep =
        (): React.ReactNode => {
            if (isLoadingTemplates) {
                return (
                    <div className="flex min-h-48 items-center justify-center gap-3 text-slate-600">
                        <Loader2
                            className="h-5 w-5 animate-spin"
                            aria-hidden="true"
                        />
                        Loading import types…
                    </div>
                );
            }

            return (
                <div className="grid gap-3 md:grid-cols-2">
                    {templates.map(
                        (
                            template:
                                ImportTemplateSummaryRead,
                        ) => {
                            const selected =
                                template.import_type ===
                                selectedImportType;

                            return (
                                <button
                                    key={
                                        template.import_type
                                    }
                                    type="button"
                                    disabled={
                                        disabled ||
                                        isWorking
                                    }
                                    onClick={() =>
                                        handleImportTypeChange(
                                            template.import_type,
                                        )
                                    }
                                    className={[
                                        "rounded-xl border p-4 text-left transition",
                                        selected
                                            ? "border-blue-600 bg-blue-50 ring-2 ring-blue-100"
                                            : "border-slate-200 bg-white hover:border-blue-300",
                                        disabled
                                            ? "cursor-not-allowed opacity-60"
                                            : "",
                                    ].join(
                                        " ",
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <h3 className="font-semibold text-slate-950">
                                                {
                                                    template.display_name
                                                }
                                            </h3>

                                            <p className="mt-1 text-sm leading-6 text-slate-600">
                                                {
                                                    template.description
                                                }
                                            </p>
                                        </div>

                                        {selected ? (
                                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
                                                <Check
                                                    className="h-4 w-4"
                                                    aria-hidden="true"
                                                />
                                            </span>
                                        ) : null}
                                    </div>

                                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                                        <span className="rounded-full bg-slate-100 px-2.5 py-1">
                                            {
                                                template.required_field_count
                                            }{" "}
                                            required
                                        </span>

                                        <span className="rounded-full bg-slate-100 px-2.5 py-1">
                                            {
                                                template.optional_field_count
                                            }{" "}
                                            optional
                                        </span>
                                    </div>
                                </button>
                            );
                        },
                    )}
                </div>
            );
        };

    const renderTemplateStep =
        (): React.ReactNode => {
            if (isLoadingMetadata) {
                return (
                    <div className="flex min-h-48 items-center justify-center gap-3 text-slate-600">
                        <Loader2
                            className="h-5 w-5 animate-spin"
                            aria-hidden="true"
                        />
                        Loading template metadata…
                    </div>
                );
            }

            if (!templateMetadata) {
                return (
                    <p className="text-sm text-slate-600">
                        Template metadata is not
                        available.
                    </p>
                );
            }

            return (
                <div className="space-y-5">
                    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                        <h3 className="font-semibold text-blue-950">
                            {
                                templateMetadata.display_name
                            }
                        </h3>

                        <p className="mt-1 text-sm leading-6 text-blue-900">
                            {
                                templateMetadata.description
                            }
                        </p>

                        <button
                            type="button"
                            disabled={
                                disabled ||
                                isWorking
                            }
                            onClick={() => {
                                void downloadTemplate();
                            }}
                            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <Download
                                className="h-4 w-4"
                                aria-hidden="true"
                            />
                            Download CSV template
                        </button>
                    </div>

                    <div className="overflow-hidden rounded-xl border border-slate-200">
                        <div className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,0.8fr)_auto] gap-3 bg-slate-100 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-600">
                            <span>Column</span>
                            <span>Type</span>
                            <span>Required</span>
                        </div>

                        {templateMetadata.fields.map(
                            (field) => (
                                <div
                                    key={
                                        field.name
                                    }
                                    className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,0.8fr)_auto] gap-3 border-t border-slate-200 px-4 py-3 text-sm"
                                >
                                    <div>
                                        <p className="font-medium text-slate-900">
                                            {
                                                field.label
                                            }
                                        </p>

                                        <p className="text-xs text-slate-500">
                                            {
                                                field.column_name
                                            }
                                        </p>
                                    </div>

                                    <span className="text-slate-600">
                                        {
                                            field.data_type
                                        }
                                    </span>

                                    <span>
                                        {field.required
                                            ? "Yes"
                                            : "No"}
                                    </span>
                                </div>
                            ),
                        )}
                    </div>
                </div>
            );
        };

    const renderUploadStep =
        (): React.ReactNode => (
            <div className="space-y-4">
                <label className="block rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center hover:border-blue-400">
                    <FileSpreadsheet
                        className="mx-auto h-10 w-10 text-blue-700"
                        aria-hidden="true"
                    />

                    <span className="mt-3 block font-semibold text-slate-950">
                        Choose a CSV file
                    </span>

                    <span className="mt-1 block text-sm text-slate-600">
                        Maximum file size: 10 MB
                    </span>

                    <input
                        type="file"
                        accept=".csv,text/csv,application/csv,application/vnd.ms-excel"
                        disabled={
                            disabled ||
                            isWorking
                        }
                        onChange={(event) => {
                            void handleFileChange(
                                event,
                            );
                        }}
                        className="mt-4 block w-full text-sm text-slate-700 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-700 file:px-4 file:py-2 file:font-semibold file:text-white hover:file:bg-blue-800"
                    />
                </label>

                {selectedFile ? (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                        <div className="flex items-start gap-3">
                            <CheckCircle2
                                className="mt-0.5 h-5 w-5 text-emerald-700"
                                aria-hidden="true"
                            />

                            <div>
                                <p className="font-semibold text-emerald-950">
                                    {
                                        selectedFile.name
                                    }
                                </p>

                                <p className="mt-1 text-sm text-emerald-800">
                                    {formatFileSize(
                                        selectedFile.size,
                                    )}{" "}
                                    ·{" "}
                                    {
                                        uploadedHeaders.length
                                    }{" "}
                                    columns detected
                                </p>
                            </div>
                        </div>
                    </div>
                ) : null}
            </div>
        );

    const renderMappingStep =
        (): React.ReactNode => (
            <div className="space-y-4">
                <p className="text-sm leading-6 text-slate-600">
                    Match each uploaded CSV column
                    to a field accepted by the{" "}
                    {
                        templateMetadata?.display_name
                    }{" "}
                    importer.
                </p>

                <div className="space-y-3">
                    {uploadedHeaders.map(
                        (header) => (
                            <div
                                key={
                                    header
                                }
                                className="grid gap-3 rounded-xl border border-slate-200 p-4 md:grid-cols-2 md:items-center"
                            >
                                <div>
                                    <p className="font-medium text-slate-900">
                                        {
                                            header
                                        }
                                    </p>

                                    <p className="text-xs text-slate-500">
                                        Uploaded CSV column
                                    </p>
                                </div>

                                <select
                                    value={
                                        columnMapping[
                                        header
                                        ] ?? ""
                                    }
                                    disabled={
                                        disabled ||
                                        isWorking
                                    }
                                    onChange={(
                                        event,
                                    ) => {
                                        setColumnMapping(
                                            (
                                                current,
                                            ) => ({
                                                ...current,
                                                [header]:
                                                    event
                                                        .target
                                                        .value,
                                            }),
                                        );
                                    }}
                                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
                                >
                                    <option value="">
                                        Do not import
                                    </option>

                                    {templateMetadata?.fields.map(
                                        (
                                            field,
                                        ) => (
                                            <option
                                                key={
                                                    field.column_name
                                                }
                                                value={
                                                    field.column_name
                                                }
                                            >
                                                {
                                                    field.label
                                                }
                                                {field.required
                                                    ? " *"
                                                    : ""}
                                            </option>
                                        ),
                                    )}
                                </select>
                            </div>
                        ),
                    )}
                </div>

                {missingRequiredFields.length >
                    0 ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                        <p className="font-semibold">
                            Required fields still
                            need mapping:
                        </p>

                        <p className="mt-1">
                            {missingRequiredFields
                                .map(
                                    (
                                        field,
                                    ) =>
                                        field.label,
                                )
                                .join(", ")}
                        </p>
                    </div>
                ) : null}

                {duplicateTargetColumns.size >
                    0 ? (
                    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
                        A destination field cannot
                        be mapped more than once.
                    </div>
                ) : null}
            </div>
        );

    const renderOptionsStep =
        (): React.ReactNode => (
            <div className="space-y-3">
                {[
                    {
                        key: "skip_duplicate_rows",
                        title: "Skip duplicate rows",
                        description:
                            "Keep processing when an identical row is encountered.",
                    },
                    {
                        key: "update_existing_records",
                        title: "Update existing records",
                        description:
                            "Allow matching records to be updated where the importer supports it.",
                    },
                    {
                        key: "send_account_notifications",
                        title: "Send account notifications",
                        description:
                            "Send account-related notifications where supported.",
                    },
                ].map((option) => {
                    const key =
                        option.key as keyof WizardImportOptions;

                    return (
                        <label
                            key={
                                option.key
                            }
                            className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 p-4"
                        >
                            <input
                                type="checkbox"
                                checked={
                                    importOptions[
                                    key
                                    ]
                                }
                                disabled={
                                    disabled ||
                                    isWorking
                                }
                                onChange={(
                                    event,
                                ) => {
                                    setImportOptions(
                                        (
                                            current,
                                        ) => ({
                                            ...current,
                                            [key]:
                                                event
                                                    .target
                                                    .checked,
                                        }),
                                    );
                                }}
                                className="mt-1 h-4 w-4 rounded border-slate-300"
                            />

                            <span>
                                <span className="block font-semibold text-slate-950">
                                    {
                                        option.title
                                    }
                                </span>

                                <span className="mt-1 block text-sm leading-6 text-slate-600">
                                    {
                                        option.description
                                    }
                                </span>
                            </span>
                        </label>
                    );
                })}
            </div>
        );

    const renderReviewStep =
        (): React.ReactNode => (
            <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Import type
                        </p>

                        <p className="mt-2 font-semibold text-slate-950">
                            {selectedTemplateSummary?.display_name ??
                                selectedImportType}
                        </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            File
                        </p>

                        <p className="mt-2 font-semibold text-slate-950">
                            {
                                selectedFile?.name
                            }
                        </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            CSV columns
                        </p>

                        <p className="mt-2 font-semibold text-slate-950">
                            {
                                uploadedHeaders.length
                            }
                        </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Mapped fields
                        </p>

                        <p className="mt-2 font-semibold text-slate-950">
                            {
                                mappedTargetColumns.length
                            }
                        </p>
                    </div>
                </div>

                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
                    Starting the import will upload
                    the CSV and queue backend
                    validation. You can monitor
                    progress and row-level issues on
                    the batch-details page.
                </div>
            </div>
        );

    const renderCurrentStep =
        (): React.ReactNode => {
            switch (currentStep.id) {
                case "type":
                    return renderTypeStep();

                case "template":
                    return renderTemplateStep();

                case "upload":
                    return renderUploadStep();

                case "mapping":
                    return renderMappingStep();

                case "options":
                    return renderOptionsStep();

                case "review":
                    return renderReviewStep();

                default:
                    return null;
            }
        };

    return (
        <section
            className={[
                "overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm",
                className,
            ].join(" ")}
        >
            <header className="border-b border-slate-200 bg-slate-950 px-6 py-5 text-white">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-300">
                            Import wizard
                        </p>

                        <h2 className="mt-1 text-2xl font-bold">
                            Import school data
                        </h2>

                        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                            Follow the steps to select
                            a template, upload a CSV,
                            map its columns and begin
                            validation.
                        </p>
                    </div>

                    <button
                        type="button"
                        disabled={
                            isWorking
                        }
                        onClick={
                            resetWizard
                        }
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-600 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        <RotateCcw
                            className="h-4 w-4"
                            aria-hidden="true"
                        />
                        Reset
                    </button>
                </div>
            </header>

            <nav
                aria-label="Import wizard progress"
                className="border-b border-slate-200 bg-slate-50 px-6 py-4"
            >
                <ol className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
                    {WIZARD_STEPS.map(
                        (
                            step,
                            index,
                        ) => {
                            const completed =
                                index <
                                currentStepIndex;

                            const active =
                                index ===
                                currentStepIndex;

                            return (
                                <li
                                    key={
                                        step.id
                                    }
                                    className="flex items-center gap-2"
                                >
                                    <span
                                        className={[
                                            "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold",
                                            completed
                                                ? "bg-emerald-600 text-white"
                                                : active
                                                    ? "bg-blue-700 text-white"
                                                    : "bg-slate-200 text-slate-600",
                                        ].join(
                                            " ",
                                        )}
                                    >
                                        {completed ? (
                                            <Check
                                                className="h-4 w-4"
                                                aria-hidden="true"
                                            />
                                        ) : (
                                            index +
                                            1
                                        )}
                                    </span>

                                    <span className="min-w-0 text-sm font-medium text-slate-700">
                                        {
                                            step.label
                                        }
                                    </span>
                                </li>
                            );
                        },
                    )}
                </ol>
            </nav>

            <div className="p-6">
                <div className="mb-5">
                    <h3 className="text-xl font-bold text-slate-950">
                        {
                            currentStep.label
                        }
                    </h3>

                    <p className="mt-1 text-sm text-slate-600">
                        {
                            currentStep.description
                        }
                    </p>
                </div>

                {errorMessage ? (
                    <div
                        role="alert"
                        className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900"
                    >
                        <AlertCircle
                            className="mt-0.5 h-5 w-5 shrink-0"
                            aria-hidden="true"
                        />
                        <span>
                            {
                                errorMessage
                            }
                        </span>
                    </div>
                ) : null}

                {successMessage ? (
                    <div
                        role="status"
                        className="mb-5 flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
                    >
                        <CheckCircle2
                            className="mt-0.5 h-5 w-5 shrink-0"
                            aria-hidden="true"
                        />
                        <span>
                            {
                                successMessage
                            }
                        </span>
                    </div>
                ) : null}

                {renderCurrentStep()}
            </div>

            <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4">
                <button
                    type="button"
                    disabled={
                        currentStepIndex ===
                        0 ||
                        isWorking
                    }
                    onClick={goBack}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    <ArrowLeft
                        className="h-4 w-4"
                        aria-hidden="true"
                    />
                    Back
                </button>

                {currentStep.id ===
                    "review" ? (
                    <button
                        type="button"
                        disabled={
                            !canContinue
                        }
                        onClick={() => {
                            void completeImport();
                        }}
                        className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isWorking ? (
                            <Loader2
                                className="h-4 w-4 animate-spin"
                                aria-hidden="true"
                            />
                        ) : (
                            <Upload
                                className="h-4 w-4"
                                aria-hidden="true"
                            />
                        )}

                        Start import
                    </button>
                ) : (
                    <button
                        type="button"
                        disabled={
                            !canContinue
                        }
                        onClick={() => {
                            void goNext();
                        }}
                        className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isWorking ? (
                            <Loader2
                                className="h-4 w-4 animate-spin"
                                aria-hidden="true"
                            />
                        ) : null}

                        Continue

                        <ArrowRight
                            className="h-4 w-4"
                            aria-hidden="true"
                        />
                    </button>
                )}
            </footer>
        </section>
    );
}
