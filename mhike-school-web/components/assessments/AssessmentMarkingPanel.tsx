"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    ApiError,
} from "@/lib/api";

import {
    completeAssessmentScriptMarking,
    getAssessmentCandidates,
    getLatestCandidateScript,
    isScriptAvailableForMarking,
    startAssessmentScriptMarking,
    type AssessmentCandidate,
    type AssessmentScript,
} from "@/lib/services/assessment-candidates";

import {
    createMarkingDecision,
    getAssessmentResponseAssetBlob,
    getMarkingAnnotations,
    getResponseMarkingPalette,
    getScriptResponses,
    instantMarkDecision,
    updateMarkingDecision,
    type AssessmentResponse,
    type MarkingAnnotation,
    type MarkingDecision,
    type MarkingPalette,
} from "@/lib/services/assessment-marking";

import type {
    Assessment,
} from "@/lib/services/assessments";


// ---------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------


type AssessmentMarkingPanelProps = {
    assessment: Assessment;
};


// ---------------------------------------------------------------------
// Local workspace types
// ---------------------------------------------------------------------


type CandidateWorkspaceItem = {
    candidate: AssessmentCandidate;
    script: AssessmentScript;
};


type DraftState = {
    mark: string;
    markerComment: string;
};


// ---------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------


function getCandidateLabel(
    assessment: Assessment,
    candidate: AssessmentCandidate,
): string {
    if (candidate.candidate_number) {
        return `Candidate ${candidate.candidate_number}`;
    }

    if (assessment.anonymous_marking) {
        return `Candidate ${candidate.id}`;
    }

    /*
     * The assessment-candidate contract deliberately does not expose
     * student names. Avoid manufacturing identity data here.
     */
    return `Candidate ${candidate.id}`;
}


function getStatusLabel(
    value: string,
): string {
    return value
        .split("_")
        .map(
            (part) => (
                part.charAt(0).toUpperCase()
                + part.slice(1)
            ),
        )
        .join(" ");
}


type StructuredResponseData =
    Record<string, unknown>;


type DiagramAnnotation = {
    id: string;
    x: number;
    y: number;
    symbol: string;
};


function parseStructuredResponse(
    value: string | null,
): unknown {
    if (!value) {
        return null;
    }

    try {
        return JSON.parse(value) as unknown;
    } catch {
        return value;
    }
}


function asResponseRecord(
    value: unknown,
): StructuredResponseData | null {
    if (
        typeof value !== "object"
        || value === null
        || Array.isArray(value)
    ) {
        return null;
    }

    return value as StructuredResponseData;
}


function asInteger(
    value: unknown,
): number | null {
    const numeric =
        typeof value === "number"
            ? value
            : typeof value === "string"
                ? Number(value)
                : Number.NaN;

    return Number.isInteger(numeric)
        ? numeric
        : null;
}


function getSelectedOptionIds(
    data: StructuredResponseData,
): number[] {
    const values: unknown[] = [];

    if ("option_id" in data) {
        values.push(data.option_id);
    }

    if ("selected_option_id" in data) {
        values.push(data.selected_option_id);
    }

    for (
        const key
        of [
            "option_ids",
            "selected_option_ids",
        ]
    ) {
        const value = data[key];

        if (Array.isArray(value)) {
            values.push(...value);
        }
    }

    return Array.from(
        new Set(
            values
                .map(asInteger)
                .filter(
                    (
                        value,
                    ): value is number => (
                        value !== null
                    ),
                ),
        ),
    );
}


function getDiagramAnnotations(
    data: StructuredResponseData,
): DiagramAnnotation[] {
    if (!Array.isArray(data.annotations)) {
        return [];
    }

    return data.annotations.flatMap(
        (
            item,
            index,
        ) => {
            const record =
                asResponseRecord(item);

            if (!record) {
                return [];
            }

            const x =
                typeof record.x === "number"
                    ? record.x
                    : Number(record.x);

            const y =
                typeof record.y === "number"
                    ? record.y
                    : Number(record.y);

            if (
                !Number.isFinite(x)
                || !Number.isFinite(y)
                || x < 0
                || x > 1
                || y < 0
                || y > 1
            ) {
                return [];
            }

            const symbol =
                typeof record.symbol === "string"
                && record.symbol.trim()
                    ? record.symbol.trim()
                    : "•";

            return [
                {
                    id:
                        typeof record.id === "string"
                            ? record.id
                            : `annotation-${index}`,
                    x,
                    y,
                    symbol,
                },
            ];
        },
    );
}


function formatUnknownResponse(
    value: unknown,
): string {
    if (typeof value === "string") {
        return value;
    }

    try {
        return JSON.stringify(
            value,
            null,
            2,
        );
    } catch {
        return String(value);
    }
}


function DiagramAnnotationResponse({
    response,
    data,
}: {
    response: AssessmentResponse;
    data: StructuredResponseData;
}) {
    const snapshot =
        response.question_snapshot;

    const requestedAssetId =
        asInteger(data.asset_id);

    const asset =
        snapshot?.assets_snapshot.find(
            (item) => (
                requestedAssetId !== null
                && item.id === requestedAssetId
            ),
        )
        ?? snapshot?.assets_snapshot[0]
        ?? null;

    const annotations =
        getDiagramAnnotations(data);

    const [
        assetUrl,
        setAssetUrl,
    ] = useState<string | null>(
        null,
    );

    const [
        assetError,
        setAssetError,
    ] = useState<string | null>(
        null,
    );

    useEffect(
        () => {
            let cancelled = false;
            let objectUrl: string | null = null;

            if (!asset) {
                setAssetUrl(null);
                setAssetError(
                    "The immutable question snapshot does not contain the diagram asset.",
                );

                return;
            }

            setAssetUrl(null);
            setAssetError(null);

            void getAssessmentResponseAssetBlob(
                response.id,
                asset.id,
            )
                .then(
                    (blob) => {
                        if (cancelled) {
                            return;
                        }

                        objectUrl =
                            URL.createObjectURL(blob);

                        setAssetUrl(objectUrl);
                    },
                )
                .catch(
                    (error: unknown) => {
                        if (cancelled) {
                            return;
                        }

                        setAssetError(
                            error instanceof Error
                                ? error.message
                                : "Unable to load the submitted diagram.",
                        );
                    },
                );

            return () => {
                cancelled = true;

                if (objectUrl) {
                    URL.revokeObjectURL(
                        objectUrl,
                    );
                }
            };
        },
        [
            asset,
            response.id,
        ],
    );

    if (assetError) {
        return (
            <p className="text-sm text-amber-300">
                {assetError}
            </p>
        );
    }

    if (!assetUrl) {
        return (
            <p className="text-sm text-slate-400">
                Loading submitted diagram…
            </p>
        );
    }

    return (
        <div className="space-y-3">
            <div className="relative inline-block max-w-full overflow-hidden rounded-xl border border-slate-600 bg-white">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                    src={assetUrl}
                    alt={
                        asset?.alt_text
                        ?? asset?.caption
                        ?? "Submitted assessment diagram"
                    }
                    className="block h-auto max-w-full"
                />

                {
                    annotations.map(
                        (annotation) => (
                            <span
                                key={annotation.id}
                                className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 border-0 bg-transparent p-0 text-lg font-bold leading-none text-slate-950 shadow-none"
                                style={{
                                    left:
                                        `${annotation.x * 100}%`,
                                    top:
                                        `${annotation.y * 100}%`,
                                }}
                            >
                                {annotation.symbol}
                            </span>
                        ),
                    )
                }
            </div>

            <p className="text-xs text-slate-400">
                {annotations.length} saved annotation{
                    annotations.length === 1
                        ? ""
                        : "s"
                }
            </p>
        </div>
    );
}


function StructuredResponseContent({
    response,
}: {
    response: AssessmentResponse;
}) {
    const snapshot =
        response.question_snapshot;

    const parsed =
        parseStructuredResponse(
            response.response_data,
        );

    const data =
        asResponseRecord(parsed);

    if (
        snapshot?.question_type
        === "diagram_annotation"
        && data
    ) {
        return (
            <DiagramAnnotationResponse
                response={response}
                data={data}
            />
        );
    }

    if (
        (
            snapshot?.question_type
            === "multiple_choice_single"
            || snapshot?.question_type
            === "multiple_choice_multiple"
        )
        && data
    ) {
        const selectedIds =
            getSelectedOptionIds(data);

        const selectedOptions =
            snapshot.options_snapshot
                .filter(
                    (option) => (
                        selectedIds.includes(
                            option.id,
                        )
                    ),
                )
                .sort(
                    (
                        left,
                        right,
                    ) => (
                        left.order
                        - right.order
                    ),
                );

        if (selectedOptions.length > 0) {
            return (
                <div className="space-y-2">
                    {
                        selectedOptions.map(
                            (option) => (
                                <div
                                    key={option.id}
                                    className="rounded-lg border border-blue-400/30 bg-blue-400/10 px-3 py-2 text-base text-white"
                                >
                                    {option.text}
                                </div>
                            ),
                        )
                    }
                </div>
            );
        }
    }

    if (parsed !== null) {
        return (
            <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-black/30 p-3 text-sm text-slate-200">
                {
                    formatUnknownResponse(
                        parsed,
                    )
                }
            </pre>
        );
    }

    return null;
}


function asFiniteNumber(
    value: string | number,
): number | null {
    const numeric =
        typeof value === "number"
            ? value
            : Number(value);

    return Number.isFinite(numeric)
        ? numeric
        : null;
}


function getQuickMarks(
    question:
        | {
            maximum_mark:
                | string
                | number;
        }
        | null
        | undefined,
): number[] {
    if (!question) {
        return [];
    }

    const maximumMark =
        asFiniteNumber(
            question.maximum_mark,
        );

    if (
        maximumMark === null
        || maximumMark < 0
    ) {
        return [];
    }

    if (
        Number.isInteger(maximumMark)
        && maximumMark <= 10
    ) {
        return Array.from(
            {
                length:
                    maximumMark + 1,
            },
            (
                _,
                index,
            ) => index,
        );
    }

    if (maximumMark === 0) {
        return [0];
    }

    return Array.from(
        new Set(
            [
                0,
                1,
                maximumMark,
            ],
        ),
    ).sort(
        (
            left,
            right,
        ) => left - right,
    );
}


function isDecisionReadOnly(
    decision: MarkingDecision | null,
): boolean {
    return decision?.status === "finalised";
}


function hasCompletedDecision(
    response: AssessmentResponse,
): boolean {
    const status =
        response.marking_decision?.status;

    return (
        status === "marked"
        || status === "reviewed"
        || status === "finalised"
    );
}


// ---------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------


export default function AssessmentMarkingPanel({
    assessment,
}: AssessmentMarkingPanelProps) {
    const [
        workspaceItems,
        setWorkspaceItems,
    ] = useState<CandidateWorkspaceItem[]>([]);

    const [
        selectedScriptId,
        setSelectedScriptId,
    ] = useState<number | null>(
        null,
    );

    const [
        responses,
        setResponses,
    ] = useState<AssessmentResponse[]>([]);

    const [
        markingPalette,
        setMarkingPalette,
    ] = useState<MarkingPalette | null>(
        null,
    );

    const [
        markingAnnotations,
        setMarkingAnnotations,
    ] = useState<Record<number, MarkingAnnotation[]>>(
        {},
    );

    const [
        loadingMarkingEvidence,
        setLoadingMarkingEvidence,
    ] = useState(
        false,
    );

    const [
        markingEvidenceError,
        setMarkingEvidenceError,
    ] = useState<string | null>(
        null,
    );

    const [
        selectedMarkingToolId,
        setSelectedMarkingToolId,
    ] = useState<number | null>(
        null,
    );

    const [
        drafts,
        setDrafts,
    ] = useState<Record<number, DraftState>>(
        {},
    );

    const [
        loadingCandidates,
        setLoadingCandidates,
    ] = useState(
        true,
    );

    const [
        loadingResponses,
        setLoadingResponses,
    ] = useState(
        false,
    );

    const [
        savingResponseId,
        setSavingResponseId,
    ] = useState<number | null>(
        null,
    );

    const [
        scriptActionPending,
        setScriptActionPending,
    ] = useState(
        false,
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


    useEffect(
        () => {
            let cancelled = false;

            if (responses.length === 0) {
                setMarkingPalette(
                    null,
                );
                setMarkingAnnotations(
                    {},
                );
                setLoadingMarkingEvidence(
                    false,
                );
                setMarkingEvidenceError(
                    null,
                );

                return () => {
                    cancelled = true;
                };
            }

            setLoadingMarkingEvidence(
                true,
            );
            setMarkingEvidenceError(
                null,
            );

            const loadMarkingEvidence =
                async (): Promise<void> => {
                    try {
                        const [
                            palette,
                            annotationEntries,
                        ] = await Promise.all([
                            getResponseMarkingPalette(
                                responses[0].id,
                            ),
                            Promise.all(
                                responses.map(
                                    async (
                                        response,
                                    ) => (
                                        [
                                            response.id,
                                            await getMarkingAnnotations(
                                                response.id,
                                            ),
                                        ] as const
                                    ),
                                ),
                            ),
                        ]);

                        if (cancelled) {
                            return;
                        }

                        setMarkingPalette(
                            palette,
                        );

                        setMarkingAnnotations(
                            Object.fromEntries(
                                annotationEntries,
                            ),
                        );
                    } catch (
                        error
                    ) {
                        if (cancelled) {
                            return;
                        }

                        setMarkingPalette(
                            null,
                        );
                        setMarkingAnnotations(
                            {},
                        );
                        setMarkingEvidenceError(
                            error instanceof Error
                                ? error.message
                                : "Unable to load examiner marking tools.",
                        );
                    } finally {
                        if (!cancelled) {
                            setLoadingMarkingEvidence(
                                false,
                            );
                        }
                    }
                };

            void loadMarkingEvidence();

            return () => {
                cancelled = true;
            };
        },
        [
            responses,
        ],
    );


    const tickTool =
        useMemo(
            () => (
                markingPalette?.tools.find(
                    (tool) => (
                        tool.tool_type === "symbol"
                        && tool.value === "✓"
                    ),
                )
                ?? null
            ),
            [
                markingPalette,
            ],
        );


    const crossTool =
        useMemo(
            () => (
                markingPalette?.tools.find(
                    (tool) => (
                        tool.tool_type === "symbol"
                        && tool.value === "✗"
                    ),
                )
                ?? null
            ),
            [
                markingPalette,
            ],
        );


    useEffect(
        () => {
            if (
                selectedMarkingToolId !== null
                && (
                    selectedMarkingToolId === tickTool?.id
                    || selectedMarkingToolId === crossTool?.id
                )
            ) {
                return;
            }

            setSelectedMarkingToolId(
                tickTool?.id
                ?? crossTool?.id
                ?? null,
            );
        },
        [
            crossTool,
            selectedMarkingToolId,
            tickTool,
        ],
    );


    const selectedWorkspaceItem =
        useMemo(
            () => (
                workspaceItems.find(
                    (item) => (
                        item.script.id
                        === selectedScriptId
                    ),
                )
                ?? null
            ),
            [
                selectedScriptId,
                workspaceItems,
            ],
        );


    const selectedScript =
        selectedWorkspaceItem?.script
        ?? null;


    const markedCount =
        useMemo(
            () => (
                responses.filter(
                    hasCompletedDecision,
                ).length
            ),
            [
                responses,
            ],
        );


    const runningTotal =
        useMemo(
            () => (
                responses.reduce(
                    (
                        total,
                        response,
                    ) => {
                        const mark =
                            response.marking_decision
                                ?.mark_awarded;

                        if (
                            mark === null
                            || mark === undefined
                        ) {
                            return total;
                        }

                        const numericMark =
                            asFiniteNumber(
                                mark,
                            );

                        return numericMark === null
                            ? total
                            : total + numericMark;
                    },
                    0,
                )
            ),
            [
                responses,
            ],
        );


    const maximumTotal =
        useMemo(
            () => (
                responses.reduce(
                    (
                        total,
                        response,
                    ) => {
                        const maximumMark =
                            response.question_snapshot
                                ?.maximum_mark;

                        if (
                            maximumMark === null
                            || maximumMark === undefined
                        ) {
                            return total;
                        }

                        const numericMaximum =
                            asFiniteNumber(
                                maximumMark,
                            );

                        return numericMaximum === null
                            ? total
                            : total + numericMaximum;
                    },
                    0,
                )
            ),
            [
                responses,
            ],
        );


    const runningPercentage =
        maximumTotal > 0
            ? (
                runningTotal
                / maximumTotal
                * 100
            )
            : 0;


    const markingProgressPercentage =
        responses.length > 0
            ? (
                markedCount
                / responses.length
                * 100
            )
            : 0;


    const allResponsesMarked =
        responses.length > 0
        && markedCount === responses.length;


    const refreshCandidates =
        useCallback(
            async () => {
                setLoadingCandidates(
                    true,
                );

                setErrorMessage(
                    null,
                );

                try {
                    const candidates =
                        await getAssessmentCandidates(
                            assessment.id,
                        );

                    const items =
                        candidates
                            .map(
                                (
                                    candidate,
                                ): CandidateWorkspaceItem | null => {
                                    const script =
                                        getLatestCandidateScript(
                                            candidate,
                                        );

                                    if (!script) {
                                        return null;
                                    }

                                    if (
                                        !isScriptAvailableForMarking(
                                            script,
                                        )
                                        && script.status
                                            !== "finalised"
                                    ) {
                                        return null;
                                    }

                                    return {
                                        candidate,
                                        script,
                                    };
                                },
                            )
                            .filter(
                                (
                                    item,
                                ): item is CandidateWorkspaceItem => (
                                    item !== null
                                ),
                            )
                            .sort(
                                (
                                    left,
                                    right,
                                ) => {
                                    const leftLabel =
                                        getCandidateLabel(
                                            assessment,
                                            left.candidate,
                                        );

                                    const rightLabel =
                                        getCandidateLabel(
                                            assessment,
                                            right.candidate,
                                        );

                                    return leftLabel.localeCompare(
                                        rightLabel,
                                    );
                                },
                            );

                    setWorkspaceItems(
                        items,
                    );

                    setSelectedScriptId(
                        (
                            current,
                        ) => {
                            if (
                                current !== null
                                && items.some(
                                    (item) => (
                                        item.script.id
                                        === current
                                    ),
                                )
                            ) {
                                return current;
                            }

                            return items[0]?.script.id
                                ?? null;
                        },
                    );
                } catch (
                    error
                ) {
                    setErrorMessage(
                        error instanceof Error
                            ? error.message
                            : "Unable to load assessment candidates.",
                    );
                } finally {
                    setLoadingCandidates(
                        false,
                    );
                }
            },
            [
                assessment,
            ],
        );


    const refreshResponses =
        useCallback(
            async (
                scriptId: number,
            ) => {
                setLoadingResponses(
                    true,
                );

                setErrorMessage(
                    null,
                );

                try {
                    const loadedResponses =
                        await getScriptResponses(
                            scriptId,
                            "submitted",
                        );

                    setResponses(
                        loadedResponses,
                    );

                    setDrafts(
                        Object.fromEntries(
                            loadedResponses.map(
                                (response) => [
                                    response.id,
                                    {
                                        mark:
                                            response
                                                .marking_decision
                                                ?.mark_awarded
                                                ?.toString()
                                            ?? "",
                                        markerComment:
                                            response
                                                .marking_decision
                                                ?.marker_comment
                                            ?? "",
                                    },
                                ],
                            ),
                        ),
                    );
                } catch (
                    error
                ) {
                    setResponses(
                        [],
                    );

                    setDrafts(
                        {},
                    );

                    setErrorMessage(
                        error instanceof Error
                            ? error.message
                            : "Unable to load script responses.",
                    );
                } finally {
                    setLoadingResponses(
                        false,
                    );
                }
            },
            [],
        );


    useEffect(
        () => {
            void refreshCandidates();
        },
        [
            refreshCandidates,
        ],
    );


    useEffect(
        () => {
            if (
                selectedScriptId === null
            ) {
                setResponses(
                    [],
                );

                setDrafts(
                    {},
                );

                return;
            }

            void refreshResponses(
                selectedScriptId,
            );
        },
        [
            refreshResponses,
            selectedScriptId,
        ],
    );


    function updateDraft(
        responseId: number,
        patch: Partial<DraftState>,
    ): void {
        setDrafts(
            (
                current,
            ) => ({
                ...current,

                [responseId]: {
                    mark:
                        current[responseId]?.mark
                        ?? "",

                    markerComment:
                        current[responseId]
                            ?.markerComment
                        ?? "",

                    ...patch,
                },
            }),
        );
    }


    function replaceDecision(
        responseId: number,
        decision: MarkingDecision,
    ): void {
        setResponses(
            (
                current,
            ) => (
                current.map(
                    (response) => (
                        response.id === responseId
                            ? {
                                ...response,
                                marking_decision:
                                    decision,
                            }
                            : response
                    ),
                )
            ),
        );

        setDrafts(
            (
                current,
            ) => ({
                ...current,

                [responseId]: {
                    mark:
                        decision
                            .mark_awarded
                            ?.toString()
                        ?? "",

                    markerComment:
                        decision
                            .marker_comment
                        ?? "",
                },
            }),
        );
    }


    async function ensureDecision(
        response: AssessmentResponse,
    ): Promise<MarkingDecision> {
        if (
            response.marking_decision
        ) {
            return response.marking_decision;
        }

        const decision =
            await createMarkingDecision(
                response.id,
            );

        replaceDecision(
            response.id,
            decision,
        );

        return decision;
    }


    async function handleConflict(
        error: unknown,
    ): Promise<boolean> {
        if (
            !(error instanceof ApiError)
            || error.status !== 409
        ) {
            return false;
        }

        setErrorMessage(
            `${error.message} The latest marking data has been reloaded.`,
        );

        if (
            selectedScriptId !== null
        ) {
            await refreshResponses(
                selectedScriptId,
            );
        }

        return true;
    }


    async function handleQuickMark(
        response: AssessmentResponse,
        mark: number,
    ): Promise<void> {
        if (
            selectedScript?.status
            !== "marking"
        ) {
            return;
        }

        if (
            isDecisionReadOnly(
                response.marking_decision,
            )
        ) {
            return;
        }

        const question =
            response.question_snapshot;

        const maximumMark =
            question
                ? asFiniteNumber(
                    question.maximum_mark,
                )
                : null;

        if (
            mark < 0
            || (
                maximumMark !== null
                && mark > maximumMark
            )
        ) {
            setErrorMessage(
                "The mark is outside the permitted range for this question.",
            );

            return;
        }

        setSavingResponseId(
            response.id,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        try {
            const decision =
                await ensureDecision(
                    response,
                );

            const updated =
                await instantMarkDecision(
                    decision.id,
                    {
                        mark_awarded:
                            mark,

                        expected_revision:
                            decision.revision,
                    },
                );

            replaceDecision(
                response.id,
                updated,
            );

            setSuccessMessage(
                `Question ${question?.question_number ?? response.question_id} marked.`,
            );
        } catch (
            error
        ) {
            if (
                await handleConflict(
                    error,
                )
            ) {
                return;
            }

            setErrorMessage(
                error instanceof Error
                    ? error.message
                    : "Unable to save the mark.",
            );
        } finally {
            setSavingResponseId(
                null,
            );
        }
    }


    async function handleSaveResponse(
        response: AssessmentResponse,
    ): Promise<void> {
        if (
            selectedScript?.status
            !== "marking"
        ) {
            return;
        }

        if (
            isDecisionReadOnly(
                response.marking_decision,
            )
        ) {
            return;
        }

        const draft =
            drafts[response.id];

        if (!draft) {
            return;
        }

        const cleanedMark =
            draft.mark.trim();

        if (!cleanedMark) {
            setErrorMessage(
                "Enter a mark before saving.",
            );

            return;
        }

        const numericMark =
            Number(cleanedMark);

        if (
            !Number.isFinite(
                numericMark,
            )
            || numericMark < 0
        ) {
            setErrorMessage(
                "Enter a valid non-negative mark.",
            );

            return;
        }

        const question =
            response.question_snapshot;

        const maximumMark =
            question
                ? asFiniteNumber(
                    question.maximum_mark,
                )
                : null;

        if (
            maximumMark !== null
            && numericMark > maximumMark
        ) {
            setErrorMessage(
                `The maximum mark for this question is ${maximumMark}.`,
            );

            return;
        }

        setSavingResponseId(
            response.id,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        try {
            const decision =
                await ensureDecision(
                    response,
                );

            const updated =
                await updateMarkingDecision(
                    decision.id,
                    {
                        mark_awarded:
                            numericMark,

                        marker_comment:
                            draft.markerComment
                                .trim()
                            || null,

                        expected_revision:
                            decision.revision,
                    },
                );

            replaceDecision(
                response.id,
                updated,
            );

            setSuccessMessage(
                `Question ${question?.question_number ?? response.question_id} saved.`,
            );
        } catch (
            error
        ) {
            if (
                await handleConflict(
                    error,
                )
            ) {
                return;
            }

            setErrorMessage(
                error instanceof Error
                    ? error.message
                    : "Unable to save marking.",
            );
        } finally {
            setSavingResponseId(
                null,
            );
        }
    }


    async function handleStartScript(): Promise<void> {
        if (
            !selectedWorkspaceItem
            || selectedWorkspaceItem
                .script.status
                !== "submitted"
        ) {
            return;
        }

        setScriptActionPending(
            true,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        try {
            const updatedScript =
                await startAssessmentScriptMarking(
                    selectedWorkspaceItem
                        .script.id,
                );

            setWorkspaceItems(
                (
                    current,
                ) => (
                    current.map(
                        (item) => (
                            item.script.id
                            === updatedScript.id
                                ? {
                                    ...item,
                                    script:
                                        updatedScript,
                                }
                                : item
                        ),
                    )
                ),
            );

            setSuccessMessage(
                "Marking started.",
            );
        } catch (
            error
        ) {
            setErrorMessage(
                error instanceof Error
                    ? error.message
                    : "Unable to start marking.",
            );
        } finally {
            setScriptActionPending(
                false,
            );
        }
    }


    async function handleCompleteScript(): Promise<void> {
        if (
            !selectedWorkspaceItem
            || selectedWorkspaceItem
                .script.status
                !== "marking"
            || !allResponsesMarked
        ) {
            return;
        }

        setScriptActionPending(
            true,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        try {
            const updatedScript =
                await completeAssessmentScriptMarking(
                    selectedWorkspaceItem
                        .script.id,
                );

            setWorkspaceItems(
                (
                    current,
                ) => (
                    current.map(
                        (item) => (
                            item.script.id
                            === updatedScript.id
                                ? {
                                    ...item,
                                    script:
                                        updatedScript,
                                }
                                : item
                        ),
                    )
                ),
            );

            setSuccessMessage(
                "Primary marking completed for this script.",
            );
        } catch (
            error
        ) {
            setErrorMessage(
                error instanceof Error
                    ? error.message
                    : "Unable to complete marking.",
            );
        } finally {
            setScriptActionPending(
                false,
            );
        }
    }


    return (
        <section className="rounded-2xl border border-slate-700 bg-[#0E1433] text-white shadow-xl">
            <div className="border-b border-slate-700 px-6 py-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <h2 className="text-2xl font-semibold">
                            Marking
                        </h2>

                        <p className="mt-1 text-sm text-slate-300">
                            Mark submitted scripts question by question.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={
                            () => {
                                void refreshCandidates();
                            }
                        }
                        disabled={
                            loadingCandidates
                            || scriptActionPending
                        }
                        className="rounded-lg border border-slate-500 px-4 py-2 text-sm font-medium transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Refresh
                    </button>
                </div>
            </div>

            {
                errorMessage
                ? (
                    <div className="mx-6 mt-5 rounded-lg border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                        {errorMessage}
                    </div>
                )
                : null
            }

            {
                successMessage
                    ? (
                        <div className="mx-6 mt-5 rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
                            {successMessage}
                        </div>
                    )
                    : null
            }

            <div className="grid min-h-[520px] lg:grid-cols-[280px_minmax(0,1fr)]">
                <aside className="border-b border-slate-700 p-4 lg:border-b-0 lg:border-r">
                    <div className="mb-3 flex items-center justify-between">
                        <h3 className="font-semibold">
                            Scripts
                        </h3>

                        <span className="text-xs text-slate-400">
                            {workspaceItems.length}
                        </span>
                    </div>

                    {
                        loadingCandidates
                            ? (
                                <p className="text-sm text-slate-400">
                                    Loading candidates…
                                </p>
                            )
                            : workspaceItems.length === 0
                                ? (
                                    <div className="rounded-lg border border-dashed border-slate-600 p-4 text-sm text-slate-400">
                                        No submitted scripts are currently available for marking.
                                    </div>
                                )
                                : (
                                    <div className="space-y-2">
                                        {
                                            workspaceItems.map(
                                                ({
                                                    candidate,
                                                    script,
                                                }) => {
                                                    const selected =
                                                        script.id
                                                        === selectedScriptId;

                                                    return (
                                                        <button
                                                            key={
                                                                script.id
                                                            }
                                                            type="button"
                                                            onClick={
                                                                () => {
                                                                    setSelectedScriptId(
                                                                        script.id,
                                                                    );

                                                                    setSuccessMessage(
                                                                        null,
                                                                    );

                                                                    setErrorMessage(
                                                                        null,
                                                                    );
                                                                }
                                                            }
                                                            className={[
                                                                "w-full rounded-xl border px-4 py-3 text-left transition",
                                                                selected
                                                                    ? "border-blue-400 bg-blue-500/20"
                                                                    : "border-slate-700 bg-white/5 hover:bg-white/10",
                                                            ].join(
                                                                " ",
                                                            )}
                                                        >
                                                            <div className="font-medium">
                                                                {
                                                                    getCandidateLabel(
                                                                        assessment,
                                                                        candidate,
                                                                    )
                                                                }
                                                            </div>

                                                            <div className="mt-1 flex items-center justify-between gap-2 text-xs text-slate-300">
                                                                <span>
                                                                    Script v{script.version}
                                                                </span>

                                                                <span>
                                                                    {
                                                                        getStatusLabel(
                                                                            script.status,
                                                                        )
                                                                    }
                                                                </span>
                                                            </div>
                                                        </button>
                                                    );
                                                },
                                            )
                                        }
                                    </div>
                                )
                    }
                </aside>

                <div className="min-w-0 p-5">
                    {
                        !selectedWorkspaceItem
                            ? (
                                <div className="flex min-h-[420px] items-center justify-center text-center text-slate-400">
                                    Select a submitted script to begin marking.
                                </div>
                            )
                            : (
                                <>
                                    {
                                        responses.length > 0
                                            ? (
                                                <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
                                                    <span className="font-medium text-slate-200">
                                                        Examiner tools:
                                                    </span>

                                                    {
                                                        loadingMarkingEvidence
                                                            ? (
                                                                <span className="text-slate-400">
                                                                    Loading…
                                                                </span>
                                                            )
                                                            : markingEvidenceError
                                                                ? (
                                                                    <span className="text-amber-300">
                                                                        {markingEvidenceError}
                                                                    </span>
                                                                )
                                                                : (
                                                                    <>
                                                                        <span className="text-slate-300">
                                                                            {
                                                                                markingPalette?.name
                                                                                ?? "No palette"
                                                                            }
                                                                        </span>

                                                                        <div className="flex items-center gap-2">
                                                                            {
                                                                                tickTool
                                                                                    ? (
                                                                                        <button
                                                                                            type="button"
                                                                                            onClick={
                                                                                                () => {
                                                                                                    setSelectedMarkingToolId(
                                                                                                        tickTool.id,
                                                                                                    );
                                                                                                }
                                                                                            }
                                                                                            aria-pressed={
                                                                                                selectedMarkingToolId
                                                                                                === tickTool.id
                                                                                            }
                                                                                            className={[
                                                                                                "flex h-9 min-w-9 items-center justify-center rounded-lg border px-3 text-xl font-bold leading-none transition",
                                                                                                selectedMarkingToolId
                                                                                                === tickTool.id
                                                                                                    ? "border-blue-400 bg-blue-500/20 text-red-500"
                                                                                                    : "border-slate-600 bg-slate-900/40 text-red-500 hover:bg-slate-800",
                                                                                            ].join(
                                                                                                " ",
                                                                                            )}
                                                                                            title={
                                                                                                tickTool.label
                                                                                            }
                                                                                        >
                                                                                            ✓
                                                                                        </button>
                                                                                    )
                                                                                    : null
                                                                            }

                                                                            {
                                                                                crossTool
                                                                                    ? (
                                                                                        <button
                                                                                            type="button"
                                                                                            onClick={
                                                                                                () => {
                                                                                                    setSelectedMarkingToolId(
                                                                                                        crossTool.id,
                                                                                                    );
                                                                                                }
                                                                                            }
                                                                                            aria-pressed={
                                                                                                selectedMarkingToolId
                                                                                                === crossTool.id
                                                                                            }
                                                                                            className={[
                                                                                                "flex h-9 min-w-9 items-center justify-center rounded-lg border px-3 text-xl font-bold leading-none transition",
                                                                                                selectedMarkingToolId
                                                                                                === crossTool.id
                                                                                                    ? "border-blue-400 bg-blue-500/20 text-red-500"
                                                                                                    : "border-slate-600 bg-slate-900/40 text-red-500 hover:bg-slate-800",
                                                                                            ].join(
                                                                                                " ",
                                                                                            )}
                                                                                            title={
                                                                                                crossTool.label
                                                                                            }
                                                                                        >
                                                                                            ✗
                                                                                        </button>
                                                                                    )
                                                                                    : null
                                                                            }
                                                                        </div>

                                                                        {
                                                                            !tickTool
                                                                            || !crossTool
                                                                                ? (
                                                                                    <span className="text-amber-300">
                                                                                        Tick/cross tools are not available in this palette.
                                                                                    </span>
                                                                                )
                                                                                : null
                                                                        }

                                                                        <span className="text-slate-500">
                                                                            •
                                                                        </span>

                                                                        <span className="text-slate-300">
                                                                            {
                                                                                Object.values(
                                                                                    markingAnnotations,
                                                                                ).reduce(
                                                                                    (
                                                                                        total,
                                                                                        items,
                                                                                    ) => (
                                                                                        total
                                                                                        + items.length
                                                                                    ),
                                                                                    0,
                                                                                )
                                                                            } examiner marks loaded
                                                                        </span>
                                                                    </>
                                                                )
                                                    }
                                                </div>
                                            )
                                            : null
                                    }

                                    <div className="mb-5 flex flex-wrap items-start justify-between gap-4 rounded-xl border border-slate-700 bg-white/5 p-4">
                                        <div>
                                            <h3 className="text-lg font-semibold">
                                                {
                                                    getCandidateLabel(
                                                        assessment,
                                                        selectedWorkspaceItem.candidate,
                                                    )
                                                }
                                            </h3>

                                            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-300">
                                                <span>
                                                    Script version{" "}
                                                    {
                                                        selectedWorkspaceItem
                                                            .script.version
                                                    }
                                                </span>

                                                <span>
                                                    Status:{" "}
                                                    {
                                                        getStatusLabel(
                                                            selectedWorkspaceItem
                                                                .script.status,
                                                        )
                                                    }
                                                </span>
                                            </div>

                                            <div className="mt-4 grid gap-3 sm:grid-cols-3">
                                                <div className="rounded-xl border border-blue-400/30 bg-blue-500/10 px-4 py-3">
                                                    <div className="text-xs font-semibold uppercase tracking-wide text-blue-200">
                                                        Current total
                                                    </div>

                                                    <div className="mt-1 text-2xl font-bold text-white">
                                                        {runningTotal}
                                                        <span className="text-base font-medium text-slate-300">
                                                            {" "}/ {maximumTotal}
                                                        </span>
                                                    </div>
                                                </div>

                                                <div className="rounded-xl border border-slate-600 bg-black/20 px-4 py-3">
                                                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                                                        Questions marked
                                                    </div>

                                                    <div className="mt-1 text-2xl font-bold text-white">
                                                        {markedCount}
                                                        <span className="text-base font-medium text-slate-300">
                                                            {" "}/ {responses.length}
                                                        </span>
                                                    </div>
                                                </div>

                                                <div className="rounded-xl border border-slate-600 bg-black/20 px-4 py-3">
                                                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                                                        Current percentage
                                                    </div>

                                                    <div className="mt-1 text-2xl font-bold text-white">
                                                        {runningPercentage.toFixed(1)}%
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="mt-3">
                                                <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
                                                    <span>
                                                        Marking progress
                                                    </span>

                                                    <span>
                                                        {Math.round(markingProgressPercentage)}%
                                                    </span>
                                                </div>

                                                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                                                    <div
                                                        className="h-full rounded-full bg-blue-500 transition-[width] duration-300"
                                                        style={{
                                                            width:
                                                                `${markingProgressPercentage}%`,
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex flex-wrap gap-2">
                                            {
                                                selectedWorkspaceItem
                                                    .script.status
                                                    === "submitted"
                                                    ? (
                                                        <button
                                                            type="button"
                                                            onClick={
                                                                () => {
                                                                    void handleStartScript();
                                                                }
                                                            }
                                                            disabled={
                                                                scriptActionPending
                                                            }
                                                            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                                                        >
                                                            Start marking
                                                        </button>
                                                    )
                                                    : null
                                            }

                                            {
                                                selectedWorkspaceItem
                                                    .script.status
                                                    === "marking"
                                                    ? (
                                                        <button
                                                            type="button"
                                                            onClick={
                                                                () => {
                                                                    void handleCompleteScript();
                                                                }
                                                            }
                                                            disabled={
                                                                scriptActionPending
                                                                || !allResponsesMarked
                                                            }
                                                            title={
                                                                allResponsesMarked
                                                                    ? "Complete primary marking"
                                                                    : "Mark every response before completing the script"
                                                            }
                                                            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
                                                        >
                                                            Complete marking
                                                        </button>
                                                    )
                                                    : null
                                            }
                                        </div>
                                    </div>

                                    {
                                        loadingResponses
                                            ? (
                                                <p className="py-10 text-center text-slate-400">
                                                    Loading responses…
                                                </p>
                                            )
                                            : responses.length === 0
                                                ? (
                                                    <div className="rounded-xl border border-dashed border-slate-600 p-8 text-center text-slate-400">
                                                        No submitted question responses were found for this script.
                                                    </div>
                                                )
                                                : (
                                                    <div className="space-y-5">
                                                        {
                                                            responses.map(
                                                                (
                                                                    response,
                                                                ) => {
                                                                    const question =
                                                                        response.question_snapshot;

                                                                    const decision =
                                                                        response.marking_decision;

                                                                    const draft =
                                                                        drafts[response.id]
                                                                        ?? {
                                                                            mark: "",
                                                                            markerComment: "",
                                                                        };

                                                                    const maximumMark =
                                                                        question
                                                                            ? asFiniteNumber(
                                                                                question.maximum_mark,
                                                                            )
                                                                            : null;

                                                                    const quickMarks =
                                                                        getQuickMarks(
                                                                            question,
                                                                        );

                                                                    const awardedMark =
                                                                        decision
                                                                            ?.mark_awarded
                                                                        !== null
                                                                        && decision
                                                                            ?.mark_awarded
                                                                        !== undefined
                                                                            ? asFiniteNumber(
                                                                                decision
                                                                                    .mark_awarded,
                                                                            )
                                                                            : null;

                                                                    const readOnly =
                                                                        isDecisionReadOnly(
                                                                            decision,
                                                                        )
                                                                        || selectedWorkspaceItem
                                                                            .script.status
                                                                            !== "marking";

                                                                    const saving =
                                                                        savingResponseId
                                                                        === response.id;

                                                                    return (
                                                                        <article
                                                                            key={
                                                                                response.id
                                                                            }
                                                                            className="rounded-2xl border border-slate-700 bg-white/[0.04] p-5"
                                                                        >
                                                                            <div className="flex flex-wrap items-start justify-between gap-4">
                                                                                <div className="min-w-0">
                                                                                    <div className="text-sm font-semibold tracking-wide text-blue-300">
                                                                                        <span className="uppercase">
                                                                                            Question
                                                                                        </span>
                                                                                        {" "}
                                                                                        <span className="normal-case">
                                                                                            {
                                                                                                question
                                                                                                    ?.question_number
                                                                                                ?? response.question_id
                                                                                            }
                                                                                        </span>
                                                                                    </div>

                                                                                    {
                                                                                        question?.title
                                                                                            ? (
                                                                                                <h4 className="mt-1 text-lg font-semibold">
                                                                                                    {question.title}
                                                                                                </h4>
                                                                                            )
                                                                                            : null
                                                                                    }

                                                                                    {
                                                                                        question?.prompt
                                                                                            ? (
                                                                                                <p className="mt-2 whitespace-pre-wrap text-slate-200">
                                                                                                    {question.prompt}
                                                                                                </p>
                                                                                            )
                                                                                            : null
                                                                                    }
                                                                                </div>

                                                                                <div className="shrink-0 rounded-xl border border-slate-600 bg-black/20 px-4 py-3 text-right">
                                                                                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                                                                                        Question score
                                                                                    </div>

                                                                                    <div className="mt-1 text-xl font-bold text-white">
                                                                                        {
                                                                                            awardedMark
                                                                                            ?? "—"
                                                                                        }
                                                                                        <span className="text-base font-medium text-slate-400">
                                                                                            {" "}/ {
                                                                                                maximumMark
                                                                                                ?? "—"
                                                                                            }
                                                                                        </span>
                                                                                    </div>
                                                                                </div>
                                                                            </div>

                                                                            <div className="mt-5 rounded-xl border border-slate-300 bg-white p-4 text-slate-950 shadow-sm">
                                                                                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                                                    Candidate response
                                                                                </div>

                                                                                {
                                                                                    response.response_text
                                                                                        ? (
                                                                                            <div className="whitespace-pre-wrap text-base leading-7 text-slate-950">
                                                                                                {
                                                                                                    response.response_text
                                                                                                }
                                                                                            </div>
                                                                                        )
                                                                                        : null
                                                                                }

                                                                                {
                                                                                    response.response_data
                                                                                        ? (
                                                                                            <div
                                                                                                className={
                                                                                                    response.response_text
                                                                                                        ? "mt-3"
                                                                                                        : ""
                                                                                                }
                                                                                            >
                                                                                                <StructuredResponseContent
                                                                                                    response={
                                                                                                        response
                                                                                                    }
                                                                                                />
                                                                                            </div>
                                                                                        )
                                                                                        : null
                                                                                }

                                                                                {
                                                                                    !response.response_text
                                                                                    && !response.response_data
                                                                                        ? (
                                                                                            <p className="text-sm italic text-slate-400">
                                                                                                No response content recorded.
                                                                                            </p>
                                                                                        )
                                                                                        : null
                                                                                }
                                                                            </div>

                                                                            <div className="mt-5 grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
                                                                                <div>
                                                                                    <label
                                                                                        htmlFor={
                                                                                            `mark-${response.id}`
                                                                                        }
                                                                                        className="mb-2 block text-sm font-medium"
                                                                                    >
                                                                                        Mark awarded
                                                                                    </label>

                                                                                    <div className="flex items-center gap-2">
                                                                                        <input
                                                                                            id={
                                                                                                `mark-${response.id}`
                                                                                            }
                                                                                            type="number"
                                                                                            min="0"
                                                                                            max={
                                                                                                maximumMark
                                                                                                ?? undefined
                                                                                            }
                                                                                            step="0.5"
                                                                                            value={
                                                                                                draft.mark
                                                                                            }
                                                                                            disabled={
                                                                                                readOnly
                                                                                                || saving
                                                                                            }
                                                                                            onChange={
                                                                                                (
                                                                                                    event,
                                                                                                ) => {
                                                                                                    updateDraft(
                                                                                                        response.id,
                                                                                                        {
                                                                                                            mark:
                                                                                                                event.target.value,
                                                                                                        },
                                                                                                    );
                                                                                                }
                                                                                            }
                                                                                            className="w-full rounded-lg border border-slate-600 bg-slate-950/60 px-3 py-2 text-white outline-none focus:border-blue-400 disabled:cursor-not-allowed disabled:opacity-50"
                                                                                        />

                                                                                        {
                                                                                            maximumMark !== null
                                                                                                ? (
                                                                                                    <span className="whitespace-nowrap text-sm text-slate-400">
                                                                                                        / {maximumMark}
                                                                                                    </span>
                                                                                                )
                                                                                                : null
                                                                                        }
                                                                                    </div>

                                                                                    {
                                                                                        quickMarks.length > 0
                                                                                        && !readOnly
                                                                                            ? (
                                                                                                <div className="mt-3 flex flex-wrap gap-2">
                                                                                                    {
                                                                                                        quickMarks.map(
                                                                                                            (
                                                                                                                mark,
                                                                                                            ) => (
                                                                                                                <button
                                                                                                                    key={
                                                                                                                        mark
                                                                                                                    }
                                                                                                                    type="button"
                                                                                                                    disabled={
                                                                                                                        saving
                                                                                                                    }
                                                                                                                    onClick={
                                                                                                                        () => {
                                                                                                                            void handleQuickMark(
                                                                                                                                response,
                                                                                                                                mark,
                                                                                                                            );
                                                                                                                        }
                                                                                                                    }
                                                                                                                    className="min-w-9 rounded-md border border-blue-400/50 bg-blue-500/10 px-2 py-1 text-sm font-semibold hover:bg-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                                                                                                                >
                                                                                                                    {mark}
                                                                                                                </button>
                                                                                                            ),
                                                                                                        )
                                                                                                    }
                                                                                                </div>
                                                                                            )
                                                                                            : null
                                                                                    }
                                                                                </div>

                                                                                <div>
                                                                                    <label
                                                                                        htmlFor={
                                                                                            `comment-${response.id}`
                                                                                        }
                                                                                        className="mb-2 block text-sm font-medium"
                                                                                    >
                                                                                        Marker comment
                                                                                    </label>

                                                                                    <textarea
                                                                                        id={
                                                                                            `comment-${response.id}`
                                                                                        }
                                                                                        rows={
                                                                                            3
                                                                                        }
                                                                                        value={
                                                                                            draft.markerComment
                                                                                        }
                                                                                        disabled={
                                                                                            readOnly
                                                                                            || saving
                                                                                        }
                                                                                        onChange={
                                                                                            (
                                                                                                event,
                                                                                            ) => {
                                                                                                updateDraft(
                                                                                                    response.id,
                                                                                                    {
                                                                                                        markerComment:
                                                                                                            event.target.value,
                                                                                                    },
                                                                                                );
                                                                                            }
                                                                                        }
                                                                                        className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-950 outline-none focus:border-blue-500 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500"
                                                                                    />
                                                                                </div>
                                                                            </div>

                                                                            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-700 pt-4">
                                                                                <div className="text-xs text-slate-400">
                                                                                    {
                                                                                        decision
                                                                                            ? (
                                                                                                <>
                                                                                                    Status:{" "}
                                                                                                    {
                                                                                                        getStatusLabel(
                                                                                                            decision.status,
                                                                                                        )
                                                                                                    }
                                                                                                    {" · "}
                                                                                                    Revision{" "}
                                                                                                    {
                                                                                                        decision.revision
                                                                                                    }
                                                                                                </>
                                                                                            )
                                                                                            : (
                                                                                                "Not yet marked"
                                                                                            )
                                                                                    }
                                                                                </div>

                                                                                {
                                                                                    selectedWorkspaceItem
                                                                                        .script.status
                                                                                        === "marking"
                                                                                        ? (
                                                                                            <button
                                                                                                type="button"
                                                                                                disabled={
                                                                                                    readOnly
                                                                                                    || saving
                                                                                                }
                                                                                                onClick={
                                                                                                    () => {
                                                                                                        void handleSaveResponse(
                                                                                                            response,
                                                                                                        );
                                                                                                    }
                                                                                                }
                                                                                                className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                                                                                            >
                                                                                                {
                                                                                                    saving
                                                                                                        ? "Saving…"
                                                                                                        : "Save mark"
                                                                                                }
                                                                                            </button>
                                                                                        )
                                                                                        : null
                                                                                }
                                                                            </div>
                                                                        </article>
                                                                    );
                                                                },
                                                            )
                                                        }
                                                    </div>
                                                )
                                    }
                                </>
                            )
                    }
                </div>
            </div>
        </section>
    );
}
