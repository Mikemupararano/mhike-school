"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
    type MouseEvent,
    type PointerEvent,
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
    createMarkingAnnotation,
    createMarkingDecision,
    deleteMarkingAnnotation,
    getAssessmentResponseAssetBlob,
    getMarkingAnnotations,
    getMarkingDecision,
    getScriptMarkingAnnotations,
    getScriptMarkingPalette,
    getScriptResponses,
    instantMarkDecision,
    updateMarkingAnnotation,
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
                                    className="rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-base font-semibold text-slate-950"
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


const LEVEL_RESPONSE_CODES =
    new Set([
        "L1^1",
        "L1",
        "L2^2",
        "L2",
        "L3^",
        "L3",
    ]);

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
        activeResponseIndex,
        setActiveResponseIndex,
    ] = useState(0);
    useEffect(
        () => {
            setActiveResponseIndex(0);
        },
        [
            selectedScriptId,
        ],
    );

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
        deleteMode,
        setDeleteMode,
    ] = useState(false);

    const [
        annotationSavingResponseId,
        setAnnotationSavingResponseId,
    ] = useState<number | null>(
        null,
    );

    const [
        selectedAnnotationId,
        setSelectedAnnotationId,
    ] = useState<number | null>(
        null,
    );

    const [
        annotationDrag,
        setAnnotationDrag,
    ] = useState<{
        annotationId: number;
        responseId: number;
        x: number;
        y: number;
        moved: boolean;
    } | null>(
        null,
    );

    const [

        pendingTextAnnotation,

        setPendingTextAnnotation,

    ] = useState<{

        responseId: number;

        toolId: number;

        x: number;

        y: number;

        text: string;

    } | null>(

        null,

    );

    const [
        pendingLine,
        setPendingLine,
    ] = useState<{
        responseId: number;
        toolId: number;
        annotationType: "line" | "arrow";
        startX: number;
        startY: number;
        currentX: number;
        currentY: number;
        pointerId: number;
        boundsLeft: number;
        boundsTop: number;
        boundsWidth: number;
        boundsHeight: number;
    } | null>(
        null,
    );
    const linePreviewRef =
        useRef<SVGLineElement | null>(
            null,
        );


    const [

        pendingHighlight,

        setPendingHighlight,

    ] = useState<{

        responseId: number;

        toolId: number;

        startX: number;

        startY: number;

        currentX: number;

        currentY: number;

        pointerId: number;

    } | null>(

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


    /*
     * Load the examiner palette directly from the selected script.
     *
     * A session cache keeps the toolbox visible immediately when the
     * examiner revisits this assessment. The backend request still runs
     * in the background and remains authoritative.
     */
    useEffect(
        () => {
            let cancelled = false;

            if (selectedScriptId === null) {
                setMarkingPalette(
                    null,
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

            const cacheKey =
                `mhike-marking-palette-assessment-${assessment.id}`;

            let cachedPalette: MarkingPalette | null =
                null;

            try {
                const cachedValue =
                    window.sessionStorage.getItem(
                        cacheKey,
                    );

                if (cachedValue) {
                    cachedPalette =
                        JSON.parse(
                            cachedValue,
                        ) as MarkingPalette;

                    setMarkingPalette(
                        cachedPalette,
                    );
                }
            } catch {
                cachedPalette = null;
            }

            setLoadingMarkingEvidence(
                cachedPalette === null,
            );

            setMarkingEvidenceError(
                null,
            );

            const loadPalette =
                async (): Promise<void> => {
                    try {
                        const palette =
                            await getScriptMarkingPalette(
                                selectedScriptId,
                            );

                        if (cancelled) {
                            return;
                        }

                        setMarkingPalette(
                            palette,
                        );

                        try {
                            window.sessionStorage.setItem(
                                cacheKey,
                                JSON.stringify(
                                    palette,
                                ),
                            );
                        } catch {
                            // Session caching is optional.
                        }
                    } catch (
                        error
                    ) {
                        if (cancelled) {
                            return;
                        }

                        /*
                         * If a cached palette is already visible, keep it.
                         * A temporary refresh failure should not remove the
                         * examiner toolbox.
                         */
                        if (cachedPalette === null) {
                            setMarkingPalette(
                                null,
                            );
                        }

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

            void loadPalette();

            return () => {
                cancelled = true;
            };
        },
        [
            assessment.id,
            selectedScriptId,
        ],
    );
    /*
     * Existing examiner marks load independently.
     *
     * All annotations for the selected script are fetched in one
     * request and grouped by response id in the browser.
     *
     * Annotation loading must never disable or hide the marking palette.
     */
    useEffect(
        () => {
            let cancelled = false;

            if (selectedScriptId === null) {
                setMarkingAnnotations(
                    {},
                );

                return () => {
                    cancelled = true;
                };
            }

            const loadAnnotations =
                async (): Promise<void> => {
                    setMarkingAnnotations(
                        {},
                    );

                    try {
                        const annotations =
                            await getScriptMarkingAnnotations(
                                selectedScriptId,
                            );

                        if (cancelled) {
                            return;
                        }

                        const grouped:
                            Record<number, MarkingAnnotation[]> =
                            {};

                        for (const annotation of annotations) {
                            const responseId =
                                annotation.response_id;

                            if (!grouped[responseId]) {
                                grouped[responseId] = [];
                            }

                            grouped[responseId].push(
                                annotation,
                            );
                        }

                        setMarkingAnnotations(
                            grouped,
                        );

                        setMarkingEvidenceError(
                            null,
                        );
                    } catch (error) {
                        if (cancelled) {
                            return;
                        }

                        console.error(
                            `Unable to load examiner annotations for script ${selectedScriptId}.`,
                            error,
                        );

                        setMarkingAnnotations(
                            {},
                        );

                        setMarkingEvidenceError(
                            error instanceof Error
                                ? error.message
                                : "Unable to load examiner annotations.",
                        );
                    }
                };

            void loadAnnotations();

            return () => {
                cancelled = true;
            };
        },
        [
            selectedScriptId,
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
            const tools =
                markingPalette?.tools
                ?? [];

            if (deleteMode) {
                return;
            }

            if (
                selectedMarkingToolId !== null
                && tools.some(
                    (tool) => (
                        tool.id
                        === selectedMarkingToolId
                    ),
                )
            ) {
                return;
            }

            setSelectedMarkingToolId(
                tickTool?.id
                ?? crossTool?.id
                ?? tools[0]?.id
                ?? null,
            );
        },
        [
            crossTool,
            deleteMode,
            markingPalette,
            selectedMarkingToolId,
            tickTool,
        ],
    );


    const selectedMarkingTool =
        useMemo(
            () => (
                markingPalette?.tools.find(
                    (tool) => (
                        tool.id
                        === selectedMarkingToolId
                    ),
                )
                ?? null
            ),
            [
                markingPalette,
                selectedMarkingToolId,
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


    async function handleSaveTextAnnotation(
        response: AssessmentResponse,
    ): Promise<void> {
        const pending =
            pendingTextAnnotation;

        if (
            !pending
            || pending.responseId !== response.id
        ) {
            return;
        }

        const text =
            pending.text.trim();

        if (!text) {
            setErrorMessage(
                "Enter examiner text before saving.",
            );

            return;
        }

        setAnnotationSavingResponseId(
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

            const annotation =
                await createMarkingAnnotation(
                    response.id,
                    {
                        palette_tool_id:
                            pending.toolId,

                        expected_decision_revision:
                            decision.revision,

                        surface_type:
                            "response",

                        surface_reference:
                            null,

                        x:
                            pending.x,

                        y:
                            pending.y,

                        text,
                    },
                );

            setMarkingAnnotations(
                (current) => ({
                    ...current,

                    [response.id]: [
                        ...(
                            current[
                                response.id
                            ]
                            ?? []
                        ),

                        annotation,
                    ],
                }),
            );

            setPendingTextAnnotation(
                null,
            );

            setSelectedAnnotationId(
                annotation.id,
            );

            setSuccessMessage(
                "Text annotation added.",
            );
        } catch (error) {
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
                    : "Unable to add text annotation.",
            );
        } finally {
            setAnnotationSavingResponseId(
                null,
            );
        }
    }

    function handleLinePointerDown(
        response: AssessmentResponse,
        event: PointerEvent<HTMLDivElement>,
        readOnly: boolean,
    ): void {
        if (
            readOnly
            || !selectedMarkingTool
            || !["line", "arrow"].includes(selectedMarkingTool.tool_type)
            || annotationSavingResponseId === response.id
        ) {
            return;
        }

        const bounds =
            event.currentTarget.getBoundingClientRect();

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            return;
        }

        const x =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );

        const y =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientY
                        - bounds.top
                    ) / bounds.height,
                ),
            );

        event.preventDefault();
        event.stopPropagation();

        event.currentTarget.setPointerCapture(
            event.pointerId,
        );

        setSelectedAnnotationId(
            null,
        );

        setPendingLine({
            responseId:
                response.id,

            toolId:
                selectedMarkingTool.id,

            annotationType:
                selectedMarkingTool.tool_type === "arrow"
                    ? "arrow"
                    : "line",

            startX:
                x,

            startY:
                y,

            currentX:
                x,

            currentY:
                y,

            pointerId:
                event.pointerId,

            boundsLeft:
                bounds.left,

            boundsTop:
                bounds.top,

            boundsWidth:
                bounds.width,

            boundsHeight:
                bounds.height,
        });

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );
    }


    function handleLinePointerMove(
        response: AssessmentResponse,
        event: PointerEvent<HTMLDivElement>,
    ): void {
        if (
            !pendingLine
            || pendingLine.responseId !== response.id
            || pendingLine.pointerId !== event.pointerId
        ) {
            return;
        }

        const bounds = {
            left: pendingLine.boundsLeft,
            top: pendingLine.boundsTop,
            width: pendingLine.boundsWidth,
            height: pendingLine.boundsHeight,
        };

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            return;
        }

        const x =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );

        const y =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientY
                        - bounds.top
                    ) / bounds.height,
                ),
            );

        event.preventDefault();

        const preview =
            linePreviewRef.current;

        if (!preview) {
            return;
        }

        preview.setAttribute(
            "x2",
            `${x * 100}%`,
        );

        preview.setAttribute(
            "y2",
            `${y * 100}%`,
        );
    }

    async function handleLinePointerUp(
        response: AssessmentResponse,
        event: PointerEvent<HTMLDivElement>,
    ): Promise<void> {
        const pending =
            pendingLine;

        if (
            !pending
            || pending.responseId !== response.id
            || pending.pointerId !== event.pointerId
        ) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        if (
            event.currentTarget.hasPointerCapture(
                event.pointerId,
            )
        ) {
            event.currentTarget.releasePointerCapture(
                event.pointerId,
            );
        }

        const bounds = {
            left: pending.boundsLeft,
            top: pending.boundsTop,
            width: pending.boundsWidth,
            height: pending.boundsHeight,
        };

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            setPendingLine(
                null,
            );

            return;
        }

        const endX =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );

        const endY =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientY
                        - bounds.top
                    ) / bounds.height,
                ),
            );

        const distance =
            Math.hypot(
                endX - pending.startX,
                endY - pending.startY,
            );

        // Ignore an accidental click rather than a deliberate drag.
        if (distance < 0.005) {
            setPendingLine(
                null,
            );

            return;
        }

        /*
         * Freeze the live preview at the exact release point while the
         * annotation is persisted. Pointer-move remains DOM-driven, so
         * this causes only one React update per completed line.
         */
        setPendingLine({
            ...pending,
            currentX: endX,
            currentY: endY,
        });

        setAnnotationSavingResponseId(
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

            const annotation =
                await createMarkingAnnotation(
                    response.id,
                    {
                        palette_tool_id:
                            pending.toolId,

                        expected_decision_revision:
                            decision.revision,

                        surface_type:
                            "response",

                        surface_reference:
                            null,

                        x:
                            pending.startX,

                        y:
                            pending.startY,

                        end_x:
                            endX,

                        end_y:
                            endY,
                    },
                );

            setMarkingAnnotations(
                (current) => ({
                    ...current,

                    [response.id]:
                        [
                            ...(
                                current[
                                    response.id
                                ]
                                ?? []
                            ),
                            annotation,
                        ],
                }),
            );

            setSelectedAnnotationId(
                null,
            );

            /*
             * The persisted annotation is now present, so the temporary
             * live SVG can be removed without a visible gap.
             */
            setPendingLine(
                null,
            );

            setSuccessMessage(
                pending.annotationType === "arrow"
                    ? "Arrow added."
                    : "Line added.",
            );
        } catch (error) {
            setPendingLine(
                null,
            );
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
                    : pending.annotationType === "arrow"
                        ? "Unable to add marking arrow."
                        : "Unable to add marking line.",
            );
        } finally {
            setAnnotationSavingResponseId(
                null,
            );
        }
    }

    function handleHighlightPointerDown(
        response: AssessmentResponse,
        event: PointerEvent<HTMLDivElement>,
        readOnly: boolean,
    ): void {
        if (
            readOnly
            || selectedMarkingTool?.tool_type
            !== "highlight"
            || annotationSavingResponseId
            === response.id
        ) {
            return;
        }

        const bounds =
            event.currentTarget.getBoundingClientRect();

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            return;
        }

        const x =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );

        const y =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientY
                        - bounds.top
                    ) / bounds.height,
                ),
            );

        event.preventDefault();
        event.stopPropagation();

        event.currentTarget.setPointerCapture(
            event.pointerId,
        );

        setPendingTextAnnotation(
            null,
        );

        setSelectedAnnotationId(
            null,
        );

        setPendingHighlight({
            responseId:
                response.id,

            toolId:
                selectedMarkingTool.id,

            startX:
                x,

            startY:
                y,

            currentX:
                x,

            currentY:
                y,

            pointerId:
                event.pointerId,
        });

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );
    }


    function handleHighlightPointerMove(
        response: AssessmentResponse,
        event: PointerEvent<HTMLDivElement>,
    ): void {
        if (
            !pendingHighlight
            || pendingHighlight.responseId
            !== response.id
            || pendingHighlight.pointerId
            !== event.pointerId
        ) {
            return;
        }

        const bounds =
            event.currentTarget.getBoundingClientRect();

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            return;
        }

        const x =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );

        const y =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientY
                        - bounds.top
                    ) / bounds.height,
                ),
            );

        event.preventDefault();

        setPendingHighlight(
            (current) => (
                current
                && current.responseId
                === response.id
                && current.pointerId
                === event.pointerId
                    ? {
                        ...current,

                        currentX:
                            x,

                        currentY:
                            y,
                    }
                    : current
            ),
        );
    }


    async function handleHighlightPointerUp(
        response: AssessmentResponse,
        event: PointerEvent<HTMLDivElement>,
    ): Promise<void> {
        const pending =
            pendingHighlight;

        if (
            !pending
            || pending.responseId
            !== response.id
            || pending.pointerId
            !== event.pointerId
        ) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        if (
            event.currentTarget.hasPointerCapture(
                event.pointerId,
            )
        ) {
            event.currentTarget.releasePointerCapture(
                event.pointerId,
            );
        }

        const bounds =
            event.currentTarget.getBoundingClientRect();

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            setPendingHighlight(
                null,
            );

            return;
        }

        const endX =
            Math.max(
                0,
                Math.min(
                    1,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );
        const x =
            Math.min(
                pending.startX,
                endX,
            );

        /*
         * HIGHLIGHT behaves like a real marker pen:
         * horizontal drag controls the span while the
         * vertical thickness stays consistent.
         */
        const highlightPixelHeight =
            28;

        const height =
            Math.min(
                1,
                highlightPixelHeight
                / bounds.height,
            );

        const y =
            Math.max(
                0,
                Math.min(
                    1 - height,
                    pending.startY
                    - (
                        height / 2
                    ),
                ),
            );

        const width =
            Math.abs(
                endX
                - pending.startX,
            );

        setPendingHighlight(
            null,
        );

        /*
         * Ignore accidental taps. A highlight must have a
         * visible rectangular area.
         */
        if (
            width < 0.005
        ) {
            return;
        }

        setAnnotationSavingResponseId(
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

            const annotation =
                await createMarkingAnnotation(
                    response.id,
                    {
                        palette_tool_id:
                            pending.toolId,

                        expected_decision_revision:
                            decision.revision,

                        surface_type:
                            "response",

                        surface_reference:
                            null,

                        x,
                        y,

                        width,
                        height,
                    },
                );

            setMarkingAnnotations(
                (current) => ({
                    ...current,

                    [response.id]: [
                        ...(
                            current[
                                response.id
                            ]
                            ?? []
                        ),

                        annotation,
                    ],
                }),
            );

            setSelectedAnnotationId(
                annotation.id,
            );

            setSuccessMessage(
                "Highlight added.",
            );
        } catch (error) {
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
                    : "Unable to add highlight.",
            );
        } finally {
            setAnnotationSavingResponseId(
                null,
            );
        }
    }

    async function handleResponseAnnotationClick(
        response: AssessmentResponse,
        event: MouseEvent<HTMLDivElement>,
        readOnly: boolean,
    ): Promise<void> {
        if (
            readOnly
            || response.question_snapshot?.question_type
            === "diagram_annotation"
        ) {
            return;
        }

        if (
            !selectedMarkingTool
            || ![
                "symbol",
                "code",
                "text",
            ].includes(
                selectedMarkingTool.tool_type,
            )
        ) {
            return;
        }

        if (
            annotationSavingResponseId
            === response.id
        ) {
            return;
        }

        const bounds =
            event.currentTarget.getBoundingClientRect();

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            return;
        }

        const x =
            Math.min(
                1,
                Math.max(
                    0,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );

        const y =
            Math.min(
                1,
                Math.max(
                    0,
                    (
                        event.clientY
                        - bounds.top
                    ) / bounds.height,
                ),
            );

        const selectedTool =
            selectedMarkingTool;

        if (selectedTool.tool_type === "text") {
            const bounds =
                event.currentTarget.getBoundingClientRect();

            const x =
                Math.max(
                    0,
                    Math.min(
                        1,
                        (
                            event.clientX
                            - bounds.left
                        ) / bounds.width,
                    ),
                );

            const y =
                Math.max(
                    0,
                    Math.min(
                        1,
                        (
                            event.clientY
                            - bounds.top
                        ) / bounds.height,
                    ),
                );

            setPendingTextAnnotation({
                responseId:
                    response.id,

                toolId:
                    selectedTool.id,

                x,
                y,

                text:
                    "",
            });

            setSelectedAnnotationId(
                null,
            );

            setErrorMessage(
                null,
            );

            setSuccessMessage(
                null,
            );

            return;
        }
const isLevelResponseTool =
            LEVEL_RESPONSE_CODES.has(
                selectedTool.value,
            );

        const previousDecision =
            response.marking_decision;

        const previousAnnotations =
            markingAnnotations[
                response.id
            ]
            ?? [];

        const existingLevelAnnotation =
            isLevelResponseTool
                ? previousAnnotations.find(
                    (annotation) => (
                        annotation.value !== null
                        && LEVEL_RESPONSE_CODES.has(
                            annotation.value,
                        )
                    ),
                )
                ?? null
                : null;

        const questionMaximumMark =
            asFiniteNumber(
                response.question_snapshot?.maximum_mark
                ?? 0,
            )
            ?? 0;

        if (
            isLevelResponseTool
            && ![
                4,
                6,
            ].includes(
                questionMaximumMark,
            )
        ) {
            setErrorMessage(
                `Level-of-response tools require a 4-mark or 6-mark question. This response is currently reporting ${questionMaximumMark} marks.`,
            );

            return;
        }

        if (
            isLevelResponseTool
            && questionMaximumMark === 4
            && [
                "L3^",
                "L3",
            ].includes(
                selectedTool.value,
            )
        ) {
            setErrorMessage(
                `${selectedTool.value} is only available for 6-mark level-of-response questions.`,
            );

            return;
        }

        const temporaryAnnotationId =
            -response.id;

        const temporaryAnnotation: MarkingAnnotation = {
            id: temporaryAnnotationId,
            response_id: response.id,
            marker_id: null,
            palette_tool_id: selectedTool.id,
            annotation_type: selectedTool.tool_type,
            value: selectedTool.value,
            label_snapshot: null,
            text: null,
            surface_type: "response",
            surface_reference: null,
            page_number: null,
            x,
            y,
            end_x: null,
            end_y: null,
            width: null,
            height: null,
            revision: 0,
            created_at: "",
            updated_at: "",
            deleted_at: null,
            deleted_by_id: null,
        };

        /*
         * Optimistic marking:
         *
         * Paint the examiner symbol before making any network request.
         * The server-created annotation replaces this temporary row later.
         */
        setMarkingAnnotations(
            (current) => {
                const currentAnnotations =
                    current[
                        response.id
                    ]
                    ?? [];

                const retainedAnnotations =
                    isLevelResponseTool
                        ? currentAnnotations.filter(
                            (annotation) => (
                                annotation.value === null
                                || !LEVEL_RESPONSE_CODES.has(
                                    annotation.value,
                                )
                            ),
                        )
                        : currentAnnotations;

                return {
                    ...current,
                    [response.id]: [
                        ...retainedAnnotations,
                        temporaryAnnotation,
                    ],
                };
            },
        );

        /*
         * A tick contributes one mark. If a decision already exists,
         * reflect that change immediately as well.
         *
         * The authoritative server decision is reconciled below.
         */
        if (previousDecision) {
            if (
                selectedTool.value === "✓"
            ) {
                replaceDecision(
                    response.id,
                    {
                        ...previousDecision,
                        mark_awarded:
                            Number(
                                previousDecision.mark_awarded
                                ?? 0,
                            ) + 1,
                    },
                );
            }
        }

        setAnnotationSavingResponseId(
            response.id,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        try {
            let decision =
                await ensureDecision(
                    response,
                );

            if (
                isLevelResponseTool
                && existingLevelAnnotation
            ) {
                await deleteMarkingAnnotation(
                    existingLevelAnnotation.id,
                    {
                        revision:
                            existingLevelAnnotation.revision,

                        expected_decision_revision:
                            decision.revision,
                    },
                );

                decision =
                    await getMarkingDecision(
                        decision.id,
                    );
            }

            const annotation =
                await createMarkingAnnotation(
                    response.id,
                    {
                        palette_tool_id:
                            selectedTool.id,

                        expected_decision_revision:
                            decision.revision,

                        surface_type:
                            "response",

                        surface_reference:
                            null,

                        x,
                        y,
                    },
                );

            /*
             * Replace the temporary local annotation with the
             * authoritative annotation returned by the API.
             */
            setMarkingAnnotations(
                (current) => ({
                    ...current,
                    [response.id]:
                        (
                            current[
                                response.id
                            ]
                            ?? []
                        ).map(
                            (item) => (
                                item.id
                                === temporaryAnnotationId
                                    ? annotation
                                    : item
                            ),
                        ),
                }),
            );

            const authoritativeDecision =
                await getMarkingDecision(
                    decision.id,
                );


            replaceDecision(
                response.id,
                authoritativeDecision,
            );

            setSuccessMessage(
                isLevelResponseTool
                    ? `${selectedTool.value} added.`
                    : selectedTool.value === "✓"
                        ? "Tick added. 1 mark awarded."
                        : "Examiner mark added.",
            );
        } catch (
            error
        ) {
            /*
             * The save failed, so remove the optimistic annotation.
             */
            setMarkingAnnotations(
                (current) => ({
                    ...current,
                    [response.id]:
                        (
                            current[
                                response.id
                            ]
                            ?? []
                        ).filter(
                            (item) => (
                                item.id
                                !== temporaryAnnotationId
                            ),
                        ),
                }),
            );

            if (isLevelResponseTool) {
                setMarkingAnnotations(
                    (current) => ({
                        ...current,
                        [response.id]:
                            previousAnnotations,
                    }),
                );
            }
            /*
             * Restore the displayed score if we optimistically
             * incremented it.
             */
            if (
                selectedTool.value === "✓"
                && previousDecision
            ) {
                replaceDecision(
                    response.id,
                    previousDecision,
                );
            }

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
                    : "Unable to add examiner annotation.",
            );
        } finally {
            setAnnotationSavingResponseId(
                null,
            );
        }
    }

    function getAnnotationPointerPosition(
        event: PointerEvent<HTMLSpanElement>,
    ): {
        x: number;
        y: number;
    } | null {
        const surface =
            event.currentTarget.parentElement;

        if (!surface) {
            return null;
        }

        const bounds =
            surface.getBoundingClientRect();

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            return null;
        }

        return {
            x:
                Math.min(
                    1,
                    Math.max(
                        0,
                        (
                            event.clientX
                            - bounds.left
                        ) / bounds.width,
                    ),
                ),

            y:
                Math.min(
                    1,
                    Math.max(
                        0,
                        (
                            event.clientY
                            - bounds.top
                        ) / bounds.height,
                    ),
                ),
        };
    }


    function handleAnnotationPointerDown(
        response: AssessmentResponse,
        annotation: MarkingAnnotation,
        event: PointerEvent<HTMLSpanElement>,
        readOnly: boolean,
    ): void {
        if (readOnly) {
            return;
        }

        if (deleteMode) {
            event.preventDefault();
            event.stopPropagation();

            void handleDeleteAnnotation(
                response,
                annotation,
                readOnly,
            );

            return;
        }

        event.preventDefault();
        event.stopPropagation();

        event.currentTarget.setPointerCapture(
            event.pointerId,
        );

        setSelectedAnnotationId(
            annotation.id,
        );

        setAnnotationDrag({
            annotationId:
                annotation.id,

            responseId:
                response.id,

            x:
                Number(
                    annotation.x,
                ),

            y:
                Number(
                    annotation.y,
                ),

            moved:
                false,
        });
    }


    function handleAnnotationPointerMove(
        annotation: MarkingAnnotation,
        event: PointerEvent<HTMLSpanElement>,
    ): void {
        if (
            !annotationDrag
            || annotationDrag.annotationId
            !== annotation.id
        ) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const position =
            getAnnotationPointerPosition(
                event,
            );

        if (!position) {
            return;
        }

        const moved =
            annotationDrag.moved
            || Math.abs(
                position.x
                - Number(annotation.x),
            ) > 0.001
            || Math.abs(
                position.y
                - Number(annotation.y),
            ) > 0.001;

        setAnnotationDrag({
            ...annotationDrag,
            x: position.x,
            y: position.y,
            moved,
        });
    }


    async function handleAnnotationPointerUp(
        response: AssessmentResponse,
        annotation: MarkingAnnotation,
        event: PointerEvent<HTMLSpanElement>,
        readOnly: boolean,
    ): Promise<void> {
        event.preventDefault();
        event.stopPropagation();

        if (
            event.currentTarget.hasPointerCapture(
                event.pointerId,
            )
        ) {
            event.currentTarget.releasePointerCapture(
                event.pointerId,
            );
        }

        const drag =
            annotationDrag;

        setAnnotationDrag(
            null,
        );

        if (
            readOnly
            || !drag
            || drag.annotationId
            !== annotation.id
            || !drag.moved
        ) {
            return;
        }

        setAnnotationSavingResponseId(
            response.id,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        /*
         * Move immediately on screen. The PATCH below persists the same
         * coordinates. Moving an annotation must never change its score.
         */
        setMarkingAnnotations(
            (current) => ({
                ...current,

                [response.id]:
                    (
                        current[
                            response.id
                        ]
                        ?? []
                    ).map(
                        (item) => (
                            item.id === annotation.id
                                ? {
                                    ...item,
                                    x: drag.x,
                                    y: drag.y,
                                }
                                : item
                        ),
                    ),
            }),
        );

        try {
            const updated =
                await updateMarkingAnnotation(
                    annotation.id,
                    {
                        revision:
                            annotation.revision,

                        x:
                            drag.x,

                        y:
                            drag.y,
                    },
                );

            setMarkingAnnotations(
                (current) => ({
                    ...current,

                    [response.id]:
                        (
                            current[
                                response.id
                            ]
                            ?? []
                        ).map(
                            (item) => (
                                item.id === updated.id
                                    ? updated
                                    : item
                            ),
                        ),
                }),
            );

            setSuccessMessage(
                "Examiner mark moved.",
            );
        } catch (
            error
        ) {
            if (
                await handleConflict(
                    error,
                )
            ) {
                const latest =
                    await getMarkingAnnotations(
                        response.id,
                    );

                setMarkingAnnotations(
                    (current) => ({
                        ...current,
                        [response.id]:
                            latest,
                    }),
                );

                return;
            }

            /*
             * Revert the optimistic movement if persistence failed.
             */
            setMarkingAnnotations(
                (current) => ({
                    ...current,

                    [response.id]:
                        (
                            current[
                                response.id
                            ]
                            ?? []
                        ).map(
                            (item) => (
                                item.id === annotation.id
                                    ? annotation
                                    : item
                            ),
                        ),
                }),
            );

            setErrorMessage(
                error instanceof Error
                    ? error.message
                    : "Unable to move examiner annotation.",
            );
        } finally {
            setAnnotationSavingResponseId(
                null,
            );
        }
    }


    async function handleDeleteAnnotation(
        response: AssessmentResponse,
        annotation: MarkingAnnotation,
        readOnly: boolean,
    ): Promise<void> {
        if (
            readOnly
            || annotationSavingResponseId
            === response.id
        ) {
            return;
        }

        const previousAnnotations =
            markingAnnotations[
                response.id
            ]
            ?? [];

        const previousDecision =
            response.marking_decision;

        setAnnotationSavingResponseId(
            response.id,
        );

        setErrorMessage(
            null,
        );

        setSuccessMessage(
            null,
        );

        setSelectedAnnotationId(
            null,
        );

        // Optimistic UI:
        // remove the annotation immediately.
        setMarkingAnnotations(
            (current) => ({
                ...current,
                [response.id]:
                    (
                        current[
                            response.id
                        ]
                        ?? []
                    ).filter(
                        (item) => (
                            item.id
                            !== annotation.id
                        ),
                    ),
            }),
        );

        // A tick contributes one mark, so update
        // the displayed question score immediately.
        if (
            annotation.value === "✓"
            && previousDecision
        ) {
            replaceDecision(
                response.id,
                {
                    ...previousDecision,
                    mark_awarded:
                        Math.max(
                            0,
                            Number(
                                previousDecision
                                    .mark_awarded
                                ?? 0,
                            ) - 1,
                        ),
                },
            );
        }

        try {
            const decision =
                previousDecision
                ?? await ensureDecision(
                    response,
                );

            await deleteMarkingAnnotation(
                annotation.id,
                {
                    revision:
                        annotation.revision,

                    expected_decision_revision:
                        decision.revision,
                },
            );

            const authoritativeDecision =
                await getMarkingDecision(
                    decision.id,
                );

            replaceDecision(
                response.id,
                authoritativeDecision,
            );

            setSuccessMessage(
                annotation.value === "✓"
                    ? "Tick removed. Score updated."
                    : "Examiner mark removed.",
            );
        } catch (
            error
        ) {
            if (
                await handleConflict(
                    error,
                )
            ) {
                const latest =
                    await getMarkingAnnotations(
                        response.id,
                    );

                setMarkingAnnotations(
                    (current) => ({
                        ...current,
                        [response.id]:
                            latest,
                    }),
                );

                return;
            }

            // Server rejected the change:
            // restore the annotation immediately.
            setMarkingAnnotations(
                (current) => ({
                    ...current,
                    [response.id]:
                        previousAnnotations,
                }),
            );

            if (
                previousDecision
            ) {
                replaceDecision(
                    response.id,
                    previousDecision,
                );
            }

            setErrorMessage(
                error instanceof Error
                    ? error.message
                    : "Unable to remove examiner annotation.",
            );
        } finally {
            setAnnotationSavingResponseId(
                null,
            );
        }
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
            <div className="border-b border-slate-700 px-5 py-3">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <h2 className="text-lg font-semibold tracking-tight">
                            Marking
                        </h2>

                        <p className="mt-0.5 text-xs text-slate-400">
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
                        className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-semibold transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Refresh
                    </button>
                </div>
            </div>

            {
                errorMessage
                ? (
                    <div className="ml-auto mr-4 mt-3 w-fit max-w-xl rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-100 shadow-sm">
                        {errorMessage}
                    </div>
                )
                : null
            }

            {
                successMessage
                    ? (
                        <div className="ml-auto mr-4 mt-3 w-fit max-w-xl rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-100 shadow-sm">
                            {successMessage}
                        </div>
                    )
                    : null
            }

            <div className="grid min-h-[520px] lg:grid-cols-[215px_290px_minmax(0,1fr)]">
                <aside className="border-b border-slate-700 p-3 lg:border-b-0 lg:border-r">
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
                                                                "w-full rounded-xl border px-3 py-2.5 text-left transition",
                                                                selected
                                                                    ? "border-blue-400 bg-blue-500/20"
                                                                    : "border-slate-700 bg-white/5 hover:bg-white/10",
                                                            ].join(
                                                                " ",
                                                            )}
                                                        >
                                                            <div className="break-words text-sm font-semibold leading-5">
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

                <aside className="border-b border-slate-300 bg-slate-50 p-3 text-slate-900 lg:border-b-0 lg:border-r">
                    <div className="lg:sticky lg:top-4">
                        <div className="rounded-xl border border-slate-300 bg-white p-3 shadow-sm">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <div className="text-xs font-bold uppercase tracking-[0.18em] text-slate-900">
                                        Examiner tools
                                    </div>

                                    <div className="mt-1 text-xs text-slate-600">
                                        {
                                            markingPalette?.name
                                            ?? "Marking palette"
                                        }
                                    </div>
                                </div>

                                <div className="rounded-lg border border-slate-300 bg-slate-50 px-2.5 py-1 text-center shadow-sm">
                                    <div className="text-lg font-bold text-slate-950">
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
                                        }
                                    </div>

                                    <div className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">
                                        marks
                                    </div>
                                </div>
                            </div>

                            {
                                loadingMarkingEvidence
                                    ? (
                                        <div className="mt-5 rounded-xl border border-slate-700 bg-black/20 px-4 py-5 text-center text-sm text-slate-400">
                                            Loading marking tools…
                                        </div>
                                    )
                                    : markingEvidenceError
                                        ? (
                                            <div className="mt-5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-4 text-sm text-amber-200">
                                                {markingEvidenceError}
                                            </div>
                                        )
                                        : (
                                            <>
                                                <div className="mt-5">
                                                    <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-600">
                                                        Selected tool
                                                    </div>

                                                    <div className="flex min-h-14 items-center gap-3 rounded-xl border border-blue-300 bg-blue-50 px-4 py-3">
                                                        <div className="flex h-10 min-w-10 items-center justify-center rounded-lg border border-red-200 bg-red-50 px-2 text-xl font-bold text-red-600">
                                                            {
                                                                selectedMarkingTool?.value
                                                                ?? "—"
                                                            }
                                                        </div>

                                                        <div className="min-w-0">
                                                            <div className="truncate text-sm font-semibold text-slate-950">
                                                                {
                                                                    selectedMarkingTool?.label
                                                                    ?? "No tool selected"
                                                                }
                                                            </div>

                                                            <div className="mt-0.5 text-[11px] text-slate-400">
                                                                {
                                                                    selectedMarkingTool?.tool_type
                                                                    === "symbol"
                                                                        ? "Click directly on the response to place it."
                                                                        : "This drawing tool will be enabled in the next toolbox stage."
                                                                }
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="mt-4 grid grid-cols-2 gap-2">
                                                    <button
                                                        type="button"
                                                        aria-pressed={deleteMode}
                                                        title="Delete examiner marks"
                                                        onClick={
                                                            () => {
                                                                setDeleteMode(true);
                                                                setSelectedMarkingToolId(null);
                                                                setSelectedAnnotationId(null);
                                                                setAnnotationDrag(null);
                                                            }
                                                        }
                                                        className={[
                                                            "group min-h-16 rounded-lg border px-2.5 py-2 text-left transition",
                                                            deleteMode
                                                                ? "border-red-500 bg-red-50 ring-2 ring-red-200 shadow-sm"
                                                                : "border-slate-300 bg-white shadow-sm hover:border-red-400 hover:bg-red-50",
                                                        ].join(" ")}
                                                    >
                                                        <div className="flex items-center justify-between gap-2">
                                                            <span className="flex min-h-9 min-w-9 items-center justify-center rounded-lg border border-red-200 bg-red-50 px-2 text-xl font-bold leading-none text-red-600">
                                                                ⌫
                                                            </span>
                                                        </div>
                                                        <div className="mt-1.5 line-clamp-2 text-[11px] font-semibold leading-4 text-slate-900">
                                                            Delete mark
                                                        </div>
                                                    </button>
                                                    {
                                                        (
                                                            markingPalette?.tools
                                                            ?? []
                                                        ).map(
                                                            (tool) => {
                                                                const selected =
                                                                    tool.id
                                                                    === selectedMarkingToolId;

                                                                const placeable =
                                                                    tool.tool_type === "symbol"
                                                                    || tool.tool_type === "code"
                                                                    || tool.tool_type === "text"
                                                                    || tool.tool_type === "line"
                       || tool.tool_type === "arrow"
                        || tool.tool_type === "highlight";

                                                                return (
                                                                    <button
                                                                        key={
                                                                            tool.id
                                                                        }
                                                                        type="button"
                                                                        disabled={
                                                                            !placeable
                                                                        }
                                                                        onClick={
                                                                            () => {
                                                                                setDeleteMode(false);
                                                                        setSelectedMarkingToolId(
                                                                                    tool.id,
                                                                                );
                                                                            }
                                                                        }
                                                                        aria-pressed={
                                                                            selected
                                                                        }
                                                                        title={
                                                                            placeable
                                                                                ? tool.label
                                                                                : `${tool.label} — drawing interaction not enabled yet`
                                                                        }
                                                                        className={[
                                                                            "group min-h-16 rounded-lg border px-2.5 py-2 text-left transition",
                                                                            placeable
                                                                                ? "cursor-pointer"
                                                                                : "cursor-not-allowed opacity-65",
                                                                            selected
                                                                                ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200 shadow-sm"
                                                                                : "border-slate-300 bg-white shadow-sm hover:border-blue-400 hover:bg-blue-50",
                                                                        ].join(
                                                                            " ",
                                                                        )}
                                                                    >
                                                                        <div className="flex items-center justify-between gap-2">
                                                                            <span className="flex min-h-9 min-w-9 items-center justify-center rounded-lg border border-red-200 bg-red-50 px-2 text-xl font-bold leading-none text-red-600">
                                                                                {
                                                                                    tool.value
                                                                                    ?? tool.label.slice(
                                                                                        0,
                                                                                        2,
                                                                                    )
                                                                                }
                                                                            </span>

                                                                            {
                                                                                !placeable
                                                                                    ? (
                                                                                        <span className="text-[9px] font-semibold uppercase tracking-wide text-slate-500">
                                                                                            soon
                                                                                        </span>
                                                                                    )
                                                                                    : null
                                                                            }
                                                                        </div>

                                                                        <div className="mt-1.5 line-clamp-2 text-[11px] font-semibold leading-4 text-slate-900">
                                                                            {
                                                                                tool.label
                                                                            }
                                                                        </div>
                                                                    </button>
                                                                );
                                                            },
                                                        )
                                                    }
                                                </div>

                                                {
                                                    (
                                                        markingPalette?.tools.length
                                                        ?? 0
                                                    ) === 0
                                                        ? (
                                                            <div className="mt-4 rounded-xl border border-dashed border-slate-700 p-4 text-center text-sm text-slate-400">
                                                                No marking tools are available.
                                                            </div>
                                                        )
                                                        : null
                                                }

                                                <div className="mt-5 border-t border-slate-300 pt-4 text-[11px] leading-5 text-slate-600">
                                                    Choose a symbol, then click where it should appear on the candidate response.
                                                    The selected tool stays active until you choose another one.
                                                </div>
                                            </>
                                        )
                            }
                        </div>
                    </div>
                </aside>
                <div className="min-w-0 p-4 xl:p-5">
                    {
                        !selectedWorkspaceItem
                            ? (
                                <div className="flex min-h-[420px] items-center justify-center text-center text-slate-400">
                                    Select a submitted script to begin marking.
                                </div>
                            )
                            : (
                                <>
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
                                                        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-700 bg-black/20 px-4 py-3">
                                                            <button
                                                                type="button"
                                                                disabled={
                                                                    activeResponseIndex <= 0
                                                                }
                                                                onClick={
                                                                    () => {
                                                                        setSelectedAnnotationId(null);
                                                                        setAnnotationDrag(null);
                                                                        setActiveResponseIndex(
                                                                            current => Math.max(
                                                                                0,
                                                                                current - 1,
                                                                            ),
                                                                        );
                                                                    }
                                                                }
                                                                className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-white transition hover:border-blue-400 hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                                                            >
                                                                ← Previous
                                                            </button>

                                                            <div className="text-center">
                                                                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                                                                    Current question
                                                                </div>
                                                                <div className="mt-1 text-sm font-bold text-white">
                                                                    {
                                                                        responses[
                                                                            activeResponseIndex
                                                                        ]?.question_snapshot
                                                                            ?.question_number
                                                                        ?? activeResponseIndex + 1
                                                                    }
                                                                    {" · "}
                                                                    {
                                                                        activeResponseIndex + 1
                                                                    }
                                                                    {" of "}
                                                                    {
                                                                        responses.length
                                                                    }
                                                                </div>
                                                            </div>

                                                            <button
                                                                type="button"
                                                                disabled={
                                                                    activeResponseIndex >= responses.length - 1
                                                                }
                                                                onClick={
                                                                    () => {
                                                                        setSelectedAnnotationId(null);
                                                                        setAnnotationDrag(null);
                                                                        setActiveResponseIndex(
                                                                            current => Math.min(
                                                                                responses.length - 1,
                                                                                current + 1,
                                                                            ),
                                                                        );
                                                                    }
                                                                }
                                                                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
                                                            >
                                                                Next →
                                                            </button>
                                                        </div>

                                                        {
                                                            responses
                                                                .slice(
                                                                    activeResponseIndex,
                                                                    activeResponseIndex + 1,
                                                                )
                                                                .map(
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

                                                                            <div
                                                                                 className={[
                                                                                     "relative mt-5 rounded-xl border border-slate-300 bg-white p-4 text-slate-950 shadow-sm",
                                                                                     !readOnly
                                                                                     && response.question_snapshot?.question_type
                                                                                     !== "diagram_annotation"
                                                                                     && selectedMarkingTool
                                                                                         ? [
                                                                                            "highlight",
                                                                                            "line",
                                                                                            "arrow",
                                                                                        ].includes(
                                                                                            selectedMarkingTool.tool_type,
                                                                                        )
                                                                                            ? "cursor-crosshair select-none touch-none"
                                                                                            : "cursor-crosshair"
                                                                                         : "",
                                                                                     annotationSavingResponseId
                                                                                     === response.id
                                                                                         ? "opacity-80"
                                                                                         : "",
                                                                                 ].join(
                                                                                     " ",
                                                                                 )}                                                                                 onPointerDown={
                                                                                     (
                                                                                         event,
                                                                                     ) => {
                                                                                         handleHighlightPointerDown(
                                                                                             response,
                                                                                             event,
                                                                                             readOnly,
                                                                                         );
                                            handleLinePointerDown(
                                                response,
                                                event,
                                                readOnly,
                                            );
                                                                                     }
                                                                                 }
                                                                                 onPointerMove={
                                                                                     (
                                                                                         event,
                                                                                     ) => {
                                                                                         handleHighlightPointerMove(
                                                                                             response,
                                                                                             event,
                                                                                         );
                                            handleLinePointerMove(
                                                response,
                                                event,
                                            );
                                                                                     }
                                                                                 }
                                                                                 onPointerUp={
                                                                                     (
                                                                                         event,
                                                                                     ) => {
                                                                                         void handleHighlightPointerUp(
                                                                                             response,
                                                                                             event,
                                                                                         );
                                            void handleLinePointerUp(
                                                response,
                                                event,
                                            );
                                                                                     }
                                                                                 }
                                                                                 onDragStart={
                                                                                     (
                                                                                         event,
                                                                                     ) => {
                                                                                         if (
                                                                                             [
                                                    "highlight",
                                                    "line",
                                                    "arrow",
                                                ].includes(
                                                    selectedMarkingTool
                                                        ?.tool_type
                                                    ?? "",
                                                )
                                                                                         ) {
                                                                                             event.preventDefault();
                                                                                         }
                                                                                     }
                                                                                 }
                                                                                 onClick={
                                                                                     (
                                                                                         event,
                                                                                     ) => {
                                                                                         void handleResponseAnnotationClick(
                                                                                             response,
                                                                                             event,
                                                                                             readOnly,
                                                                                         );
                                                                                     }
                                                                                 }
                                                                             >
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
                                                                            {
    pendingLine
    && pendingLine.responseId
    === response.id
        ? (
            <svg
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 z-30 h-full w-full overflow-visible"
            >
                {pendingLine.annotationType === "arrow" ? (
                    <defs>
                        <marker
                            id={`marking-arrow-preview-${response.id}`}
                            markerWidth="10"
                            markerHeight="10"
                            refX="9"
                            refY="5"
                            orient="auto"
                            markerUnits="userSpaceOnUse"
                            viewBox="0 0 10 10"
                        >
                            <path
                                d="M 0 0 L 10 5 L 0 10 Z"
                                fill="currentColor"
                                className="text-red-600"
                            />
                        </marker>
                    </defs>
                ) : null}

                <line
                    ref={linePreviewRef}
                    x1={`${pendingLine.startX * 100}%`}
                    y1={`${pendingLine.startY * 100}%`}
                    x2={`${pendingLine.currentX * 100}%`}
                    y2={`${pendingLine.currentY * 100}%`}
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                    markerEnd={
                        pendingLine.annotationType === "arrow"
                            ? `url(#marking-arrow-preview-${response.id})`
                            : undefined
                    }
                    className="text-red-600"
                />
            </svg>
        )
        : null
}{
    pendingHighlight
    && pendingHighlight.responseId
    === response.id
        ? (
            <div
                aria-hidden="true"
                className="pointer-events-none absolute z-10 border border-yellow-500 bg-yellow-300/40"
                style={{
                    left:
                        `${Math.min(
                            pendingHighlight.startX,
                            pendingHighlight.currentX,
                        ) * 100}%`,

                    top:
                        `calc(${pendingHighlight.startY * 100}% - 14px)`,

                    width:
                        `${Math.abs(
                            pendingHighlight.currentX
                            - pendingHighlight.startX,
                        ) * 100}%`,

                    height:
                        "28px",
                }}
            />
        )
        : null
}
{
    pendingTextAnnotation
    && pendingTextAnnotation.responseId
    === response.id
        ? (
            <div
                className="absolute z-40 w-64 -translate-x-1/2 rounded-lg border border-red-300 bg-white p-3 shadow-xl"
                style={{
                    left:
                        `${pendingTextAnnotation.x * 100}%`,

                    top:
                        `${pendingTextAnnotation.y * 100}%`,
                }}
                onClick={
                    (event) => {
                        event.stopPropagation();
                    }
                }
            >
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-red-600">
                    Examiner comment
                </div>

                <textarea
                    autoFocus
                    rows={3}
                    value={
                        pendingTextAnnotation.text
                    }
                    onChange={
                        (event) => {
                            const text =
                                event.target.value;

                            setPendingTextAnnotation(
                                (current) => (
                                    current
                                        ? {
                                            ...current,
                                            text,
                                        }
                                        : null
                                ),
                            );
                        }
                    }
                    onKeyDown={
                        (event) => {
                            if (
                                event.key === "Enter"
                                && !event.shiftKey
                            ) {
                                event.preventDefault();

                                void handleSaveTextAnnotation(
                                    response,
                                );
                            }

                            if (
                                event.key === "Escape"
                            ) {
                                event.preventDefault();

                                setPendingTextAnnotation(
                                    null,
                                );
                            }
                        }
                    }
                    className="w-full resize-none rounded-md border border-slate-300 bg-white px-2 py-2 text-sm leading-5 text-slate-950 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
                    placeholder="Type examiner comment…"
                />

                <div className="mt-2 flex justify-end gap-2">
                    <button
                        type="button"
                        className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                        onClick={
                            (event) => {
                                event.stopPropagation();

                                setPendingTextAnnotation(
                                    null,
                                );
                            }
                        }
                    >
                        Cancel
                    </button>

                    <button
                        type="button"
                        disabled={
                            !pendingTextAnnotation.text.trim()
                            || annotationSavingResponseId
                            === response.id
                        }
                        className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                        onClick={
                            (event) => {
                                event.stopPropagation();

                                void handleSaveTextAnnotation(
                                    response,
                                );
                            }
                        }
                    >
                        {
                            annotationSavingResponseId
                            === response.id
                                ? "Saving…"
                                : "Save"
                        }
                    </button>
                </div>
            </div>
        )
        : null
}
{
                                                                                     (
                                                                                         markingAnnotations[
                                                                                             response.id
                                                                                         ]
                                                                                         ?? []
                                                                                     )
                                                                                         .filter(
                                                                                             (annotation) => (
                                                                                                 annotation.surface_type
                                                                                                 === "response"
                                                                                                 && annotation.deleted_at
                                                                                                 === null
                                                                                             ),
                                                                                         )
                                                                                         .map(
                                                                                             (annotation) => (
                                                    ["line", "arrow"].includes(annotation.annotation_type)
                                                        ? (
                                                            annotation.x !== null
                                                            && annotation.y !== null
                                                            && annotation.end_x !== null
                                                            && annotation.end_y !== null
                                                                ? (
                                                                    <svg
                                                                        key={
                                                                            annotation.id
                                                                        }
                                                                        aria-label={
                                                                            annotation.annotation_type === "arrow"
                                                                                ? "Examiner arrow annotation"
                                                                                : "Examiner line annotation"
                                                                        }
                                                                        className="pointer-events-none absolute inset-0 z-20 h-full w-full overflow-visible"
                                                                    >
                                                                        {annotation.annotation_type === "arrow" ? (
                                                                            <defs>
                                                                                <marker
                                                                                    id={`marking-arrow-${annotation.id}`}
                                                                                    markerWidth="10"
                                                                                    markerHeight="10"
                                                                                    refX="9"
                                                                                    refY="5"
                                                                                    orient="auto"
                                                                                    markerUnits="userSpaceOnUse"
                                                                                    viewBox="0 0 10 10"
                                                                                >
                                                                                    <path
                                                                                        d="M 0 0 L 10 5 L 0 10 Z"
                                                                                        fill="currentColor"
                                                                                        className="text-red-600"
                                                                                    />
                                                                                </marker>
                                                                            </defs>
                                                                        ) : null}
                                                                        {deleteMode && !readOnly ? (
                                <line
                                    x1={`${Number(annotation.x) * 100}%`}
                                    y1={`${Number(annotation.y) * 100}%`}
                                    x2={`${Number(annotation.end_x) * 100}%`}
                                    y2={`${Number(annotation.end_y) * 100}%`}
                                    stroke="transparent"
                                    strokeWidth="18"
                                    strokeLinecap="round"
                                    vectorEffect="non-scaling-stroke"
                                    style={{
                                        pointerEvents:
                                            "stroke",
                                        cursor:
                                            "pointer",
                                    }}
                                    onPointerDown={
                                        (event) => {
                                            event.preventDefault();
                                            event.stopPropagation();
                                        }
                                    }
                                    onClick={
                                        (event) => {
                                            event.preventDefault();
                                            event.stopPropagation();

                                            void handleDeleteAnnotation(
                                                response,
                                                annotation,
                                                readOnly,
                                            );
                                        }
                                    }
                                />
                            ) : null}
                           
<line
                                                                            x1={`${Number(annotation.x) * 100}%`}
                                                                            y1={`${Number(annotation.y) * 100}%`}
                                                                            x2={`${Number(annotation.end_x) * 100}%`}
                                                                            y2={`${Number(annotation.end_y) * 100}%`}
                                                                            stroke="currentColor"
                                                                            strokeWidth="3"
                                                                            strokeLinecap="round"
                                                                            vectorEffect="non-scaling-stroke"
                                                                            markerEnd={
                                                                                annotation.annotation_type === "arrow"
                                                                                    ? `url(#marking-arrow-${annotation.id})`
                                                                                    : undefined
                                                                            }
                                                                            className="text-red-600"
                                                                            style={{
                                                                                pointerEvents:
                                                                                    !readOnly
                                                                                    && deleteMode
                                                                                        ? "stroke"
                                                                                        : "none",
                                                                            }}
                                                                            onPointerDown={
                                                                                (event) => {
                                                                                    if (
                                                                                        !readOnly
                                                                                        && deleteMode
                                                                                    ) {
                                                                                        event.preventDefault();
                                                                                        event.stopPropagation();
                                                                                    }
                                                                                }
                                                                            }
                                                                            onClick={
                                                                                (event) => {
                                                                                    if (
                                                                                        !readOnly
                                                                                        && deleteMode
                                                                                    ) {
                                                                                        event.preventDefault();
                                                                                        event.stopPropagation();

                                                                                        void handleDeleteAnnotation(
                                                                                            response,
                                                                                            annotation,
                                                                                            readOnly,
                                                                                        );
                                                                                    }
                                                                                }
                                                                            }
                                                                        />
                                                                    </svg>
                                                                )
                                                                : null
                                                        )
                                                        : (
                                                                                                 <span
                                                                                                     key={
                                                                                                         annotation.id
                                                                                                     }
                                                                                                     className={[
                                                            annotation.annotation_type === "highlight"
    ? "absolute z-10 border border-yellow-500 bg-yellow-300/40"
    : annotation.annotation_type === "text"
        ? "absolute z-30 -translate-x-1/2 -translate-y-1/2 max-w-xs whitespace-pre-wrap rounded-md border border-red-300 bg-white/95 px-2 py-1 text-sm font-semibold leading-5 text-red-600 shadow-sm"
        : "absolute z-30 -translate-x-1/2 -translate-y-1/2 select-none border-0 bg-transparent p-0 text-2xl font-black leading-none text-red-600 shadow-none",
                                                            annotation.annotation_type === "highlight"
    ? (
        !readOnly
        && deleteMode
            ? "pointer-events-auto cursor-pointer"
            : "pointer-events-none"
    )
    : !readOnly
        && deleteMode
            ? (
                annotation.annotation_type === "text"
                    ? "pointer-events-auto cursor-pointer"
                    : "pointer-events-auto cursor-pointer flex min-h-9 min-w-9 items-center justify-center"
            )
        : [
            "highlight",
            "line",
            "arrow",
        ].includes(
            selectedMarkingTool?.tool_type
            ?? "",
        )
            ? "pointer-events-none"
            : readOnly
                ? "pointer-events-none"
                : "cursor-move touch-none",
                                                            selectedAnnotationId
                                                            === annotation.id
                                                                ? "rounded-sm ring-2 ring-blue-500 ring-offset-2 ring-offset-white"
                                                                : "",
                                                        ].join(
                                                            " ",
                                                        )}
                                                        style={{
                                                            left:
                                                                `${(
                                                                    annotationDrag?.annotationId
                                                                    === annotation.id
                                                                        ? annotationDrag.x
                                                                        : Number(
                                                                            annotation.x,
                                                                        )
                                                                ) * 100}%`,

                                                            top:
                                                                `${(
                                                                    annotationDrag?.annotationId
                                                                    === annotation.id
                                                                        ? annotationDrag.y
                                                                        : Number(
                                                                            annotation.y,
                                                                        )
                                                                ) * 100}%`,
                                                            width:
                                                                annotation.annotation_type
                                                                === "highlight"
                                                                    ? `${Number(
                                                                        annotation.width
                                                                        ?? 0,
                                                                    ) * 100}%`
                                                                    : undefined,

                                                            height:
                                                                annotation.annotation_type
                                                                === "highlight"
                                                                    ? `${Number(
                                                                        annotation.height
                                                                        ?? 0,
                                                                    ) * 100}%`
                                                                    : undefined,
                                                        }}
                                                        tabIndex={
                                                            readOnly
                                                                ? -1
                                                                : 0
                                                        }
                                                        title={
                                                            readOnly
                                                                ? undefined
                                                                : "Drag to move. Press Delete or Backspace to remove."
                                                        }
                                                        aria-label={
                                                            `Examiner annotation ${annotation.annotation_type === "text"
    ? annotation.text ?? ""
    : annotation.value ?? ""}`
                                                        }
                                                        onClick={
                                                            (event) => {
                                                                event.stopPropagation();

                                                                if (!readOnly && !deleteMode) {
                                                                    setSelectedAnnotationId(
                                                                        annotation.id,
                                                                    );
                                                                }
                                                            }
                                                        }
                                                        onPointerDown={
                                                            (event) => {
                                                                handleAnnotationPointerDown(
                                                                    response,
                                                                    annotation,
                                                                    event,
                                                                    readOnly,
                                                                );
                                                            }
                                                        }
                                                        onPointerMove={
                                                            (event) => {
                                                                handleAnnotationPointerMove(
                                                                    annotation,
                                                                    event,
                                                                );
                                                            }
                                                        }
                                                        onPointerUp={
                                                            (event) => {
                                                                void handleAnnotationPointerUp(
                                                                    response,
                                                                    annotation,
                                                                    event,
                                                                    readOnly,
                                                                );
                                                            }
                                                        }
                                                        onPointerCancel={
                                                            (event) => {
                                                                event.stopPropagation();

                                                                setAnnotationDrag(
                                                                    null,
                                                                );
                                                            }
                                                        }
                                                        onKeyDown={
                                                            (event) => {
                                                                if (
                                                                    !readOnly
                                                                    && (
                                                                        event.key === "Delete"
                                                                        || event.key === "Backspace"
                                                                    )
                                                                ) {
                                                                    event.preventDefault();
                                                                    event.stopPropagation();

                                                                    void handleDeleteAnnotation(
                                                                        response,
                                                                        annotation,
                                                                        readOnly,
                                                                    );
                                                                }
                                                            }
                                                        }
                                                                                                 >
                                                                                                     {
                                                                                                         annotation.annotation_type === "highlight"
    ? null
    : annotation.annotation_type === "text"
        ? annotation.text
        : annotation.value
                                                                                                     }
                                                                                                 
                                                            {
                                                                !readOnly
                                                                && selectedAnnotationId
                                                                === annotation.id
                                                                    ? (
                                                                        <button
                                                                            type="button"
                                                                            aria-label="Delete examiner annotation"
                                                                            title="Delete this examiner mark"
                                                                            className="absolute -right-7 -top-7 z-30 flex h-7 w-7 items-center justify-center rounded-full border border-red-800 bg-red-600 text-base font-bold leading-none text-white shadow-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                                                                            onPointerDown={
                                                                                (event) => {
                                                                                    event.preventDefault();
                                                                                    event.stopPropagation();
                                                                                }
                                                                            }
                                                                            onPointerUp={
                                                                                (event) => {
                                                                                    event.preventDefault();
                                                                                    event.stopPropagation();
                                                                                }
                                                                            }
                                                                            onClick={
                                                                                (event) => {
                                                                                    event.preventDefault();
                                                                                    event.stopPropagation();

                                                                                    void handleDeleteAnnotation(
                                                                                        response,
                                                                                        annotation,
                                                                                        readOnly,
                                                                                    );
                                                                                }
                                                                            }
                                                                        >
                                                                            ×
                                                                        </button>
                                                                    )
                                                                    : null
                                                            
                                                        }</span>
                                                        )
                                                                                             ),
                                                                                         )
                                                                                 }

                                                                             </div>

                                                                            <div className="mt-4 max-w-[260px]">
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

                                                                                <div className="hidden">
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














































































        status=initial_status,
