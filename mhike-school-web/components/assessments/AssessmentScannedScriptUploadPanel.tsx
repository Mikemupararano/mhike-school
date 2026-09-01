"use client";

import {
    ChangeEvent,
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";

import {
    getAssessmentCandidates,
    uploadAssessmentScannedScript,
    type AssessmentCandidate,
    type AssessmentScript,
} from "@/lib/services/assessment-candidates";


// ---------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------


const MAX_SCANNED_SCRIPT_SIZE_BYTES =
    25 * 1024 * 1024;


// ---------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------


type AssessmentScannedScriptUploadPanelProps = {
    assessmentId: number;
};


// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------


function getLatestScript(
    candidate: AssessmentCandidate,
): AssessmentScript | null {
    if (candidate.scripts.length === 0) {
        return null;
    }

    return candidate.scripts.reduce(
        (
            latest,
            current,
        ) => (
            current.version > latest.version
                ? current
                : latest
        ),
    );
}


function candidateDisplayName(
    candidate: AssessmentCandidate,
): string {
    if (candidate.candidate_number) {
        return candidate.candidate_number;
    }

    return `Student ${candidate.student_id}`;
}


function formatStatus(
    value: string,
): string {
    return value
        .replaceAll(
            "_",
            " ",
        )
        .replace(
            /\b\w/g,
            character => (
                character.toUpperCase()
            ),
        );
}


// ---------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------


export default function AssessmentScannedScriptUploadPanel({
    assessmentId,
}: AssessmentScannedScriptUploadPanelProps) {
    const fileInputRef =
        useRef<HTMLInputElement | null>(
            null,
        );

    const [
        candidates,
        setCandidates,
    ] = useState<AssessmentCandidate[]>(
        [],
    );

    const [
        loading,
        setLoading,
    ] = useState(
        true,
    );

    const [
        selectedCandidateId,
        setSelectedCandidateId,
    ] = useState<number | null>(
        null,
    );

    const [
        selectedFile,
        setSelectedFile,
    ] = useState<File | null>(
        null,
    );

    const [
        uploadingCandidateId,
        setUploadingCandidateId,
    ] = useState<number | null>(
        null,
    );

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


    const loadCandidates =
        useCallback(
            async () => {
                setLoading(
                    true,
                );

                setErrorMessage(
                    null,
                );

                try {
                    const result =
                        await getAssessmentCandidates(
                            assessmentId,
                        );

                    setCandidates(
                        result,
                    );
                } catch (error) {
                    setErrorMessage(
                        error instanceof Error
                            ? error.message
                            : "Unable to load assessment candidates.",
                    );
                } finally {
                    setLoading(
                        false,
                    );
                }
            },
            [
                assessmentId,
            ],
        );


    useEffect(
        () => {
            void loadCandidates();
        },
        [
            loadCandidates,
        ],
    );


    const sortedCandidates =
        useMemo(
            () => (
                [...candidates].sort(
                    (
                        first,
                        second,
                    ) => (
                        candidateDisplayName(
                            first,
                        ).localeCompare(
                            candidateDisplayName(
                                second,
                            ),
                            undefined,
                            {
                                numeric: true,
                            },
                        )
                    ),
                )
            ),
            [
                candidates,
            ],
        );


    const selectedCandidate =
        useMemo(
            () => (
                sortedCandidates.find(
                    candidate => (
                        candidate.id
                        === selectedCandidateId
                    ),
                )
                ?? null
            ),
            [
                selectedCandidateId,
                sortedCandidates,
            ],
        );


    const clearSelection =
        useCallback(
            () => {
                setSelectedCandidateId(
                    null,
                );

                setSelectedFile(
                    null,
                );

                if (fileInputRef.current) {
                    fileInputRef.current.value =
                        "";
                }
            },
            [],
        );


    const beginUpload =
        useCallback(
            (
                candidate: AssessmentCandidate,
            ) => {
                setSelectedCandidateId(
                    candidate.id,
                );

                setSelectedFile(
                    null,
                );

                setErrorMessage(
                    null,
                );

                setSuccessMessage(
                    null,
                );

                if (fileInputRef.current) {
                    fileInputRef.current.value =
                        "";
                }
            },
            [],
        );


    const handleFileChange =
        useCallback(
            (
                event:
                    ChangeEvent<HTMLInputElement>,
            ) => {
                const file =
                    event.target.files?.[0]
                    ?? null;

                setErrorMessage(
                    null,
                );

                setSuccessMessage(
                    null,
                );

                if (!file) {
                    setSelectedFile(
                        null,
                    );

                    return;
                }

                const lowerName =
                    file.name
                        .trim()
                        .toLowerCase();

                if (
                    !lowerName.endsWith(
                        ".pdf",
                    )
                ) {
                    setSelectedFile(
                        null,
                    );

                    event.target.value =
                        "";

                    setErrorMessage(
                        "Scanned scripts must be uploaded as PDF files.",
                    );

                    return;
                }

                if (
                    file.size
                    > MAX_SCANNED_SCRIPT_SIZE_BYTES
                ) {
                    setSelectedFile(
                        null,
                    );

                    event.target.value =
                        "";

                    setErrorMessage(
                        "The PDF is larger than the 25 MB upload limit.",
                    );

                    return;
                }

                setSelectedFile(
                    file,
                );
            },
            [],
        );


    const handleUpload =
        useCallback(
            async () => {
                if (
                    !selectedCandidate
                    || !selectedFile
                ) {
                    return;
                }

                const existingScript =
                    getLatestScript(
                        selectedCandidate,
                    );

                if (existingScript) {
                    const confirmed =
                        window.confirm(
                            `This candidate already has script version ${existingScript.version}. Uploading this PDF will create a new script version. Continue?`,
                        );

                    if (!confirmed) {
                        return;
                    }
                }

                try {
                    setUploadingCandidateId(
                        selectedCandidate.id,
                    );

                    setErrorMessage(
                        null,
                    );

                    setSuccessMessage(
                        null,
                    );

                    const uploadedScript =
                        await uploadAssessmentScannedScript(
                            selectedCandidate.id,
                            selectedFile,
                        );

                    await loadCandidates();

                    setSuccessMessage(
                        `Uploaded ${selectedFile.name} as script version ${uploadedScript.version} for ${candidateDisplayName(
                            selectedCandidate,
                        )}.`,
                    );

                    clearSelection();
                } catch (error) {
                    setErrorMessage(
                        error instanceof Error
                            ? error.message
                            : "Unable to upload the scanned script.",
                    );
                } finally {
                    setUploadingCandidateId(
                        null,
                    );
                }
            },
            [
                clearSelection,
                loadCandidates,
                selectedCandidate,
                selectedFile,
            ],
        );


    return (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="text-xs font-extrabold uppercase tracking-[0.16em] text-blue-600">
                        Paper assessment workflow
                    </div>

                    <h2 className="mt-1 text-2xl font-extrabold text-slate-900">
                        Scanned scripts
                    </h2>

                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                        Upload completed handwritten assessment papers against the correct candidate.
                        Uploaded PDFs are submitted directly into the marking workflow.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={
                        () => {
                            void loadCandidates();
                        }
                    }
                    disabled={loading}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-400 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {
                        loading
                            ? "Refreshing…"
                            : "Refresh candidates"
                    }
                </button>
            </div>

            {
                errorMessage
                    ? (
                        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                            {errorMessage}
                        </div>
                    )
                    : null
            }

            {
                successMessage
                    ? (
                        <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
                            {successMessage}
                        </div>
                    )
                    : null
            }

            {
                loading
                    ? (
                        <div className="mt-6 rounded-xl border border-dashed border-slate-300 px-6 py-10 text-center text-sm text-slate-500">
                            Loading assessment candidates…
                        </div>
                    )
                    : sortedCandidates.length === 0
                        ? (
                            <div className="mt-6 rounded-xl border border-dashed border-slate-300 px-6 py-10 text-center">
                                <div className="font-bold text-slate-700">
                                    No candidates allocated
                                </div>

                                <p className="mt-2 text-sm text-slate-500">
                                    Candidates must be allocated to this assessment before scanned scripts can be uploaded.
                                </p>
                            </div>
                        )
                        : (
                            <div className="mt-6 overflow-hidden rounded-xl border border-slate-200">
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-slate-200">
                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th className="px-4 py-3 text-left text-xs font-extrabold uppercase tracking-wide text-slate-500">
                                                    Candidate
                                                </th>

                                                <th className="px-4 py-3 text-left text-xs font-extrabold uppercase tracking-wide text-slate-500">
                                                    Candidate status
                                                </th>

                                                <th className="px-4 py-3 text-left text-xs font-extrabold uppercase tracking-wide text-slate-500">
                                                    Current script
                                                </th>

                                                <th className="px-4 py-3 text-right text-xs font-extrabold uppercase tracking-wide text-slate-500">
                                                    Action
                                                </th>
                                            </tr>
                                        </thead>

                                        <tbody className="divide-y divide-slate-100 bg-white">
                                            {
                                                sortedCandidates.map(
                                                    candidate => {
                                                        const script =
                                                            getLatestScript(
                                                                candidate,
                                                            );

                                                        const hasScannedScript =
                                                            script?.source_type
                                                            === "scanned_pdf";

                                                        return (
                                                            <tr
                                                                key={candidate.id}
                                                                className="hover:bg-slate-50/70"
                                                            >
                                                                <td className="px-4 py-4">
                                                                    <div className="font-bold text-slate-900">
                                                                        {
                                                                            candidateDisplayName(
                                                                                candidate,
                                                                            )
                                                                        }
                                                                    </div>

                                                                    <div className="mt-1 text-xs text-slate-400">
                                                                        Candidate ID {candidate.id}
                                                                    </div>
                                                                </td>

                                                                <td className="px-4 py-4">
                                                                    <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
                                                                        {
                                                                            formatStatus(
                                                                                candidate.status,
                                                                            )
                                                                        }
                                                                    </span>
                                                                </td>

                                                                <td className="px-4 py-4">
                                                                    {
                                                                        script
                                                                            ? (
                                                                                <div>
                                                                                    <div className="flex flex-wrap items-center gap-2">
                                                                                        <span className="font-semibold text-slate-800">
                                                                                            Version {script.version}
                                                                                        </span>

                                                                                        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700">
                                                                                            {
                                                                                                formatStatus(
                                                                                                    script.status,
                                                                                                )
                                                                                            }
                                                                                        </span>

                                                                                        {
                                                                                            hasScannedScript
                                                                                                ? (
                                                                                                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700">
                                                                                                        Scanned PDF
                                                                                                    </span>
                                                                                                )
                                                                                                : null
                                                                                        }
                                                                                    </div>

                                                                                    <div className="mt-1 max-w-md truncate text-xs text-slate-500">
                                                                                        {
                                                                                            script.source_filename
                                                                                            ?? script.source_type
                                                                                            ?? "Assessment script"
                                                                                        }
                                                                                    </div>
                                                                                </div>
                                                                            )
                                                                            : (
                                                                                <span className="text-sm text-slate-400">
                                                                                    No script uploaded
                                                                                </span>
                                                                            )
                                                                    }
                                                                </td>

                                                                <td className="px-4 py-4 text-right">
                                                                    <button
                                                                        type="button"
                                                                        onClick={
                                                                            () => {
                                                                                beginUpload(
                                                                                    candidate,
                                                                                );
                                                                            }
                                                                        }
                                                                        disabled={
                                                                            uploadingCandidateId
                                                                            !== null
                                                                        }
                                                                        className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                                                                    >
                                                                        {
                                                                            script
                                                                                ? "Upload replacement"
                                                                                : "Upload PDF"
                                                                        }
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        );
                                                    },
                                                )
                                            }
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )
            }

            {
                selectedCandidate
                    ? (
                        <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50/50 p-5">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <div className="text-xs font-extrabold uppercase tracking-wide text-blue-600">
                                        Upload scanned paper
                                    </div>

                                    <div className="mt-1 text-lg font-extrabold text-slate-900">
                                        {
                                            candidateDisplayName(
                                                selectedCandidate,
                                            )
                                        }
                                    </div>
                                </div>

                                <button
                                    type="button"
                                    onClick={clearSelection}
                                    disabled={
                                        uploadingCandidateId
                                        !== null
                                    }
                                    className="text-sm font-semibold text-slate-500 hover:text-slate-800 disabled:opacity-50"
                                >
                                    Cancel
                                </button>
                            </div>

                            <div className="mt-4">
                                <label className="block">
                                    <span className="text-sm font-bold text-slate-700">
                                        PDF file
                                    </span>

                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept=".pdf,application/pdf"
                                        onChange={handleFileChange}
                                        disabled={
                                            uploadingCandidateId
                                            !== null
                                        }
                                        className="mt-2 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-bold file:text-slate-700 hover:file:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
                                    />
                                </label>

                                {
                                    selectedFile
                                        ? (
                                            <div className="mt-3 rounded-lg bg-white px-3 py-2 text-sm text-slate-600">
                                                Selected:{" "}
                                                <span className="font-semibold text-slate-900">
                                                    {selectedFile.name}
                                                </span>
                                            </div>
                                        )
                                        : null
                                }
                            </div>

                            <div className="mt-4 flex justify-end">
                                <button
                                    type="button"
                                    onClick={
                                        () => {
                                            void handleUpload();
                                        }
                                    }
                                    disabled={
                                        !selectedFile
                                        || uploadingCandidateId
                                            !== null
                                    }
                                    className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-extrabold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {
                                        uploadingCandidateId
                                        === selectedCandidate.id
                                            ? "Uploading…"
                                            : "Upload scanned script"
                                    }
                                </button>
                            </div>
                        </div>
                    )
                    : null
            }
        </section>
    );
}
