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

type ImportUploadPanelProps = {
    title?: string;
    description?: string;
    acceptedFileTypes?: string;
    maximumFileSizeMb?: number;
    disabled?: boolean;
    isUploading?: boolean;
    errorMessage?: string | null;
    successMessage?: string | null;
    onUpload: (file: File) => Promise<void> | void;
    onFileSelected?: (file: File | null) => void;
    className?: string;
};

function formatFileSize(sizeInBytes: number): string {
    if (sizeInBytes < 1024) {
        return `${sizeInBytes} B`;
    }

    const sizeInKilobytes = sizeInBytes / 1024;

    if (sizeInKilobytes < 1024) {
        return `${sizeInKilobytes.toFixed(1)} KB`;
    }

    const sizeInMegabytes = sizeInKilobytes / 1024;

    return `${sizeInMegabytes.toFixed(1)} MB`;
}

function isCsvFile(file: File): boolean {
    const fileName = file.name.toLowerCase();

    return (
        fileName.endsWith(".csv") ||
        file.type === "text/csv" ||
        file.type === "application/csv" ||
        file.type === "application/vnd.ms-excel"
    );
}

export default function ImportUploadPanel({
    title = "Upload CSV file",
    description = "Choose a CSV file containing the records you want to import.",
    acceptedFileTypes = ".csv,text/csv",
    maximumFileSizeMb = 10,
    disabled = false,
    isUploading = false,
    errorMessage = null,
    successMessage = null,
    onUpload,
    onFileSelected,
    className = "",
}: ImportUploadPanelProps) {
    const fileInputRef = useRef<HTMLInputElement | null>(null);

    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [validationError, setValidationError] = useState<string | null>(null);

    const maximumFileSizeBytes = maximumFileSizeMb * 1024 * 1024;

    const effectiveErrorMessage = validationError ?? errorMessage;

    const canUpload = useMemo(
        () =>
            selectedFile !== null &&
            !disabled &&
            !isUploading &&
            effectiveErrorMessage === null,
        [disabled, effectiveErrorMessage, isUploading, selectedFile],
    );

    function updateSelectedFile(file: File | null) {
        setSelectedFile(file);
        onFileSelected?.(file);
    }

    function validateAndSelectFile(file: File | null) {
        setValidationError(null);

        if (!file) {
            updateSelectedFile(null);
            return;
        }

        if (!isCsvFile(file)) {
            setValidationError("Please select a valid CSV file.");
            updateSelectedFile(null);
            return;
        }

        if (file.size === 0) {
            setValidationError("The selected CSV file is empty.");
            updateSelectedFile(null);
            return;
        }

        if (file.size > maximumFileSizeBytes) {
            setValidationError(
                `The file is too large. The maximum size is ${maximumFileSizeMb} MB.`,
            );
            updateSelectedFile(null);
            return;
        }

        updateSelectedFile(file);
    }

    function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
        const file = event.target.files?.[0] ?? null;
        validateAndSelectFile(file);
    }

    function handleDragEnter(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();

        if (!disabled && !isUploading) {
            setIsDragging(true);
        }
    }

    function handleDragOver(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();
    }

    function handleDragLeave(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();

        if (event.currentTarget === event.target) {
            setIsDragging(false);
        }
    }

    function handleDrop(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();
        setIsDragging(false);

        if (disabled || isUploading) {
            return;
        }

        const file = event.dataTransfer.files?.[0] ?? null;
        validateAndSelectFile(file);
    }

    function openFilePicker() {
        if (!disabled && !isUploading) {
            fileInputRef.current?.click();
        }
    }

    function clearSelectedFile() {
        setValidationError(null);
        updateSelectedFile(null);

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!selectedFile || !canUpload) {
            return;
        }

        try {
            await onUpload(selectedFile);
        } catch {
            // The parent component owns API error handling.
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
                <h2 className="text-xl font-bold text-slate-950">{title}</h2>

                <p className="mt-1 text-sm leading-6 text-slate-600">
                    {description}
                </p>
            </div>

            <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept={acceptedFileTypes}
                    className="sr-only"
                    disabled={disabled || isUploading}
                    onChange={handleFileInputChange}
                />

                <div
                    role="button"
                    tabIndex={disabled || isUploading ? -1 : 0}
                    aria-disabled={disabled || isUploading}
                    className={[
                        "flex min-h-56 flex-col items-center justify-center rounded-2xl",
                        "border-2 border-dashed px-6 py-8 text-center transition",
                        isDragging
                            ? "border-blue-500 bg-blue-50"
                            : "border-slate-300 bg-slate-50",
                        disabled || isUploading
                            ? "cursor-not-allowed opacity-60"
                            : "cursor-pointer hover:border-blue-400 hover:bg-blue-50/60",
                    ].join(" ")}
                    onClick={openFilePicker}
                    onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            openFilePicker();
                        }
                    }}
                    onDragEnter={handleDragEnter}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                >
                    <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100 text-blue-700">
                        <Upload className="h-7 w-7" aria-hidden="true" />
                    </span>

                    <p className="mt-4 text-base font-semibold text-slate-950">
                        Drop your CSV file here
                    </p>

                    <p className="mt-1 text-sm text-slate-600">
                        or click to browse your computer
                    </p>

                    <p className="mt-3 text-xs font-medium text-slate-500">
                        CSV files only, up to {maximumFileSizeMb} MB
                    </p>
                </div>

                {selectedFile ? (
                    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                            <FileSpreadsheet className="h-6 w-6" aria-hidden="true" />
                        </span>

                        <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-slate-950">
                                {selectedFile.name}
                            </p>

                            <p className="mt-1 text-xs text-slate-500">
                                {formatFileSize(selectedFile.size)}
                            </p>
                        </div>

                        <button
                            type="button"
                            className={[
                                "inline-flex h-9 w-9 items-center justify-center rounded-lg",
                                "text-slate-500 transition hover:bg-slate-200",
                                "hover:text-slate-900 disabled:cursor-not-allowed",
                                "disabled:opacity-50",
                            ].join(" ")}
                            disabled={disabled || isUploading}
                            aria-label="Remove selected file"
                            onClick={(event) => {
                                event.stopPropagation();
                                clearSelectedFile();
                            }}
                        >
                            <X className="h-5 w-5" aria-hidden="true" />
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

                        <p className="text-sm font-medium">{effectiveErrorMessage}</p>
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

                        <p className="text-sm font-medium">{successMessage}</p>
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
                            <Upload className="h-5 w-5" aria-hidden="true" />
                            Upload CSV
                        </>
                    )}
                </button>
            </form>
        </section>
    );
}