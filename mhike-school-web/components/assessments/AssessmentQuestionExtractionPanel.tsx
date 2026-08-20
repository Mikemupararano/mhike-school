"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";

import ScientificTextEditor from "@/components/assessments/ScientificTextEditor";


type ExtractionStatus =
    | "pending"
    | "processing"
    | "completed"
    | "failed"
    | "imported"
    | "superseded"
    | "cancelled";


type ReviewStatus =
    | "unreviewed"
    | "in_progress"
    | "reviewed";


type QuestionType =
    | "written"
    | "multiple_choice_single"
    | "multiple_choice_multiple"
    | "true_false"
    | "numeric"
    | "diagram_annotation"
    | "structural";


type QuestionAssetType =
    | "image"
    | "diagram"
    | "graph"
    | "figure";


type ExtractionOption = {
    text: string;
    order: number;
    is_correct: boolean;
    feedback: string | null;
    [key: string]: unknown;
};


type ExtractionAsset = {
    asset_type: QuestionAssetType;
    storage_path: string | null;
    content_url: string | null;
    original_filename: string | null;
    mime_type: string | null;
    file_size_bytes: number | null;
    alt_text: string | null;
    caption: string | null;
    order: number;
    candidate_visible: boolean;
    source_document_id: number | null;
    source_page_number: number | null;
    source_bbox: Record<string, unknown> | null;
    included: boolean;
    reviewed: boolean;
    [key: string]: unknown;
};


type AssessmentDocumentSummary = {
    id: number;
    assessment_id: number;
    original_filename: string;
    extraction_requested: boolean;
    extraction_completed: boolean;
    extraction_error: string | null;
};


type ExtractionSource = {
    page_number: number;
    line_number: number | null;
    source_line: string | null;
    [key: string]: unknown;
};


type ExtractionCandidate = {
    question_number: string;
    text: string;
    marks: number | null;
    depth: number;
    parent_question_number: string | null;
    question_type: QuestionType;
    options: ExtractionOption[];
    assets: ExtractionAsset[];
    included: boolean;
    source: ExtractionSource;
    confidence: string;
    requires_review: boolean;
    reviewed: boolean;
    [key: string]: unknown;
};


type ExtractionWarning = {
    code: string;
    message: string;
    page_numbers: number[];
    [key: string]: unknown;
};


type ExtractionProposalSummary = {
    detected_question_count: number;
    questions_with_detected_marks: number;
    detected_mark_sum: number;
    included_question_count: number | null;
    included_mark_sum: number | null;
    [key: string]: unknown;
};


type ExtractionProposal = {
    parser_version: string;
    review_required: boolean;
    auto_import_allowed: boolean;
    review_status: ReviewStatus;
    reviewed_by_id: number | null;
    reviewed_at: string | null;
    review_notes: string | null;
    questions: ExtractionCandidate[];
    summary: ExtractionProposalSummary;
    warnings: ExtractionWarning[];
    declared_totals: Array<{
        marks: number;
        page_number: number;
        line_number: number | null;
        source_line: string | null;
        [key: string]: unknown;
    }>;
    [key: string]: unknown;
};


type ExtractionResponse = {
    id: number;
    assessment_id: number;
    assessment_document_id: number;
    requested_by_id: number;
    imported_by_id: number | null;
    version: number;
    status: ExtractionStatus;
    extractor_name: string;
    extractor_version: string | null;
    parser_version: string;
    page_count: number | null;
    text_page_count: number | null;
    detected_question_count: number | null;
    detected_markable_question_count: number | null;
    detected_total_marks: number | null;
    error_message: string | null;
    started_at: string | null;
    completed_at: string | null;
    imported_at: string | null;
    created_at: string;
    updated_at: string;
    proposal_data: ExtractionProposal | null;
};


type ExtractionSummaryResponse = Omit<
    ExtractionResponse,
    "proposal_data"
>;


type ExtractionHistoryResponse = {
    assessment_id: number;
    assessment_document_id: number;
    extractions: ExtractionSummaryResponse[];
};


type ReviewOptionState = {
    localId: string;
    text: string;
    order: number;
    isCorrect: boolean;
    feedback: string;
};


type ReviewAssetState = {
    assetIndex: number;
    assetType: QuestionAssetType;
    altText: string;
    caption: string;
    order: number;
    candidateVisible: boolean;
    included: boolean;
    reviewed: boolean;

    // Display-only extractor-owned metadata.
    contentUrl: string | null;
    originalFilename: string | null;
    mimeType: string | null;
    fileSizeBytes: number | null;
    sourceDocumentId: number | null;
    sourcePageNumber: number | null;
    sourceBbox: Record<string, unknown> | null;
};


type ReviewQuestionState = {
    candidateIndex: number;
    questionNumber: string;
    text: string;
    marks: string;
    parentQuestionNumber: string;
    questionType: QuestionType;
    options: ReviewOptionState[];
    assets: ReviewAssetState[];
    included: boolean;
    reviewed: boolean;
    source: ExtractionSource;
    confidence: string;
};


type ImportedQuestion = {
    id: number;
    question_number: string;
    parent_question_id: number | null;
    parent_question_number: string | null;
    maximum_mark: number | string;
    order: number;
    is_markable: boolean;
    question_type: QuestionType;
    option_count: number;
    asset_count: number;
    synthesised: boolean;
    source_candidate_index: number | null;
};


type ImportResponse = ExtractionResponse & {
    message: string;
    imported_question_count: number;
    imported_markable_question_count: number;
    synthesised_parent_count: number;
    imported_total_marks: number | string;
    imported_questions: ImportedQuestion[];
};


type ExtractionAction =
    | "extract"
    | "load"
    | "save-review"
    | "complete-review"
    | "import"
    | null;


type ReviewSaveState =
    | "saved"
    | "dirty"
    | "saving"
    | "error";


type ReviewPayload = {
    review_status: ReviewStatus;
    review_notes: string | null;
    questions: Array<{
        candidate_index: number;
        question_number: string;
        text: string;
        marks: number | null;
        parent_question_number: string | null;
        question_type: QuestionType;
        options: Array<{
            text: string;
            order: number;
            is_correct: boolean;
            feedback: string | null;
        }>;
        assets: Array<{
            asset_index: number;
            asset_type: QuestionAssetType;
            alt_text: string | null;
            caption: string | null;
            order: number;
            candidate_visible: boolean;
            included: boolean;
            reviewed: boolean;
        }>;
        included: boolean;
        reviewed: boolean;
    }>;
};


type Props = {
    assessmentId: number;
    questionPaper: AssessmentDocumentSummary;
    isDraft: boolean;
    onImported?: () => void | Promise<void>;
};


const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL
    ?? "http://localhost:8000/api/v1";


function getAuthToken(): string | null {
    if (typeof window === "undefined") {
        return null;
    }

    return sessionStorage.getItem(
        "mhike_token",
    );
}


async function getApiErrorMessage(
    response: Response,
    fallback: string,
): Promise<string> {
    try {
        const body =
            await response.json() as {
                detail?: unknown;
                message?: unknown;
                error?: unknown;
            };

        if (
            typeof body.detail
            === "string"
        ) {
            return body.detail;
        }

        if (
            typeof body.message
            === "string"
        ) {
            return body.message;
        }

        if (
            typeof body.error
            === "string"
        ) {
            return body.error;
        }

        if (
            body.error
            && typeof body.error
            === "object"
        ) {
            const nestedError =
                body.error as {
                    message?: unknown;
                    detail?: unknown;
                };

            if (
                typeof nestedError.message
                === "string"
            ) {
                return nestedError.message;
            }

            if (
                typeof nestedError.detail
                === "string"
            ) {
                return nestedError.detail;
            }
        }
    } catch {
        // Use fallback below.
    }

    return fallback;
}


function formatDateTime(
    value: string | null,
): string {
    if (!value) {
        return "Not set";
    }

    const date =
        new Date(
            value,
        );

    if (
        Number.isNaN(
            date.getTime(),
        )
    ) {
        return value;
    }

    return date.toLocaleString(
        "en-GB",
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        },
    );
}


function statusLabel(
    status: ExtractionStatus,
): string {
    switch (status) {
        case "pending":
            return "Pending";
        case "processing":
            return "Processing";
        case "completed":
            return "Completed";
        case "failed":
            return "Failed";
        case "imported":
            return "Imported";
        case "superseded":
            return "Superseded";
        case "cancelled":
            return "Cancelled";
        default:
            return status;
    }
}


function reviewStatusLabel(
    status: ReviewStatus,
): string {
    switch (status) {
        case "unreviewed":
            return "Not reviewed";
        case "in_progress":
            return "Review in progress";
        case "reviewed":
            return "Review complete";
        default:
            return status;
    }
}


function extractionStatusClasses(
    status: ExtractionStatus,
): string {
    if (status === "imported") {
        return "bg-green-50 text-green-700";
    }

    if (status === "completed") {
        return "bg-blue-50 text-blue-700";
    }

    if (
        status === "failed"
        || status === "cancelled"
    ) {
        return "bg-red-50 text-red-700";
    }

    if (status === "superseded") {
        return "bg-slate-100 text-slate-600";
    }

    return "bg-amber-50 text-amber-700";
}


const QUESTION_TYPE_OPTIONS: Array<{
    value: QuestionType;
    label: string;
}> = [
        {
            value: "written",
            label: "Written response",
        },
        {
            value: "multiple_choice_single",
            label: "Multiple choice · one answer",
        },
        {
            value: "multiple_choice_multiple",
            label: "Multiple choice · multiple answers",
        },
        {
            value: "true_false",
            label: "True / false",
        },
        {
            value: "numeric",
            label: "Numeric response",
        },
        {
            value: "diagram_annotation",
            label: "Diagram annotation",
        },
        {
            value: "structural",
            label: "Structural / heading",
        },
    ];


const QUESTION_ASSET_TYPE_OPTIONS: Array<{
    value: QuestionAssetType;
    label: string;
}> = [
        {
            value: "image",
            label: "Image",
        },
        {
            value: "diagram",
            label: "Diagram",
        },
        {
            value: "graph",
            label: "Graph",
        },
        {
            value: "figure",
            label: "Figure",
        },
    ];


function questionTypeUsesOptions(
    questionType: QuestionType,
): boolean {
    return (
        questionType === "multiple_choice_single"
        || questionType === "multiple_choice_multiple"
        || questionType === "true_false"
    );
}


function createLocalOptionId(
    candidateIndex: number,
    optionIndex: number,
): string {
    return `candidate-${candidateIndex}-option-${optionIndex}-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2)}`;
}


function normaliseReviewOptions(
    candidateIndex: number,
    options: ExtractionOption[] | undefined,
): ReviewOptionState[] {
    return (options ?? [])
        .slice()
        .sort(
            (left, right) =>
                left.order - right.order,
        )
        .map(
            (
                option,
                optionIndex,
            ) => ({
                localId:
                    createLocalOptionId(
                        candidateIndex,
                        optionIndex,
                    ),
                text:
                    option.text
                    ?? "",
                order:
                    optionIndex + 1,
                isCorrect:
                    option.is_correct
                    ?? false,
                feedback:
                    option.feedback
                    ?? "",
            }),
        );
}


function normaliseReviewAssets(
    assets: ExtractionAsset[] | undefined,
): ReviewAssetState[] {
    return (assets ?? []).map(
        (
            asset,
            assetIndex,
        ) => ({
            assetIndex,
            assetType:
                asset.asset_type
                ?? "figure",
            altText:
                asset.alt_text
                ?? "",
            caption:
                asset.caption
                ?? "",
            order:
                asset.order
                ?? assetIndex + 1,
            candidateVisible:
                asset.candidate_visible
                ?? true,
            included:
                asset.included
                ?? true,
            reviewed:
                asset.reviewed
                ?? false,
            contentUrl:
                asset.content_url
                ?? null,
            originalFilename:
                asset.original_filename
                ?? null,
            mimeType:
                asset.mime_type
                ?? null,
            fileSizeBytes:
                asset.file_size_bytes
                ?? null,
            sourceDocumentId:
                asset.source_document_id
                ?? null,
            sourcePageNumber:
                asset.source_page_number
                ?? null,
            sourceBbox:
                asset.source_bbox
                ?? null,
        }),
    );
}


function buildReviewQuestions(
    extraction: ExtractionResponse,
): ReviewQuestionState[] {
    const questions =
        extraction.proposal_data?.questions
        ?? [];

    return questions.map(
        (
            question,
            candidateIndex,
        ) => ({
            candidateIndex,
            questionNumber:
                question.question_number,
            text:
                question.text
                ?? "",
            marks:
                question.marks === null
                    ? ""
                    : String(
                        question.marks,
                    ),
            parentQuestionNumber:
                question.parent_question_number
                ?? "",
            questionType:
                question.question_type
                ?? "written",
            options:
                normaliseReviewOptions(
                    candidateIndex,
                    question.options,
                ),
            assets:
                normaliseReviewAssets(
                    question.assets,
                ),
            included:
                question.included
                ?? true,
            reviewed:
                question.reviewed
                ?? false,
            source:
                question.source,
            confidence:
                question.confidence
                ?? "candidate",
        }),
    );
}


function buildReviewPayload(
    reviewQuestions: ReviewQuestionState[],
    reviewNotes: string,
    reviewStatus: ReviewStatus,
): ReviewPayload {
    return {
        review_status:
            reviewStatus,
        review_notes:
            reviewNotes.trim()
            || null,
        questions:
            reviewQuestions.map(
                question => ({
                    candidate_index:
                        question.candidateIndex,
                    question_number:
                        question.questionNumber,
                    text:
                        question.text,
                    marks:
                        question.marks.trim()
                            === ""
                            ? null
                            : Number(
                                question.marks,
                            ),
                    parent_question_number:
                        question
                            .parentQuestionNumber
                            .trim()
                        || null,
                    question_type:
                        question.questionType,
                    options:
                        question.options.map(
                            (
                                option,
                                optionIndex,
                            ) => ({
                                text:
                                    option.text,
                                order:
                                    optionIndex + 1,
                                is_correct:
                                    option.isCorrect,
                                feedback:
                                    option.feedback.trim()
                                    || null,
                            }),
                        ),
                    assets:
                        question.assets.map(
                            asset => ({
                                asset_index:
                                    asset.assetIndex,
                                asset_type:
                                    asset.assetType,
                                alt_text:
                                    asset.altText.trim()
                                    || null,
                                caption:
                                    asset.caption.trim()
                                    || null,
                                order:
                                    asset.order,
                                candidate_visible:
                                    asset.candidateVisible,
                                included:
                                    asset.included,
                                reviewed:
                                    asset.reviewed,
                            }),
                        ),
                    included:
                        question.included,
                    reviewed:
                        question.reviewed,
                }),
            ),
    };
}


function reviewFingerprint(
    reviewQuestions: ReviewQuestionState[],
    reviewNotes: string,
): string {
    const payload =
        buildReviewPayload(
            reviewQuestions,
            reviewNotes,
            "in_progress",
        );

    return JSON.stringify({
        review_notes:
            payload.review_notes,
        questions:
            payload.questions,
    });
}


function resolveExtractionAssetContentUrl(
    contentUrl: string,
): string {
    if (
        /^https?:\/\//i.test(
            contentUrl,
        )
    ) {
        return contentUrl;
    }

    const normalisedBase =
        API_BASE_URL.replace(
            /\/+$/,
            "",
        );

    const apiPrefix =
        "/api/v1";

    if (
        contentUrl.startsWith(
            `${apiPrefix}/`,
        )
        && normalisedBase.endsWith(
            apiPrefix,
        )
    ) {
        return `${normalisedBase.slice(
            0,
            -apiPrefix.length,
        )}${contentUrl}`;
    }

    if (
        contentUrl.startsWith(
            "/",
        )
    ) {
        return contentUrl;
    }

    return `${normalisedBase}/${contentUrl.replace(
        /^\/+/,
        "",
    )}`;
}


type SecureExtractionAssetPreviewProps = {
    contentUrl: string | null;
    altText: string;
    caption: string;
    mimeType: string | null;
};


function SecureExtractionAssetPreview({
    contentUrl,
    altText,
    caption,
    mimeType,
}: SecureExtractionAssetPreviewProps) {
    const [objectUrl, setObjectUrl] =
        useState<string | null>(
            null,
        );

    const [isLoading, setIsLoading] =
        useState(
            false,
        );

    const [previewError, setPreviewError] =
        useState<string | null>(
            null,
        );

    useEffect(
        () => {
            const controller =
                new AbortController();

            let objectUrlToRevoke:
                string | null =
                null;

            setObjectUrl(
                null,
            );

            setPreviewError(
                null,
            );

            if (!contentUrl) {
                setIsLoading(
                    false,
                );

                return () => {
                    controller.abort();
                };
            }

            const token =
                getAuthToken();

            if (!token) {
                setIsLoading(
                    false,
                );

                setPreviewError(
                    "Your session has expired. Please sign in again to view this visual.",
                );

                return () => {
                    controller.abort();
                };
            }

            const loadPreview =
                async () => {
                    try {
                        setIsLoading(
                            true,
                        );

                        const response =
                            await fetch(
                                resolveExtractionAssetContentUrl(
                                    contentUrl,
                                ),
                                {
                                    headers: {
                                        Authorization:
                                            `Bearer ${token}`,
                                    },
                                    signal:
                                        controller.signal,
                                },
                            );

                        if (!response.ok) {
                            throw new Error(
                                await getApiErrorMessage(
                                    response,
                                    "Failed to load the extracted visual.",
                                ),
                            );
                        }

                        const blob =
                            await response.blob();

                        if (
                            controller.signal.aborted
                        ) {
                            return;
                        }

                        const nextObjectUrl =
                            URL.createObjectURL(
                                blob,
                            );

                        objectUrlToRevoke =
                            nextObjectUrl;

                        setObjectUrl(
                            nextObjectUrl,
                        );
                    } catch (err: unknown) {
                        if (
                            controller.signal.aborted
                        ) {
                            return;
                        }

                        setPreviewError(
                            err instanceof Error
                                ? err.message
                                : "Failed to load the extracted visual.",
                        );
                    } finally {
                        if (
                            !controller.signal.aborted
                        ) {
                            setIsLoading(
                                false,
                            );
                        }
                    }
                };

            void loadPreview();

            return () => {
                controller.abort();

                if (
                    objectUrlToRevoke
                ) {
                    URL.revokeObjectURL(
                        objectUrlToRevoke,
                    );
                }
            };
        },
        [
            contentUrl,
        ],
    );

    if (!contentUrl) {
        return (
            <div className="mb-4 rounded-lg border border-dashed border-amber-300 bg-amber-50 p-4 text-sm font-medium text-amber-800">
                This extracted visual does not currently have a secure preview URL.
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="mb-4 flex min-h-40 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-4 text-sm font-medium text-slate-500">
                Loading extracted visual...
            </div>
        );
    }

    if (previewError) {
        return (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                {previewError}
            </div>
        );
    }

    if (!objectUrl) {
        return null;
    }

    const accessibleAltText =
        altText.trim()
        || caption.trim()
        || "Extracted visual asset";

    return (
        <figure className="mb-4 overflow-hidden rounded-lg border border-slate-200 bg-white">
            <div className="flex min-h-40 items-center justify-center p-3">
                <img
                    src={
                        objectUrl
                    }
                    alt={
                        accessibleAltText
                    }
                    className="max-h-[32rem] w-full object-contain"
                />
            </div>

            {(caption.trim() || mimeType) && (
                <figcaption className="border-t border-slate-200 px-3 py-2 text-xs text-slate-500">
                    {caption.trim() && (
                        <span>
                            {caption.trim()}
                        </span>
                    )}

                    {caption.trim() && mimeType && (
                        <span aria-hidden="true">
                            {" · "}
                        </span>
                    )}

                    {mimeType && (
                        <span>
                            {mimeType}
                        </span>
                    )}
                </figcaption>
            )}
        </figure>
    );
}


export default function AssessmentQuestionExtractionPanel({
    assessmentId,
    questionPaper,
    isDraft,
    onImported,
}: Props) {
    const [history, setHistory] =
        useState<ExtractionSummaryResponse[]>(
            [],
        );

    const [extraction, setExtraction] =
        useState<ExtractionResponse | null>(
            null,
        );

    const [reviewQuestions, setReviewQuestions] =
        useState<ReviewQuestionState[]>(
            [],
        );

    const [reviewNotes, setReviewNotes] =
        useState(
            "",
        );

    const [reviewSaveState, setReviewSaveState] =
        useState<ReviewSaveState>(
            "saved",
        );

    const [reviewSaveError, setReviewSaveError] =
        useState<string | null>(
            null,
        );

    const [lastReviewSavedAt, setLastReviewSavedAt] =
        useState<Date | null>(
            null,
        );

    const [autosaveRetryNonce, setAutosaveRetryNonce] =
        useState(
            0,
        );

    const reviewFormRef =
        useRef<{
            reviewQuestions: ReviewQuestionState[];
            reviewNotes: string;
        }>({
            reviewQuestions: [],
            reviewNotes: "",
        });

    const lastSavedFingerprintRef =
        useRef(
            "",
        );

    const autosaveTimerRef =
        useRef<ReturnType<typeof setTimeout> | null>(
            null,
        );

    const autosaveInFlightRef =
        useRef(
            false,
        );

    const [action, setAction] =
        useState<ExtractionAction>(
            null,
        );

    const [error, setError] =
        useState<string | null>(
            null,
        );

    const [message, setMessage] =
        useState<string | null>(
            null,
        );

    const [importResult, setImportResult] =
        useState<ImportResponse | null>(
            null,
        );


    const proposal =
        extraction?.proposal_data
        ?? null;


    const includedQuestions =
        useMemo(
            () =>
                reviewQuestions.filter(
                    question =>
                        question.included,
                ),
            [
                reviewQuestions,
            ],
        );


    const includedMarkTotal =
        useMemo(
            () =>
                includedQuestions.reduce(
                    (
                        total,
                        question,
                    ) => {
                        const value =
                            Number(
                                question.marks,
                            );

                        if (
                            question.marks.trim()
                            === ""
                            || !Number.isFinite(
                                value,
                            )
                        ) {
                            return total;
                        }

                        return total + value;
                    },
                    0,
                ),
            [
                includedQuestions,
            ],
        );


    const missingMarkCount =
        useMemo(
            () =>
                includedQuestions.filter(
                    question =>
                        question.marks.trim()
                        === "",
                ).length,
            [
                includedQuestions,
            ],
        );


    const unreviewedIncludedCount =
        useMemo(
            () =>
                includedQuestions.filter(
                    question =>
                        !question.reviewed,
                ).length,
            [
                includedQuestions,
            ],
        );


    const isImported =
        extraction?.status === "imported";


    const isReviewComplete =
        proposal?.review_status === "reviewed"
        && proposal.review_required === false;


    const canEditReview =
        isDraft
        && extraction?.status === "completed";


    const canImport =
        isDraft
        && extraction?.status === "completed"
        && isReviewComplete
        && missingMarkCount === 0
        && unreviewedIncludedCount === 0
        && includedQuestions.length > 0
        && reviewSaveState === "saved";


    const hydrateExtraction =
        useCallback(
            (
                nextExtraction: ExtractionResponse,
            ) => {
                const nextReviewQuestions =
                    buildReviewQuestions(
                        nextExtraction,
                    );

                const nextReviewNotes =
                    nextExtraction
                        .proposal_data
                        ?.review_notes
                    ?? "";

                reviewFormRef.current = {
                    reviewQuestions:
                        nextReviewQuestions,
                    reviewNotes:
                        nextReviewNotes,
                };

                lastSavedFingerprintRef.current =
                    reviewFingerprint(
                        nextReviewQuestions,
                        nextReviewNotes,
                    );

                setExtraction(
                    nextExtraction,
                );

                setReviewQuestions(
                    nextReviewQuestions,
                );

                setReviewNotes(
                    nextReviewNotes,
                );

                setReviewSaveState(
                    "saved",
                );

                setReviewSaveError(
                    null,
                );

                if (
                    nextExtraction.status
                    === "imported"
                ) {
                    setImportResult(
                        null,
                    );
                }
            },
            [],
        );


    const fetchExtraction =
        useCallback(
            async (
                extractionId: number,
            ): Promise<ExtractionResponse> => {
                const token =
                    getAuthToken();

                if (!token) {
                    throw new Error(
                        "Your session has expired. Please sign in again.",
                    );
                }

                const response =
                    await fetch(
                        `${API_BASE_URL}/assessments/${assessmentId}/question-extractions/${extractionId}`,
                        {
                            headers: {
                                Authorization:
                                    `Bearer ${token}`,
                            },
                        },
                    );

                if (!response.ok) {
                    throw new Error(
                        await getApiErrorMessage(
                            response,
                            "Failed to load the question extraction.",
                        ),
                    );
                }

                return await response.json() as ExtractionResponse;
            },
            [
                assessmentId,
            ],
        );


    const loadExtractionHistory =
        useCallback(
            async () => {
                const token =
                    getAuthToken();

                if (!token) {
                    setError(
                        "Your session has expired. Please sign in again.",
                    );
                    return;
                }

                try {
                    setAction(
                        "load",
                    );

                    setError(
                        null,
                    );

                    const response =
                        await fetch(
                            `${API_BASE_URL}/assessments/${assessmentId}/documents/${questionPaper.id}/question-extractions`,
                            {
                                headers: {
                                    Authorization:
                                        `Bearer ${token}`,
                                },
                            },
                        );

                    if (!response.ok) {
                        throw new Error(
                            await getApiErrorMessage(
                                response,
                                "Failed to load question extraction history.",
                            ),
                        );
                    }

                    const data =
                        await response.json() as ExtractionHistoryResponse;

                    setHistory(
                        data.extractions,
                    );

                    const latest =
                        data.extractions[0];

                    if (!latest) {
                        setExtraction(
                            null,
                        );

                        setReviewQuestions(
                            [],
                        );

                        setReviewNotes(
                            "",
                        );

                        return;
                    }

                    const fullExtraction =
                        await fetchExtraction(
                            latest.id,
                        );

                    hydrateExtraction(
                        fullExtraction,
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load question extraction history.",
                    );
                } finally {
                    setAction(
                        null,
                    );
                }
            },
            [
                assessmentId,
                fetchExtraction,
                hydrateExtraction,
                questionPaper.id,
            ],
        );


    useEffect(
        () => {
            void loadExtractionHistory();
        },
        [
            loadExtractionHistory,
        ],
    );


    useEffect(
        () => {
            reviewFormRef.current = {
                reviewQuestions,
                reviewNotes,
            };
        },
        [
            reviewNotes,
            reviewQuestions,
        ],
    );


    const handleExtract =
        useCallback(
            async () => {
                if (
                    !isDraft
                    || action !== null
                    || reviewSaveState !== "saved"
                ) {
                    return;
                }

                const token =
                    getAuthToken();

                if (!token) {
                    setError(
                        "Your session has expired. Please sign in again.",
                    );
                    return;
                }

                const hasExistingExtraction =
                    history.length > 0;

                if (hasExistingExtraction) {
                    const confirmed =
                        window.confirm(
                            "Run extraction again? The existing proposal will remain in history and the new completed extraction will become the active proposal.",
                        );

                    if (!confirmed) {
                        return;
                    }
                }

                try {
                    setAction(
                        "extract",
                    );

                    setError(
                        null,
                    );

                    setMessage(
                        null,
                    );

                    setImportResult(
                        null,
                    );

                    const response =
                        await fetch(
                            `${API_BASE_URL}/assessments/${assessmentId}/documents/${questionPaper.id}/question-extractions`,
                            {
                                method: "POST",
                                headers: {
                                    Authorization:
                                        `Bearer ${token}`,
                                },
                            },
                        );

                    if (!response.ok) {
                        throw new Error(
                            await getApiErrorMessage(
                                response,
                                "Failed to extract questions from the question paper.",
                            ),
                        );
                    }

                    const created =
                        await response.json() as ExtractionResponse & {
                            message?: string;
                        };

                    hydrateExtraction(
                        created,
                    );

                    setMessage(
                        created.message
                        ?? "Question-paper extraction completed.",
                    );

                    await loadExtractionHistory();
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to extract questions from the question paper.",
                    );
                } finally {
                    setAction(
                        null,
                    );
                }
            },
            [
                action,
                assessmentId,
                history.length,
                hydrateExtraction,
                isDraft,
                loadExtractionHistory,
                questionPaper.id,
                reviewSaveState,
            ],
        );


    const updateReviewQuestion =
        useCallback(
            (
                candidateIndex: number,
                update:
                    Partial<ReviewQuestionState>,
            ) => {
                setReviewQuestions(
                    current =>
                        current.map(
                            question =>
                                question.candidateIndex
                                    === candidateIndex
                                    ? {
                                        ...question,
                                        ...update,
                                    }
                                    : question,
                        ),
                );
            },
            [],
        );


    const setReviewQuestionType =
        useCallback(
            (
                candidateIndex: number,
                questionType: QuestionType,
            ) => {
                setReviewQuestions(
                    current =>
                        current.map(
                            question => {
                                if (
                                    question.candidateIndex
                                    !== candidateIndex
                                ) {
                                    return question;
                                }

                                if (
                                    questionType
                                    === "true_false"
                                ) {
                                    const existingCorrectIndex =
                                        question.options.findIndex(
                                            option =>
                                                option.isCorrect,
                                        );

                                    const correctIndex =
                                        existingCorrectIndex >= 0
                                            ? Math.min(
                                                existingCorrectIndex,
                                                1,
                                            )
                                            : 0;

                                    return {
                                        ...question,
                                        questionType,
                                        options: [
                                            {
                                                localId:
                                                    createLocalOptionId(
                                                        candidateIndex,
                                                        0,
                                                    ),
                                                text: "True",
                                                order: 1,
                                                isCorrect:
                                                    correctIndex === 0,
                                                feedback: "",
                                            },
                                            {
                                                localId:
                                                    createLocalOptionId(
                                                        candidateIndex,
                                                        1,
                                                    ),
                                                text: "False",
                                                order: 2,
                                                isCorrect:
                                                    correctIndex === 1,
                                                feedback: "",
                                            },
                                        ],
                                    };
                                }

                                if (
                                    questionTypeUsesOptions(
                                        questionType,
                                    )
                                ) {
                                    return {
                                        ...question,
                                        questionType,
                                        options:
                                            question.options.length >= 2
                                                ? question.options
                                                : [
                                                    ...question.options,
                                                    ...Array.from(
                                                        {
                                                            length:
                                                                2
                                                                - question.options.length,
                                                        },
                                                        (
                                                            _,
                                                            optionIndex,
                                                        ) => ({
                                                            localId:
                                                                createLocalOptionId(
                                                                    candidateIndex,
                                                                    question.options.length
                                                                    + optionIndex,
                                                                ),
                                                            text: "",
                                                            order:
                                                                question.options.length
                                                                + optionIndex
                                                                + 1,
                                                            isCorrect: false,
                                                            feedback: "",
                                                        }),
                                                    ),
                                                ],
                                    };
                                }

                                return {
                                    ...question,
                                    questionType,
                                    options: [],
                                };
                            },
                        ),
                );
            },
            [],
        );


    const addReviewOption =
        useCallback(
            (
                candidateIndex: number,
            ) => {
                setReviewQuestions(
                    current =>
                        current.map(
                            question =>
                                question.candidateIndex
                                    === candidateIndex
                                    ? {
                                        ...question,
                                        options: [
                                            ...question.options,
                                            {
                                                localId:
                                                    createLocalOptionId(
                                                        candidateIndex,
                                                        question.options.length,
                                                    ),
                                                text: "",
                                                order:
                                                    question.options.length + 1,
                                                isCorrect: false,
                                                feedback: "",
                                            },
                                        ],
                                    }
                                    : question,
                        ),
                );
            },
            [],
        );


    const updateReviewOption =
        useCallback(
            (
                candidateIndex: number,
                localId: string,
                update: Partial<ReviewOptionState>,
            ) => {
                setReviewQuestions(
                    current =>
                        current.map(
                            question => {
                                if (
                                    question.candidateIndex
                                    !== candidateIndex
                                ) {
                                    return question;
                                }

                                const nextOptions =
                                    question.options.map(
                                        option =>
                                            option.localId === localId
                                                ? {
                                                    ...option,
                                                    ...update,
                                                }
                                                : option,
                                    );

                                if (
                                    "isCorrect" in update
                                    && update.isCorrect
                                    && (
                                        question.questionType
                                        === "multiple_choice_single"
                                        || question.questionType
                                        === "true_false"
                                    )
                                ) {
                                    return {
                                        ...question,
                                        options:
                                            nextOptions.map(
                                                option => ({
                                                    ...option,
                                                    isCorrect:
                                                        option.localId
                                                        === localId,
                                                }),
                                            ),
                                    };
                                }

                                return {
                                    ...question,
                                    options: nextOptions,
                                };
                            },
                        ),
                );
            },
            [],
        );


    const removeReviewOption =
        useCallback(
            (
                candidateIndex: number,
                localId: string,
            ) => {
                setReviewQuestions(
                    current =>
                        current.map(
                            question => {
                                if (
                                    question.candidateIndex
                                    !== candidateIndex
                                ) {
                                    return question;
                                }

                                return {
                                    ...question,
                                    options:
                                        question.options
                                            .filter(
                                                option =>
                                                    option.localId
                                                    !== localId,
                                            )
                                            .map(
                                                (
                                                    option,
                                                    optionIndex,
                                                ) => ({
                                                    ...option,
                                                    order:
                                                        optionIndex + 1,
                                                }),
                                            ),
                                };
                            },
                        ),
                );
            },
            [],
        );


    const moveReviewOption =
        useCallback(
            (
                candidateIndex: number,
                localId: string,
                direction: -1 | 1,
            ) => {
                setReviewQuestions(
                    current =>
                        current.map(
                            question => {
                                if (
                                    question.candidateIndex
                                    !== candidateIndex
                                ) {
                                    return question;
                                }

                                const currentIndex =
                                    question.options.findIndex(
                                        option =>
                                            option.localId
                                            === localId,
                                    );

                                const targetIndex =
                                    currentIndex + direction;

                                if (
                                    currentIndex < 0
                                    || targetIndex < 0
                                    || targetIndex
                                    >= question.options.length
                                ) {
                                    return question;
                                }

                                const nextOptions = [
                                    ...question.options,
                                ];

                                const [
                                    movedOption,
                                ] =
                                    nextOptions.splice(
                                        currentIndex,
                                        1,
                                    );

                                nextOptions.splice(
                                    targetIndex,
                                    0,
                                    movedOption,
                                );

                                return {
                                    ...question,
                                    options:
                                        nextOptions.map(
                                            (
                                                option,
                                                optionIndex,
                                            ) => ({
                                                ...option,
                                                order:
                                                    optionIndex + 1,
                                            }),
                                        ),
                                };
                            },
                        ),
                );
            },
            [],
        );


    const updateReviewAsset =
        useCallback(
            (
                candidateIndex: number,
                assetIndex: number,
                update: Partial<ReviewAssetState>,
            ) => {
                setReviewQuestions(
                    current =>
                        current.map(
                            question =>
                                question.candidateIndex
                                    === candidateIndex
                                    ? {
                                        ...question,
                                        assets:
                                            question.assets.map(
                                                asset =>
                                                    asset.assetIndex
                                                        === assetIndex
                                                        ? {
                                                            ...asset,
                                                            ...update,
                                                        }
                                                        : asset,
                                            ),
                                    }
                                    : question,
                        ),
                );
            },
            [],
        );


    const validateReview =
        useCallback(
            (
                targetStatus: ReviewStatus,
            ): string | null => {
                if (
                    reviewQuestions.length === 0
                ) {
                    return "The extraction proposal does not contain any questions.";
                }

                const included =
                    reviewQuestions.filter(
                        question =>
                            question.included,
                    );

                if (included.length === 0) {
                    return "Include at least one question before completing the review.";
                }

                const seen =
                    new Set<string>();

                for (const question of included) {
                    const questionNumber =
                        question.questionNumber
                            .replace(
                                /\s+/g,
                                "",
                            );

                    if (!questionNumber) {
                        return "Every included question must have a question number.";
                    }

                    if (
                        questionNumber.length
                        > 100
                    ) {
                        return "Question numbers cannot exceed 100 characters during review.";
                    }

                    if (
                        seen.has(
                            questionNumber,
                        )
                    ) {
                        return `Question number ${questionNumber} is duplicated.`;
                    }

                    seen.add(
                        questionNumber,
                    );

                    if (
                        question.marks.trim()
                        !== ""
                    ) {
                        const marks =
                            Number(
                                question.marks,
                            );

                        if (
                            !Number.isInteger(
                                marks,
                            )
                            || marks < 0
                            || marks > 10_000
                        ) {
                            return `Marks for question ${questionNumber} must be a whole number from 0 to 10000.`;
                        }
                    }

                    if (
                        targetStatus
                        === "reviewed"
                    ) {
                        if (
                            question.marks.trim()
                            === ""
                        ) {
                            return `Question ${questionNumber} needs a mark allocation before review can be completed.`;
                        }

                        if (!question.reviewed) {
                            return `Question ${questionNumber} must be marked as reviewed before the proposal can be completed.`;
                        }

                        if (
                            question.questionType
                            === "structural"
                            && Number(
                                question.marks,
                            ) !== 0
                        ) {
                            return `Structural question ${questionNumber} must have 0 marks.`;
                        }

                        if (
                            questionTypeUsesOptions(
                                question.questionType,
                            )
                        ) {
                            if (
                                question.options.length < 2
                            ) {
                                return `Question ${questionNumber} needs at least two answer options.`;
                            }

                            const blankOption =
                                question.options.some(
                                    option =>
                                        option.text.trim()
                                        === "",
                                );

                            if (blankOption) {
                                return `Every option for question ${questionNumber} must contain text.`;
                            }

                            const correctCount =
                                question.options.filter(
                                    option =>
                                        option.isCorrect,
                                ).length;

                            if (
                                (
                                    question.questionType
                                    === "multiple_choice_single"
                                    || question.questionType
                                    === "true_false"
                                )
                                && correctCount !== 1
                            ) {
                                return `Question ${questionNumber} needs exactly one correct answer.`;
                            }

                            if (
                                question.questionType
                                === "multiple_choice_multiple"
                                && correctCount < 1
                            ) {
                                return `Question ${questionNumber} needs at least one correct answer.`;
                            }

                            if (
                                question.questionType
                                === "true_false"
                                && question.options.length !== 2
                            ) {
                                return `True/false question ${questionNumber} must have exactly two options.`;
                            }
                        }

                        const unreviewedAsset =
                            question.assets.find(
                                asset =>
                                    asset.included
                                    && !asset.reviewed,
                            );

                        if (unreviewedAsset) {
                            return `Every included visual asset for question ${questionNumber} must be reviewed before completion.`;
                        }
                    }
                }

                return null;
            },
            [
                reviewQuestions,
            ],
        );


    const persistReview =
        useCallback(
            async (
                targetStatus: ReviewStatus,
                mode: "manual" | "autosave",
            ) => {
                if (
                    !extraction
                    || !canEditReview
                ) {
                    return;
                }

                if (
                    mode === "manual"
                    && action !== null
                ) {
                    return;
                }

                if (
                    mode === "autosave"
                    && (
                        autosaveInFlightRef.current
                        || action !== null
                    )
                ) {
                    return;
                }

                const currentForm =
                    reviewFormRef.current;

                const validationError =
                    validateReview(
                        targetStatus,
                    );

                if (validationError) {
                    if (
                        mode === "autosave"
                    ) {
                        setReviewSaveState(
                            "dirty",
                        );

                        setReviewSaveError(
                            `Autosave paused: ${validationError}`,
                        );

                        return;
                    }

                    setError(
                        validationError,
                    );
                    return;
                }

                const token =
                    getAuthToken();

                if (!token) {
                    if (
                        mode === "autosave"
                    ) {
                        setReviewSaveState(
                            "error",
                        );

                        setReviewSaveError(
                            "Autosave failed because your session has expired.",
                        );

                        return;
                    }

                    setError(
                        "Your session has expired. Please sign in again.",
                    );
                    return;
                }

                if (
                    mode === "manual"
                    && autosaveTimerRef.current
                ) {
                    clearTimeout(
                        autosaveTimerRef.current,
                    );

                    autosaveTimerRef.current =
                        null;
                }

                const payload =
                    buildReviewPayload(
                        currentForm.reviewQuestions,
                        currentForm.reviewNotes,
                        targetStatus,
                    );

                const submittedFingerprint =
                    reviewFingerprint(
                        currentForm.reviewQuestions,
                        currentForm.reviewNotes,
                    );

                try {
                    if (
                        mode === "autosave"
                    ) {
                        autosaveInFlightRef.current =
                            true;

                        setReviewSaveState(
                            "saving",
                        );
                    } else {
                        setAction(
                            targetStatus === "reviewed"
                                ? "complete-review"
                                : "save-review",
                        );
                    }

                    setReviewSaveError(
                        null,
                    );

                    setError(
                        null,
                    );

                    if (
                        mode === "manual"
                    ) {
                        setMessage(
                            null,
                        );
                    }

                    const response =
                        await fetch(
                            `${API_BASE_URL}/assessments/${assessmentId}/question-extractions/${extraction.id}/review`,
                            {
                                method: "PATCH",
                                headers: {
                                    Authorization:
                                        `Bearer ${token}`,
                                    "Content-Type":
                                        "application/json",
                                },
                                body:
                                    JSON.stringify(
                                        payload,
                                    ),
                            },
                        );

                    if (!response.ok) {
                        throw new Error(
                            await getApiErrorMessage(
                                response,
                                "Failed to save the extraction review.",
                            ),
                        );
                    }

                    const updated =
                        await response.json() as ExtractionResponse & {
                            message?: string;
                        };

                    lastSavedFingerprintRef.current =
                        submittedFingerprint;

                    setLastReviewSavedAt(
                        new Date(),
                    );

                    const latestForm =
                        reviewFormRef.current;

                    const latestFingerprint =
                        reviewFingerprint(
                            latestForm.reviewQuestions,
                            latestForm.reviewNotes,
                        );

                    if (
                        latestFingerprint
                        === submittedFingerprint
                    ) {
                        hydrateExtraction(
                            updated,
                        );

                        setLastReviewSavedAt(
                            new Date(),
                        );
                    } else {
                        /*
                         * The teacher kept typing while this autosave was
                         * in flight. Keep those newer local edits intact,
                         * but update extraction metadata from the response.
                         */
                        setExtraction(
                            updated,
                        );

                        setReviewSaveState(
                            "dirty",
                        );
                    }

                    if (
                        mode === "manual"
                    ) {
                        setMessage(
                            targetStatus === "reviewed"
                                ? "Question extraction review completed."
                                : updated.message
                                ?? "Question extraction review saved.",
                        );
                    }
                } catch (err: unknown) {
                    const saveError =
                        err instanceof Error
                            ? err.message
                            : "Failed to save the extraction review.";

                    if (
                        mode === "autosave"
                    ) {
                        setReviewSaveState(
                            "error",
                        );

                        setReviewSaveError(
                            saveError,
                        );
                    } else {
                        setError(
                            saveError,
                        );
                    }
                } finally {
                    if (
                        mode === "autosave"
                    ) {
                        autosaveInFlightRef.current =
                            false;

                        const latestForm =
                            reviewFormRef.current;

                        const latestFingerprint =
                            reviewFingerprint(
                                latestForm.reviewQuestions,
                                latestForm.reviewNotes,
                            );

                        if (
                            latestFingerprint
                            !== lastSavedFingerprintRef.current
                        ) {
                            setReviewSaveState(
                                "dirty",
                            );

                            setAutosaveRetryNonce(
                                current =>
                                    current + 1,
                            );
                        }
                    } else {
                        setAction(
                            null,
                        );
                    }
                }
            },
            [
                action,
                assessmentId,
                canEditReview,
                extraction,
                hydrateExtraction,
                validateReview,
            ],
        );


    const saveReview =
        useCallback(
            async (
                targetStatus: ReviewStatus,
            ) => {
                await persistReview(
                    targetStatus,
                    "manual",
                );
            },
            [
                persistReview,
            ],
        );


    useEffect(
        () => {
            if (
                !canEditReview
                || !extraction
                || action !== null
            ) {
                return;
            }

            const currentFingerprint =
                reviewFingerprint(
                    reviewQuestions,
                    reviewNotes,
                );

            if (
                currentFingerprint
                === lastSavedFingerprintRef.current
            ) {
                if (
                    reviewSaveState !== "saving"
                ) {
                    setReviewSaveState(
                        "saved",
                    );

                    setReviewSaveError(
                        null,
                    );
                }

                return;
            }

            setReviewSaveState(
                current =>
                    current === "saving"
                        ? current
                        : "dirty",
            );

            if (
                autosaveTimerRef.current
            ) {
                clearTimeout(
                    autosaveTimerRef.current,
                );
            }

            autosaveTimerRef.current =
                setTimeout(
                    () => {
                        void persistReview(
                            "in_progress",
                            "autosave",
                        );
                    },
                    1000,
                );

            return () => {
                if (
                    autosaveTimerRef.current
                ) {
                    clearTimeout(
                        autosaveTimerRef.current,
                    );

                    autosaveTimerRef.current =
                        null;
                }
            };
        },
        [
            action,
            autosaveRetryNonce,
            canEditReview,
            extraction,
            persistReview,
            reviewNotes,
            reviewQuestions,
            reviewSaveState,
        ],
    );


    useEffect(
        () => {
            if (
                reviewSaveState !== "dirty"
                && reviewSaveState !== "saving"
            ) {
                return;
            }

            const handleBeforeUnload =
                (
                    event: BeforeUnloadEvent,
                ) => {
                    event.preventDefault();
                    event.returnValue = "";
                };

            window.addEventListener(
                "beforeunload",
                handleBeforeUnload,
            );

            return () => {
                window.removeEventListener(
                    "beforeunload",
                    handleBeforeUnload,
                );
            };
        },
        [
            reviewSaveState,
        ],
    );


    const handleImport =
        useCallback(
            async () => {
                if (
                    !extraction
                    || !canImport
                    || action !== null
                ) {
                    return;
                }

                const confirmed =
                    window.confirm(
                        `Import ${includedQuestions.length} reviewed question${includedQuestions.length === 1 ? "" : "s"} into this assessment? Missing structural parents will be created automatically. This proposal cannot be imported twice.`,
                    );

                if (!confirmed) {
                    return;
                }

                const token =
                    getAuthToken();

                if (!token) {
                    setError(
                        "Your session has expired. Please sign in again.",
                    );
                    return;
                }

                try {
                    setAction(
                        "import",
                    );

                    setError(
                        null,
                    );

                    setMessage(
                        null,
                    );

                    const response =
                        await fetch(
                            `${API_BASE_URL}/assessments/${assessmentId}/question-extractions/${extraction.id}/import`,
                            {
                                method: "POST",
                                headers: {
                                    Authorization:
                                        `Bearer ${token}`,
                                },
                            },
                        );

                    if (!response.ok) {
                        throw new Error(
                            await getApiErrorMessage(
                                response,
                                "Failed to import reviewed questions.",
                            ),
                        );
                    }

                    const imported =
                        await response.json() as ImportResponse;

                    setImportResult(
                        imported,
                    );

                    hydrateExtraction(
                        imported,
                    );

                    setMessage(
                        imported.message
                        ?? "Reviewed question extraction imported.",
                    );

                    await loadExtractionHistory();

                    if (onImported) {
                        await onImported();
                    }
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to import reviewed questions.",
                    );
                } finally {
                    setAction(
                        null,
                    );
                }
            },
            [
                action,
                assessmentId,
                canImport,
                extraction,
                hydrateExtraction,
                includedQuestions.length,
                loadExtractionHistory,
                onImported,
            ],
        );


    return (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <h2 className="text-2xl font-extrabold text-slate-900">
                        Question extraction
                    </h2>

                    <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                        Detect question structure from the uploaded PDF,
                        review every proposed question, then explicitly import
                        the approved structure into the assessment.
                    </p>
                </div>

                {extraction && (
                    <div className="flex flex-wrap gap-2">
                        <span
                            className={`rounded-full px-3 py-1 text-xs font-bold ${extractionStatusClasses(
                                extraction.status,
                            )}`}
                        >
                            {statusLabel(
                                extraction.status,
                            )}
                        </span>

                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                            Extraction v
                            {extraction.version}
                        </span>

                        {proposal && (
                            <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-bold text-violet-700">
                                {reviewStatusLabel(
                                    proposal.review_status,
                                )}
                            </span>
                        )}
                    </div>
                )}
            </div>

            {error && (
                <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                    {error}
                </div>
            )}

            {message && (
                <div className="mt-5 rounded-xl border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-700">
                    {message}
                </div>
            )}

            {action === "load" && !extraction && (
                <div className="mt-5 rounded-xl border border-dashed border-slate-300 p-5 text-sm text-slate-500">
                    Loading question extraction history...
                </div>
            )}

            {!extraction && action !== "load" && (
                <div className="mt-5 rounded-xl border border-dashed border-slate-300 p-5">
                    <p className="font-semibold text-slate-800">
                        No extraction has been created for this question paper.
                    </p>

                    <p className="mt-1 text-sm leading-6 text-slate-600">
                        Extraction creates a reviewable proposal only.
                        It does not add live assessment questions until you
                        complete the review and explicitly import them.
                    </p>

                    <button
                        type="button"
                        onClick={() =>
                            void handleExtract()
                        }
                        disabled={
                            !isDraft
                            || action !== null
                        }
                        className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {action === "extract"
                            ? "Extracting..."
                            : "Extract questions"}
                    </button>

                    {!isDraft && (
                        <p className="mt-3 text-xs font-medium text-amber-700">
                            Question extraction changes are available only
                            while the assessment is in draft.
                        </p>
                    )}
                </div>
            )}

            {extraction && (
                <>
                    <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                Pages
                            </p>

                            <p className="mt-1 text-xl font-extrabold text-slate-900">
                                {extraction.page_count
                                    ?? "—"}
                            </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                Text pages
                            </p>

                            <p className="mt-1 text-xl font-extrabold text-slate-900">
                                {extraction.text_page_count
                                    ?? "—"}
                            </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                Detected
                            </p>

                            <p className="mt-1 text-xl font-extrabold text-slate-900">
                                {extraction.detected_question_count
                                    ?? "—"}
                            </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                Included
                            </p>

                            <p className="mt-1 text-xl font-extrabold text-slate-900">
                                {includedQuestions.length}
                            </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                Included marks
                            </p>

                            <p className="mt-1 text-xl font-extrabold text-slate-900">
                                {includedMarkTotal}
                            </p>
                        </div>
                    </div>

                    {extraction.error_message && (
                        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4">
                            <p className="text-sm font-bold text-red-800">
                                Extraction failed
                            </p>

                            <p className="mt-1 text-sm text-red-700">
                                {extraction.error_message}
                            </p>
                        </div>
                    )}

                    {extraction.status === "superseded" && (
                        <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                            This extraction has been superseded by a newer
                            completed extraction and is retained for history.
                        </div>
                    )}

                    {history.length > 1 && (
                        <div className="mt-5 rounded-xl border border-slate-200 p-4">
                            <p className="text-sm font-bold text-slate-800">
                                Extraction history
                            </p>

                            <div className="mt-3 flex flex-wrap gap-2">
                                {history.map(
                                    item => (
                                        <button
                                            key={
                                                item.id
                                            }
                                            type="button"
                                            onClick={() => {
                                                void (
                                                    async () => {
                                                        try {
                                                            setAction(
                                                                "load",
                                                            );

                                                            setError(
                                                                null,
                                                            );

                                                            const full =
                                                                await fetchExtraction(
                                                                    item.id,
                                                                );

                                                            hydrateExtraction(
                                                                full,
                                                            );

                                                            setImportResult(
                                                                null,
                                                            );
                                                        } catch (err: unknown) {
                                                            setError(
                                                                err instanceof Error
                                                                    ? err.message
                                                                    : "Failed to load extraction history.",
                                                            );
                                                        } finally {
                                                            setAction(
                                                                null,
                                                            );
                                                        }
                                                    }
                                                )();
                                            }}
                                            disabled={
                                                action !== null
                                                || reviewSaveState !== "saved"
                                            }
                                            className={`rounded-lg border px-3 py-2 text-xs font-semibold transition disabled:opacity-50 ${item.id
                                                === extraction.id
                                                ? "border-blue-300 bg-blue-50 text-blue-700"
                                                : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                                                }`}
                                        >
                                            v
                                            {item.version}
                                            {" · "}
                                            {statusLabel(
                                                item.status,
                                            )}
                                        </button>
                                    ),
                                )}
                            </div>
                        </div>
                    )}

                    {proposal && (
                        <>
                            {proposal.warnings.length > 0 && (
                                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
                                    <p className="text-sm font-bold text-amber-900">
                                        Extraction warnings
                                    </p>

                                    <div className="mt-2 space-y-2">
                                        {proposal.warnings.map(
                                            (
                                                warning,
                                                index,
                                            ) => (
                                                <div
                                                    key={`${warning.code}-${index}`}
                                                    className="text-sm text-amber-800"
                                                >
                                                    <span className="font-semibold">
                                                        {warning.message}
                                                    </span>

                                                    {warning.page_numbers.length > 0 && (
                                                        <span>
                                                            {" "}
                                                            Pages{" "}
                                                            {warning.page_numbers.join(
                                                                ", ",
                                                            )}
                                                            .
                                                        </span>
                                                    )}
                                                </div>
                                            ),
                                        )}
                                    </div>
                                </div>
                            )}

                            <div className="mt-6">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                                    <div>
                                        <h3 className="text-lg font-extrabold text-slate-900">
                                            Teacher review
                                        </h3>

                                        <p className="mt-1 text-sm leading-6 text-slate-600">
                                            Check the numbering, wording,
                                            marks, hierarchy, question type,
                                            answer options and visual assets
                                            against the original paper.
                                        </p>
                                    </div>

                                    {isDraft
                                        && extraction.status === "completed"
                                        && (
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    void handleExtract()
                                                }
                                                disabled={
                                                    action !== null
                                                    || reviewSaveState !== "saved"
                                                }
                                                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                                            >
                                                {action === "extract"
                                                    ? "Extracting..."
                                                    : "Run extraction again"}
                                            </button>
                                        )}
                                </div>

                                <div className="mt-4 space-y-4">
                                    {reviewQuestions.map(
                                        question => (
                                            <div
                                                key={
                                                    question.candidateIndex
                                                }
                                                className={`rounded-xl border p-4 ${question.included
                                                    ? "border-slate-200 bg-white"
                                                    : "border-slate-200 bg-slate-50 opacity-75"
                                                    }`}
                                            >
                                                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">
                                                            Candidate{" "}
                                                            {question.candidateIndex + 1}
                                                        </span>

                                                        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">
                                                            Page{" "}
                                                            {question.source.page_number}
                                                        </span>

                                                        {question.source.line_number && (
                                                            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
                                                                Line{" "}
                                                                {question.source.line_number}
                                                            </span>
                                                        )}

                                                        <span className="rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700">
                                                            {question.confidence}
                                                        </span>
                                                    </div>

                                                    <div className="flex flex-wrap gap-4">
                                                        <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                                                            <input
                                                                type="checkbox"
                                                                checked={
                                                                    question.included
                                                                }
                                                                onChange={
                                                                    event =>
                                                                        updateReviewQuestion(
                                                                            question.candidateIndex,
                                                                            {
                                                                                included:
                                                                                    event.target.checked,
                                                                            },
                                                                        )
                                                                }
                                                                disabled={
                                                                    !canEditReview
                                                                    || action !== null
                                                                }
                                                                className="h-4 w-4"
                                                            />
                                                            Include
                                                        </label>

                                                        <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                                                            <input
                                                                type="checkbox"
                                                                checked={
                                                                    question.reviewed
                                                                }
                                                                onChange={
                                                                    event =>
                                                                        updateReviewQuestion(
                                                                            question.candidateIndex,
                                                                            {
                                                                                reviewed:
                                                                                    event.target.checked,
                                                                            },
                                                                        )
                                                                }
                                                                disabled={
                                                                    !canEditReview
                                                                    || action !== null
                                                                    || !question.included
                                                                }
                                                                className="h-4 w-4"
                                                            />
                                                            Reviewed
                                                        </label>
                                                    </div>
                                                </div>

                                                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                                    <label className="block">
                                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                            Question number
                                                        </span>

                                                        <input
                                                            type="text"
                                                            value={
                                                                question.questionNumber
                                                            }
                                                            onChange={
                                                                event =>
                                                                    updateReviewQuestion(
                                                                        question.candidateIndex,
                                                                        {
                                                                            questionNumber:
                                                                                event.target.value,
                                                                        },
                                                                    )
                                                            }
                                                            disabled={
                                                                !canEditReview
                                                                || action !== null
                                                                || !question.included
                                                            }
                                                            maxLength={
                                                                100
                                                            }
                                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                        />
                                                    </label>

                                                    <label className="block">
                                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                            Marks
                                                        </span>

                                                        <input
                                                            type="number"
                                                            min={
                                                                0
                                                            }
                                                            max={
                                                                10000
                                                            }
                                                            step={
                                                                1
                                                            }
                                                            value={
                                                                question.marks
                                                            }
                                                            onChange={
                                                                event =>
                                                                    updateReviewQuestion(
                                                                        question.candidateIndex,
                                                                        {
                                                                            marks:
                                                                                event.target.value,
                                                                        },
                                                                    )
                                                            }
                                                            disabled={
                                                                !canEditReview
                                                                || action !== null
                                                                || !question.included
                                                            }
                                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                        />
                                                    </label>

                                                    <label className="block md:col-span-2 xl:col-span-1">
                                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                            Question type
                                                        </span>

                                                        <select
                                                            value={
                                                                question.questionType
                                                            }
                                                            onChange={
                                                                event =>
                                                                    setReviewQuestionType(
                                                                        question.candidateIndex,
                                                                        event.target.value as QuestionType,
                                                                    )
                                                            }
                                                            disabled={
                                                                !canEditReview
                                                                || action !== null
                                                                || !question.included
                                                            }
                                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                        >
                                                            {QUESTION_TYPE_OPTIONS.map(
                                                                option => (
                                                                    <option
                                                                        key={
                                                                            option.value
                                                                        }
                                                                        value={
                                                                            option.value
                                                                        }
                                                                    >
                                                                        {option.label}
                                                                    </option>
                                                                ),
                                                            )}
                                                        </select>
                                                    </label>

                                                    <label className="block md:col-span-2 xl:col-span-1">
                                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                            Parent question number
                                                        </span>

                                                        <input
                                                            type="text"
                                                            value={
                                                                question.parentQuestionNumber
                                                            }
                                                            onChange={
                                                                event =>
                                                                    updateReviewQuestion(
                                                                        question.candidateIndex,
                                                                        {
                                                                            parentQuestionNumber:
                                                                                event.target.value,
                                                                        },
                                                                    )
                                                            }
                                                            disabled={
                                                                !canEditReview
                                                                || action !== null
                                                                || !question.included
                                                            }
                                                            maxLength={
                                                                100
                                                            }
                                                            placeholder="Leave blank to infer from numbering"
                                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                        />
                                                    </label>

                                                    <label className="block md:col-span-2 xl:col-span-4">
                                                        <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                            Question text
                                                        </span>

                                                        <div className="mt-1">
                                                            <ScientificTextEditor
                                                                value={
                                                                    question.text
                                                                }
                                                                onChange={
                                                                    value =>
                                                                        updateReviewQuestion(
                                                                            question.candidateIndex,
                                                                            {
                                                                                text:
                                                                                    value,
                                                                            },
                                                                        )
                                                                }
                                                                disabled={
                                                                    !canEditReview
                                                                    || action !== null
                                                                    || !question.included
                                                                }
                                                                rows={
                                                                    3
                                                                }
                                                                maxLength={
                                                                    20_000
                                                                }
                                                                ariaLabel={`Question ${question.questionNumber || question.candidateIndex + 1} text`}
                                                            />
                                                        </div>
                                                    </label>

                                                    {questionTypeUsesOptions(
                                                        question.questionType,
                                                    ) && (
                                                            <div className="md:col-span-2 xl:col-span-4">
                                                                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                                                                    <div>
                                                                        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                                            Answer options
                                                                        </p>

                                                                        <p className="mt-1 text-xs leading-5 text-slate-500">
                                                                            {question.questionType
                                                                                === "multiple_choice_multiple"
                                                                                ? "Select every answer that should be accepted as correct."
                                                                                : "Select the single correct answer."}
                                                                        </p>
                                                                    </div>

                                                                    {question.questionType
                                                                        !== "true_false"
                                                                        && (
                                                                            <button
                                                                                type="button"
                                                                                onClick={() =>
                                                                                    addReviewOption(
                                                                                        question.candidateIndex,
                                                                                    )
                                                                                }
                                                                                disabled={
                                                                                    !canEditReview
                                                                                    || action !== null
                                                                                    || !question.included
                                                                                }
                                                                                className="rounded-lg border border-blue-300 bg-white px-3 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 disabled:opacity-50"
                                                                            >
                                                                                Add option
                                                                            </button>
                                                                        )}
                                                                </div>

                                                                <div className="mt-3 space-y-3">
                                                                    {question.options.map(
                                                                        (
                                                                            option,
                                                                            optionIndex,
                                                                        ) => (
                                                                            <div
                                                                                key={
                                                                                    option.localId
                                                                                }
                                                                                className="rounded-xl border border-slate-200 bg-slate-50 p-3"
                                                                            >
                                                                                <div className="flex flex-col gap-3 lg:flex-row lg:items-start">
                                                                                    <label className="flex shrink-0 items-center gap-2 pt-2 text-sm font-semibold text-slate-700">
                                                                                        <input
                                                                                            type={
                                                                                                question.questionType
                                                                                                    === "multiple_choice_multiple"
                                                                                                    ? "checkbox"
                                                                                                    : "radio"
                                                                                            }
                                                                                            name={
                                                                                                question.questionType
                                                                                                    === "multiple_choice_multiple"
                                                                                                    ? undefined
                                                                                                    : `correct-option-${question.candidateIndex}`
                                                                                            }
                                                                                            checked={
                                                                                                option.isCorrect
                                                                                            }
                                                                                            onChange={
                                                                                                event =>
                                                                                                    updateReviewOption(
                                                                                                        question.candidateIndex,
                                                                                                        option.localId,
                                                                                                        {
                                                                                                            isCorrect:
                                                                                                                event.target.checked,
                                                                                                        },
                                                                                                    )
                                                                                            }
                                                                                            disabled={
                                                                                                !canEditReview
                                                                                                || action !== null
                                                                                                || !question.included
                                                                                            }
                                                                                            className="h-4 w-4"
                                                                                        />

                                                                                        Correct
                                                                                    </label>

                                                                                    <div className="min-w-0 flex-1">
                                                                                        <ScientificTextEditor
                                                                                            value={
                                                                                                option.text
                                                                                            }
                                                                                            onChange={
                                                                                                value =>
                                                                                                    updateReviewOption(
                                                                                                        question.candidateIndex,
                                                                                                        option.localId,
                                                                                                        {
                                                                                                            text:
                                                                                                                value,
                                                                                                        },
                                                                                                    )
                                                                                            }
                                                                                            disabled={
                                                                                                !canEditReview
                                                                                                || action !== null
                                                                                                || !question.included
                                                                                                || question.questionType
                                                                                                === "true_false"
                                                                                            }
                                                                                            rows={
                                                                                                1
                                                                                            }
                                                                                            maxLength={
                                                                                                20_000
                                                                                            }
                                                                                            ariaLabel={`Question ${question.questionNumber || question.candidateIndex + 1} option ${optionIndex + 1}`}
                                                                                        />

                                                                                        <input
                                                                                            type="text"
                                                                                            value={
                                                                                                option.feedback
                                                                                            }
                                                                                            onChange={
                                                                                                event =>
                                                                                                    updateReviewOption(
                                                                                                        question.candidateIndex,
                                                                                                        option.localId,
                                                                                                        {
                                                                                                            feedback:
                                                                                                                event.target.value,
                                                                                                        },
                                                                                                    )
                                                                                            }
                                                                                            disabled={
                                                                                                !canEditReview
                                                                                                || action !== null
                                                                                                || !question.included
                                                                                            }
                                                                                            maxLength={
                                                                                                20_000
                                                                                            }
                                                                                            placeholder="Optional feedback for this option"
                                                                                            className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                                                        />
                                                                                    </div>

                                                                                    {question.questionType
                                                                                        !== "true_false"
                                                                                        && (
                                                                                            <div className="flex shrink-0 gap-1">
                                                                                                <button
                                                                                                    type="button"
                                                                                                    onClick={() =>
                                                                                                        moveReviewOption(
                                                                                                            question.candidateIndex,
                                                                                                            option.localId,
                                                                                                            -1,
                                                                                                        )
                                                                                                    }
                                                                                                    disabled={
                                                                                                        !canEditReview
                                                                                                        || action !== null
                                                                                                        || !question.included
                                                                                                        || optionIndex === 0
                                                                                                    }
                                                                                                    className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-bold text-slate-600 disabled:opacity-40"
                                                                                                    aria-label={`Move option ${optionIndex + 1} up`}
                                                                                                >
                                                                                                    ↑
                                                                                                </button>

                                                                                                <button
                                                                                                    type="button"
                                                                                                    onClick={() =>
                                                                                                        moveReviewOption(
                                                                                                            question.candidateIndex,
                                                                                                            option.localId,
                                                                                                            1,
                                                                                                        )
                                                                                                    }
                                                                                                    disabled={
                                                                                                        !canEditReview
                                                                                                        || action !== null
                                                                                                        || !question.included
                                                                                                        || optionIndex
                                                                                                        === question.options.length - 1
                                                                                                    }
                                                                                                    className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-bold text-slate-600 disabled:opacity-40"
                                                                                                    aria-label={`Move option ${optionIndex + 1} down`}
                                                                                                >
                                                                                                    ↓
                                                                                                </button>

                                                                                                <button
                                                                                                    type="button"
                                                                                                    onClick={() =>
                                                                                                        removeReviewOption(
                                                                                                            question.candidateIndex,
                                                                                                            option.localId,
                                                                                                        )
                                                                                                    }
                                                                                                    disabled={
                                                                                                        !canEditReview
                                                                                                        || action !== null
                                                                                                        || !question.included
                                                                                                        || question.options.length <= 2
                                                                                                    }
                                                                                                    className="rounded-md border border-red-200 bg-white px-2 py-1 text-xs font-bold text-red-600 disabled:opacity-40"
                                                                                                >
                                                                                                    Remove
                                                                                                </button>
                                                                                            </div>
                                                                                        )}
                                                                                </div>
                                                                            </div>
                                                                        ),
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}

                                                    {question.assets.length > 0 && (
                                                        <div className="md:col-span-2 xl:col-span-4">
                                                            <div>
                                                                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                                    Visual assets
                                                                </p>

                                                                <p className="mt-1 text-xs leading-5 text-slate-500">
                                                                    Review each extractor-owned image, diagram, graph or figure. Source provenance is shown for reference and cannot be edited here.
                                                                </p>
                                                            </div>

                                                            <div className="mt-3 space-y-3">
                                                                {question.assets.map(
                                                                    asset => (
                                                                        <div
                                                                            key={
                                                                                asset.assetIndex
                                                                            }
                                                                            className={`rounded-xl border p-4 ${asset.included
                                                                                ? "border-slate-200 bg-slate-50"
                                                                                : "border-slate-200 bg-slate-100 opacity-75"
                                                                                }`}
                                                                        >
                                                                            <SecureExtractionAssetPreview
                                                                                contentUrl={
                                                                                    asset.contentUrl
                                                                                }
                                                                                altText={
                                                                                    asset.altText
                                                                                }
                                                                                caption={
                                                                                    asset.caption
                                                                                }
                                                                                mimeType={
                                                                                    asset.mimeType
                                                                                }
                                                                            />

                                                                            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                                                                <label className="block">
                                                                                    <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                                                        Asset type
                                                                                    </span>

                                                                                    <select
                                                                                        value={
                                                                                            asset.assetType
                                                                                        }
                                                                                        onChange={
                                                                                            event =>
                                                                                                updateReviewAsset(
                                                                                                    question.candidateIndex,
                                                                                                    asset.assetIndex,
                                                                                                    {
                                                                                                        assetType:
                                                                                                            event.target.value as QuestionAssetType,
                                                                                                    },
                                                                                                )
                                                                                        }
                                                                                        disabled={
                                                                                            !canEditReview
                                                                                            || action !== null
                                                                                            || !question.included
                                                                                            || !asset.included
                                                                                        }
                                                                                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                                                    >
                                                                                        {QUESTION_ASSET_TYPE_OPTIONS.map(
                                                                                            option => (
                                                                                                <option
                                                                                                    key={
                                                                                                        option.value
                                                                                                    }
                                                                                                    value={
                                                                                                        option.value
                                                                                                    }
                                                                                                >
                                                                                                    {option.label}
                                                                                                </option>
                                                                                            ),
                                                                                        )}
                                                                                    </select>
                                                                                </label>

                                                                                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 md:self-end md:pb-2">
                                                                                    <input
                                                                                        type="checkbox"
                                                                                        checked={
                                                                                            asset.included
                                                                                        }
                                                                                        onChange={
                                                                                            event =>
                                                                                                updateReviewAsset(
                                                                                                    question.candidateIndex,
                                                                                                    asset.assetIndex,
                                                                                                    {
                                                                                                        included:
                                                                                                            event.target.checked,
                                                                                                    },
                                                                                                )
                                                                                        }
                                                                                        disabled={
                                                                                            !canEditReview
                                                                                            || action !== null
                                                                                            || !question.included
                                                                                        }
                                                                                        className="h-4 w-4"
                                                                                    />

                                                                                    Include asset
                                                                                </label>

                                                                                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 md:self-end md:pb-2">
                                                                                    <input
                                                                                        type="checkbox"
                                                                                        checked={
                                                                                            asset.candidateVisible
                                                                                        }
                                                                                        onChange={
                                                                                            event =>
                                                                                                updateReviewAsset(
                                                                                                    question.candidateIndex,
                                                                                                    asset.assetIndex,
                                                                                                    {
                                                                                                        candidateVisible:
                                                                                                            event.target.checked,
                                                                                                    },
                                                                                                )
                                                                                        }
                                                                                        disabled={
                                                                                            !canEditReview
                                                                                            || action !== null
                                                                                            || !question.included
                                                                                            || !asset.included
                                                                                        }
                                                                                        className="h-4 w-4"
                                                                                    />

                                                                                    Candidate visible
                                                                                </label>

                                                                                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 md:self-end md:pb-2">
                                                                                    <input
                                                                                        type="checkbox"
                                                                                        checked={
                                                                                            asset.reviewed
                                                                                        }
                                                                                        onChange={
                                                                                            event =>
                                                                                                updateReviewAsset(
                                                                                                    question.candidateIndex,
                                                                                                    asset.assetIndex,
                                                                                                    {
                                                                                                        reviewed:
                                                                                                            event.target.checked,
                                                                                                    },
                                                                                                )
                                                                                        }
                                                                                        disabled={
                                                                                            !canEditReview
                                                                                            || action !== null
                                                                                            || !question.included
                                                                                            || !asset.included
                                                                                        }
                                                                                        className="h-4 w-4"
                                                                                    />

                                                                                    Asset reviewed
                                                                                </label>

                                                                                <label className="block md:col-span-2">
                                                                                    <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                                                        Alt text
                                                                                    </span>

                                                                                    <input
                                                                                        type="text"
                                                                                        value={
                                                                                            asset.altText
                                                                                        }
                                                                                        onChange={
                                                                                            event =>
                                                                                                updateReviewAsset(
                                                                                                    question.candidateIndex,
                                                                                                    asset.assetIndex,
                                                                                                    {
                                                                                                        altText:
                                                                                                            event.target.value,
                                                                                                    },
                                                                                                )
                                                                                        }
                                                                                        disabled={
                                                                                            !canEditReview
                                                                                            || action !== null
                                                                                            || !question.included
                                                                                            || !asset.included
                                                                                        }
                                                                                        maxLength={
                                                                                            20_000
                                                                                        }
                                                                                        placeholder="Describe the visual for accessibility"
                                                                                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                                                    />
                                                                                </label>

                                                                                <label className="block md:col-span-2">
                                                                                    <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                                                        Caption
                                                                                    </span>

                                                                                    <input
                                                                                        type="text"
                                                                                        value={
                                                                                            asset.caption
                                                                                        }
                                                                                        onChange={
                                                                                            event =>
                                                                                                updateReviewAsset(
                                                                                                    question.candidateIndex,
                                                                                                    asset.assetIndex,
                                                                                                    {
                                                                                                        caption:
                                                                                                            event.target.value,
                                                                                                    },
                                                                                                )
                                                                                        }
                                                                                        disabled={
                                                                                            !canEditReview
                                                                                            || action !== null
                                                                                            || !question.included
                                                                                            || !asset.included
                                                                                        }
                                                                                        maxLength={
                                                                                            20_000
                                                                                        }
                                                                                        placeholder="Optional candidate-facing caption"
                                                                                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                                                                    />
                                                                                </label>
                                                                            </div>

                                                                            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                                                                                {asset.sourcePageNumber && (
                                                                                    <span className="rounded-full bg-white px-2.5 py-1 font-semibold">
                                                                                        Source page {asset.sourcePageNumber}
                                                                                    </span>
                                                                                )}

                                                                                {asset.originalFilename && (
                                                                                    <span className="rounded-full bg-white px-2.5 py-1 font-semibold">
                                                                                        {asset.originalFilename}
                                                                                    </span>
                                                                                )}

                                                                                {asset.mimeType && (
                                                                                    <span className="rounded-full bg-white px-2.5 py-1 font-semibold">
                                                                                        {asset.mimeType}
                                                                                    </span>
                                                                                )}

                                                                                {!asset.contentUrl && asset.included && (
                                                                                    <span className="rounded-full bg-amber-100 px-2.5 py-1 font-bold text-amber-700">
                                                                                        Secure visual preview unavailable
                                                                                    </span>
                                                                                )}
                                                                            </div>
                                                                        </div>
                                                                    ),
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>

                                                {question.source.source_line && (
                                                    <div className="mt-4 rounded-lg bg-slate-50 p-3">
                                                        <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                                            Extracted source line
                                                        </p>

                                                        <p className="mt-1 text-sm leading-6 text-slate-600">
                                                            {question.source.source_line}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        ),
                                    )}
                                </div>

                                <label className="mt-5 block">
                                    <span className="text-sm font-bold text-slate-700">
                                        Review notes
                                    </span>

                                    <textarea
                                        value={
                                            reviewNotes
                                        }
                                        onChange={
                                            event =>
                                                setReviewNotes(
                                                    event.target.value,
                                                )
                                        }
                                        disabled={
                                            !canEditReview
                                            || action !== null
                                        }
                                        rows={
                                            3
                                        }
                                        maxLength={
                                            10_000
                                        }
                                        placeholder="Optional notes about checks or corrections made during review."
                                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-slate-900 outline-none focus:border-blue-500 disabled:bg-slate-100"
                                    />
                                </label>

                                <div className="mt-5 flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                                    <div className="text-sm text-slate-600">
                                        <span className="font-bold text-slate-800">
                                            {includedQuestions.length}
                                        </span>
                                        {" "}
                                        included ·{" "}
                                        <span className="font-bold text-slate-800">
                                            {includedMarkTotal}
                                        </span>
                                        {" "}
                                        marks

                                        {missingMarkCount > 0 && (
                                            <span className="ml-2 font-semibold text-amber-700">
                                                · {missingMarkCount} missing mark
                                                {missingMarkCount === 1
                                                    ? ""
                                                    : "s"}
                                            </span>
                                        )}

                                        {unreviewedIncludedCount > 0 && (
                                            <span className="ml-2 font-semibold text-amber-700">
                                                · {unreviewedIncludedCount} not reviewed
                                            </span>
                                        )}
                                    </div>

                                    <div className="flex flex-wrap items-center gap-2">
                                        {reviewSaveState === "saved" && (
                                            <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-bold text-green-700">
                                                All changes saved
                                                {lastReviewSavedAt
                                                    ? ` · ${lastReviewSavedAt.toLocaleTimeString(
                                                        "en-GB",
                                                        {
                                                            hour:
                                                                "2-digit",
                                                            minute:
                                                                "2-digit",
                                                            second:
                                                                "2-digit",
                                                        },
                                                    )}`
                                                    : ""}
                                            </span>
                                        )}

                                        {reviewSaveState === "dirty" && (
                                            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-700">
                                                Unsaved changes · autosaving shortly
                                            </span>
                                        )}

                                        {reviewSaveState === "saving" && (
                                            <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-bold text-blue-700">
                                                Saving...
                                            </span>
                                        )}

                                        {reviewSaveState === "error" && (
                                            <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-700">
                                                Autosave needs attention
                                            </span>
                                        )}
                                    </div>

                                    {reviewSaveError && (
                                        <p className="w-full text-xs font-semibold text-red-700">
                                            {reviewSaveError}
                                        </p>
                                    )}

                                    {canEditReview
                                        && !isReviewComplete
                                        && (
                                        <div className="flex flex-wrap gap-3">
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    void saveReview(
                                                        "in_progress",
                                                    )
                                                }
                                                disabled={
                                                    action !== null
                                                    || reviewSaveState === "saving"
                                                }
                                                className="rounded-lg border border-blue-300 bg-white px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-50 disabled:opacity-50"
                                            >
                                                {action === "save-review"
                                                    ? "Saving..."
                                                    : "Save review"}
                                            </button>

                                            <button
                                                type="button"
                                                onClick={() =>
                                                    void saveReview(
                                                        "reviewed",
                                                    )
                                                }
                                                disabled={
                                                    action !== null
                                                    || reviewSaveState === "saving"
                                                }
                                                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                                            >
                                                {action === "complete-review"
                                                    ? "Completing..."
                                                    : "Mark review complete"}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {isReviewComplete
                                && extraction.status === "completed"
                                && (
                                    <div className="mt-6 rounded-xl border border-green-200 bg-green-50 p-5">
                                        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                                            <div>
                                                <p className="font-bold text-green-900">
                                                    Review complete
                                                </p>

                                                <p className="mt-1 text-sm leading-6 text-green-800">
                                                    The reviewed proposal is ready
                                                    for explicit import into the
                                                    assessment question structure.
                                                </p>
                                            </div>

                                            <button
                                                type="button"
                                                onClick={() =>
                                                    void handleImport()
                                                }
                                                disabled={
                                                    !canImport
                                                    || action !== null
                                                }
                                                className="rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-50"
                                            >
                                                {action === "import"
                                                    ? "Importing..."
                                                    : "Import reviewed questions"}
                                            </button>
                                        </div>
                                    </div>
                                )}
                        </>
                    )}

                    {isImported && (
                        <div className="mt-6 rounded-xl border border-green-200 bg-green-50 p-5">
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <p className="font-bold text-green-900">
                                        Questions imported
                                    </p>

                                    <p className="mt-1 text-sm leading-6 text-green-800">
                                        This extraction has been converted into
                                        canonical assessment questions.
                                    </p>
                                </div>

                                <span className="text-xs font-semibold text-green-700">
                                    Imported{" "}
                                    {formatDateTime(
                                        extraction.imported_at,
                                    )}
                                </span>
                            </div>

                            {importResult && (
                                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                                    <div className="rounded-lg bg-white/70 p-3">
                                        <p className="text-xs font-bold uppercase tracking-wide text-green-700">
                                            Created
                                        </p>

                                        <p className="mt-1 text-lg font-extrabold text-green-950">
                                            {importResult.imported_question_count}
                                        </p>
                                    </div>

                                    <div className="rounded-lg bg-white/70 p-3">
                                        <p className="text-xs font-bold uppercase tracking-wide text-green-700">
                                            Markable
                                        </p>

                                        <p className="mt-1 text-lg font-extrabold text-green-950">
                                            {importResult.imported_markable_question_count}
                                        </p>
                                    </div>

                                    <div className="rounded-lg bg-white/70 p-3">
                                        <p className="text-xs font-bold uppercase tracking-wide text-green-700">
                                            Structural parents
                                        </p>

                                        <p className="mt-1 text-lg font-extrabold text-green-950">
                                            {importResult.synthesised_parent_count}
                                        </p>
                                    </div>

                                    <div className="rounded-lg bg-white/70 p-3">
                                        <p className="text-xs font-bold uppercase tracking-wide text-green-700">
                                            Total marks
                                        </p>

                                        <p className="mt-1 text-lg font-extrabold text-green-950">
                                            {String(
                                                importResult.imported_total_marks,
                                            )}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}
        </section>
    );
}
