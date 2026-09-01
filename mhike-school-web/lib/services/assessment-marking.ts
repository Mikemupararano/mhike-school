import {
    apiDelete,
    apiGet,
    apiGetBlob,
    apiPatch,
    apiPost,
    apiPut,
} from "@/lib/api";


// ---------------------------------------------------------------------
// Core lifecycle types
// ---------------------------------------------------------------------


export type AssessmentResponseStatus =
    | "not_started"
    | "in_progress"
    | "submitted"
    | "void";


export type MarkingDecisionStatus =
    | "unmarked"
    | "in_progress"
    | "marked"
    | "reviewed"
    | "finalised";


export type MarkingDecisionRevisionChangeType =
    | "updated"
    | "instant_marked"
    | "started"
    | "marked"
    | "reviewed"
    | "moderated"
    | "finalised";


export type MarkingDecisionRevisionSource =
    | "manual"
    | "moderation"
    | "quick_mark"
    | "automated"
    | "ai";


// ---------------------------------------------------------------------
// Mark-scheme evidence
// ---------------------------------------------------------------------


export type MarkSchemeItemSummary = {
    /*
     * The backend may enrich this nested representation as the
     * mark-scheme UI develops. Keep the known identity available
     * without manufacturing fields that are not part of the
     * confirmed frontend contract yet.
     */
    id: number;

    [key: string]: unknown;
};


export type MarkSchemeItemAward = {
    id: number;

    marking_decision_id: number;
    mark_scheme_item_id: number;

    marks_awarded: string | number;

    marker_note: string | null;

    awarded_by_id: number | null;

    awarded_at: string;
    updated_at: string;

    mark_scheme_item: MarkSchemeItemSummary | null;
};


export type MarkSchemeItemAwardCreate = {
    mark_scheme_item_id: number;
    marks_awarded: string | number;
    marker_note?: string | null;

    expected_revision: number;
};


export type MarkSchemeItemAwardDeleteRequest = {
    expected_revision: number;
};


// ---------------------------------------------------------------------
// Marking decision
// ---------------------------------------------------------------------


export type MarkingDecision = {
    id: number;

    response_id: number;
    marker_id: number | null;

    status: MarkingDecisionStatus;

    mark_awarded: string | number | null;

    revision: number;

    marker_comment: string | null;
    moderation_comment: string | null;

    created_at: string;
    updated_at: string;

    marked_at: string | null;
    reviewed_at: string | null;
    finalised_at: string | null;

    item_awards: MarkSchemeItemAward[];
};


export type MarkingDecisionRevision = {
    id: number;

    marking_decision_id: number;
    response_id: number;

    revision: number;

    changed_by_id: number | null;

    change_type:
        | MarkingDecisionRevisionChangeType
        | string;

    source:
        | MarkingDecisionRevisionSource
        | string;

    marker_id: number | null;

    status: MarkingDecisionStatus;

    mark_awarded: string | number | null;

    marker_comment: string | null;
    moderation_comment: string | null;

    marked_at: string | null;
    reviewed_at: string | null;
    finalised_at: string | null;

    created_at: string;
};


// ---------------------------------------------------------------------
// Immutable question snapshot
// ---------------------------------------------------------------------


export type AssessmentQuestionSnapshotOption = {
    id: number;
    text: string;
    order: number;
};


export type AssessmentQuestionSnapshotAsset = {
    id: number;
    asset_type: string;

    original_filename: string | null;
    mime_type: string | null;
    file_size_bytes: number | null;

    alt_text: string | null;
    caption: string | null;

    order: number;
};


export type AssessmentQuestionSnapshot = {
    id: number;

    script_id: number;
    question_id: number;
    parent_question_id_snapshot: number | null;

    question_number: string;
    source_page_number: number | null;
    title: string | null;
    prompt: string | null;
    question_type: string;

    interaction_config_snapshot:
        | Record<string, unknown>
        | null;

    maximum_mark: string | number;
    order: number;
    is_markable: boolean;

    section_snapshot:
        | Record<string, unknown>
        | null;

    options_snapshot: AssessmentQuestionSnapshotOption[];
    assets_snapshot: AssessmentQuestionSnapshotAsset[];

    created_at: string;
};


// ---------------------------------------------------------------------
// Assessment response
// ---------------------------------------------------------------------


export type AssessmentResponse = {
    id: number;

    script_id: number;
    question_id: number;

    question_snapshot_id: number | null;
    question_snapshot: AssessmentQuestionSnapshot | null;

    status: AssessmentResponseStatus;

    response_text: string | null;
    response_data: string | null;
    source_reference: string | null;

    created_at: string;
    updated_at: string;
    submitted_at: string | null;

    marking_decision: MarkingDecision | null;
};


// ---------------------------------------------------------------------
// Marking palette
// ---------------------------------------------------------------------


export type MarkingPaletteToolType =
    | "symbol"
    | "code"
    | "text"
    | "line"
    | "arrow"
    | "highlight";


export type MarkingPaletteTool = {
    id: number;
    palette_id: number;

    tool_type: MarkingPaletteToolType;

    value: string;
    label: string;
    description: string | null;
    keyboard_shortcut: string | null;

    sort_order: number;
    is_active: boolean;

    created_at: string;
    updated_at: string;
};


export type MarkingPalette = {
    id: number;
    school_id: number;
    subject_id: number | null;

    name: string;
    description: string | null;

    is_default: boolean;
    is_active: boolean;

    created_at: string;
    updated_at: string;

    tools: MarkingPaletteTool[];
};


// ---------------------------------------------------------------------
// Examiner annotations
// ---------------------------------------------------------------------


export type MarkingAnnotationType =
    | "symbol"
    | "code"
    | "text"
    | "line"
    | "arrow"
    | "highlight";


export type MarkingAnnotationSurfaceType =
    | "response"
    | "question_asset"
    | "script_page";


export type MarkingAnnotation = {
    id: number;

    response_id: number;
    marker_id: number | null;
    palette_tool_id: number | null;

    annotation_type: MarkingAnnotationType;

    value: string | null;
    label_snapshot: string | null;
    text: string | null;

    surface_type: MarkingAnnotationSurfaceType;
    surface_reference: string | null;
    page_number: number | null;

    x: string | number;
    y: string | number;

    end_x: string | number | null;
    end_y: string | number | null;

    width: string | number | null;
    height: string | number | null;

    revision: number;

    created_at: string;
    updated_at: string;

    deleted_at: string | null;
    deleted_by_id: number | null;
};


export type MarkingAnnotationCreate = {
    palette_tool_id: number;

    /*
     * Required by the backend for score-bearing ✓ / ✗ tools.
     * Non-scoring examiner annotations may omit it.
     */
    expected_decision_revision?: number | null;

    surface_type?: MarkingAnnotationSurfaceType;
    surface_reference?: string | null;
    page_number?: number | null;

    x: string | number;
    y: string | number;

    end_x?: string | number | null;
    end_y?: string | number | null;

    width?: string | number | null;
    height?: string | number | null;

    text?: string | null;
};


export type MarkingAnnotationUpdate = {
    revision: number;

    x?: string | number | null;
    y?: string | number | null;

    end_x?: string | number | null;
    end_y?: string | number | null;

    width?: string | number | null;
    height?: string | number | null;

    text?: string | null;
};


export type MarkingAnnotationDeleteRequest = {
    revision: number;

    /*
     * Required when deleting a score-bearing ✓ / ✗ annotation.
     */
    expected_decision_revision?: number | null;
};


// ---------------------------------------------------------------------
// Decision mutation payloads
// ---------------------------------------------------------------------


export type MarkingDecisionUpdate = {
    mark_awarded?: string | number | null;
    marker_comment?: string | null;

    expected_revision: number;
};


export type InstantMarkRequest = {
    mark_awarded: string | number;

    expected_revision: number;
};


export type MarkingDecisionStatusUpdate = {
    status: MarkingDecisionStatus;
    moderation_comment?: string | null;

    expected_revision: number;
};


export type MarkingDecisionTransitionRequest = {
    expected_revision: number;
};


export type MarkingReviewRequest = {
    moderation_comment?: string | null;

    expected_revision: number;
};


// ---------------------------------------------------------------------
// Query helpers
// ---------------------------------------------------------------------


function buildResponseStatusQuery(
    responseStatus?: AssessmentResponseStatus,
): string {
    if (!responseStatus) {
        return "";
    }

    const params =
        new URLSearchParams();

    params.set(
        "response_status",
        responseStatus,
    );

    return `?${params.toString()}`;
}


function buildDecisionStatusQuery(
    decisionStatus?: MarkingDecisionStatus,
): string {
    if (!decisionStatus) {
        return "";
    }

    const params =
        new URLSearchParams();

    params.set(
        "decision_status",
        decisionStatus,
    );

    return `?${params.toString()}`;
}


// ---------------------------------------------------------------------
// Script marking workspace
// ---------------------------------------------------------------------


export async function getScriptResponses(
    scriptId: number,
    responseStatus?: AssessmentResponseStatus,
): Promise<AssessmentResponse[]> {
    const startedAt = Date.now();

    try {
        return await apiGet<AssessmentResponse[]>(
            `/assessment-marking/scripts/${scriptId}/responses${buildResponseStatusQuery(
                responseStatus,
            )}`,
        );
    } finally {
        console.info(
            `[MARKING TIMING] getScriptResponses script=${scriptId}: ${
                Date.now() - startedAt
            } ms`,
        );
    }
}


export async function getScriptMarkingDecisions(
    scriptId: number,
    decisionStatus?: MarkingDecisionStatus,
): Promise<MarkingDecision[]> {
    return apiGet<MarkingDecision[]>(
        `/assessment-marking/scripts/${scriptId}/decisions${buildDecisionStatusQuery(
            decisionStatus,
        )}`,
    );
}


// ---------------------------------------------------------------------
// Individual responses
// ---------------------------------------------------------------------


export async function getAssessmentResponse(
    responseId: number,
): Promise<AssessmentResponse> {
    return apiGet<AssessmentResponse>(
        `/assessment-marking/responses/${responseId}`,
    );
}


export async function getAssessmentResponseAssetBlob(
    responseId: number,
    assetId: number,
): Promise<Blob> {
    return apiGetBlob(
        `/assessment-marking/responses/${responseId}/assets/${assetId}/content`,
    );
}


// ---------------------------------------------------------------------
// Marking palette API
// ---------------------------------------------------------------------


export async function getScriptMarkingPalette(
    scriptId: number,
): Promise<MarkingPalette> {
    const startedAt = Date.now();

    try {
        return await apiGet<MarkingPalette>(
            `/assessment-marking/scripts/${scriptId}/palette`,
        );
    } finally {
        console.info(
            `[MARKING TIMING] getScriptMarkingPalette script=${scriptId}: ${
                Date.now() - startedAt
            } ms`,
        );
    }
}

export async function getResponseMarkingPalette(
    responseId: number,
): Promise<MarkingPalette> {
    const startedAt = Date.now();

    try {
        return await apiGet<MarkingPalette>(
            `/assessment-marking/responses/${responseId}/palette`,
        );
    } finally {
        console.info(
            `[MARKING TIMING] getResponseMarkingPalette response=${responseId}: ${
                Date.now() - startedAt
            } ms`,
        );
    }
}


// ---------------------------------------------------------------------
// Examiner annotation API
// ---------------------------------------------------------------------


export async function getScriptMarkingAnnotations(
    scriptId: number,
    includeDeleted = false,
): Promise<MarkingAnnotation[]> {
    const startedAt = Date.now();

    const params =
        new URLSearchParams();

    if (includeDeleted) {
        params.set(
            "include_deleted",
            "true",
        );
    }

    const query =
        params.size > 0
            ? `?${params.toString()}`
            : "";

    try {
        return await apiGet<MarkingAnnotation[]>(
            `/assessment-marking/scripts/${scriptId}/annotations${query}`,
        );
    } finally {
        console.info(
            `[MARKING TIMING] getScriptMarkingAnnotations script=${scriptId}: ${
                Date.now() - startedAt
            } ms`,
        );
    }
}

export async function getMarkingAnnotations(
    responseId: number,
    includeDeleted = false,
): Promise<MarkingAnnotation[]> {
    const startedAt = Date.now();

    const params =
        new URLSearchParams();

    if (includeDeleted) {
        params.set(
            "include_deleted",
            "true",
        );
    }

    const query =
        params.size > 0
            ? `?${params.toString()}`
            : "";

    try {
        return await apiGet<MarkingAnnotation[]>(
            `/assessment-marking/responses/${responseId}/annotations${query}`,
        );
    } finally {
        console.info(
            `[MARKING TIMING] getMarkingAnnotations response=${responseId}: ${
                Date.now() - startedAt
            } ms`,
        );
    }
}


export async function getMarkingAnnotation(
    annotationId: number,
    includeDeleted = false,
): Promise<MarkingAnnotation> {
    const params =
        new URLSearchParams();

    if (includeDeleted) {
        params.set(
            "include_deleted",
            "true",
        );
    }

    const query =
        params.size > 0
            ? `?${params.toString()}`
            : "";

    return apiGet<MarkingAnnotation>(
        `/assessment-marking/annotations/${annotationId}${query}`,
    );
}


export async function createMarkingAnnotation(
    responseId: number,
    payload: MarkingAnnotationCreate,
): Promise<MarkingAnnotation> {
    return apiPost<MarkingAnnotation>(
        `/assessment-marking/responses/${responseId}/annotations`,
        payload,
    );
}


export async function updateMarkingAnnotation(
    annotationId: number,
    payload: MarkingAnnotationUpdate,
): Promise<MarkingAnnotation> {
    return apiPatch<MarkingAnnotation>(
        `/assessment-marking/annotations/${annotationId}`,
        payload,
    );
}


export async function deleteMarkingAnnotation(
    annotationId: number,
    payload: MarkingAnnotationDeleteRequest,
): Promise<MarkingAnnotation> {
    const params =
        new URLSearchParams();

    params.set(
        "revision",
        String(
            payload.revision,
        ),
    );

    if (
        payload.expected_decision_revision !== undefined
        && payload.expected_decision_revision !== null
    ) {
        params.set(
            "expected_decision_revision",
            String(
                payload.expected_decision_revision,
            ),
        );
    }

    return apiDelete<MarkingAnnotation>(
        `/assessment-marking/annotations/${annotationId}?${params.toString()}`,
    );
}


// ---------------------------------------------------------------------
// Decision creation and reads
// ---------------------------------------------------------------------


export async function createMarkingDecision(
    responseId: number,
): Promise<MarkingDecision> {
    /*
     * New decisions are intentionally pristine:
     *
     * revision = 0
     * no mark
     * no marker comment
     *
     * Authoritative content is added only through revision-aware
     * mutation endpoints.
     */
    return apiPost<MarkingDecision>(
        `/assessment-marking/responses/${responseId}/decision`,
        {},
    );
}


export async function getMarkingDecision(
    decisionId: number,
): Promise<MarkingDecision> {
    return apiGet<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}`,
    );
}


export async function getMarkingDecisionRevisions(
    decisionId: number,
): Promise<MarkingDecisionRevision[]> {
    return apiGet<MarkingDecisionRevision[]>(
        `/assessment-marking/decisions/${decisionId}/revisions`,
    );
}


// ---------------------------------------------------------------------
// Authoritative marking mutations
// ---------------------------------------------------------------------


export async function updateMarkingDecision(
    decisionId: number,
    payload: MarkingDecisionUpdate,
): Promise<MarkingDecision> {
    return apiPatch<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}`,
        payload,
    );
}


export async function instantMarkDecision(
    decisionId: number,
    payload: InstantMarkRequest,
): Promise<MarkingDecision> {
    return apiPost<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}/instant-mark`,
        payload,
    );
}


export async function updateMarkingDecisionStatus(
    decisionId: number,
    payload: MarkingDecisionStatusUpdate,
): Promise<MarkingDecision> {
    return apiPatch<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}/status`,
        payload,
    );
}


// ---------------------------------------------------------------------
// Marking lifecycle
// ---------------------------------------------------------------------


export async function startMarkingDecision(
    decisionId: number,
    expectedRevision: number,
): Promise<MarkingDecision> {
    return apiPost<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}/start`,
        {
            expected_revision:
                expectedRevision,
        } satisfies MarkingDecisionTransitionRequest,
    );
}


export async function completeMarkingDecision(
    decisionId: number,
    expectedRevision: number,
): Promise<MarkingDecision> {
    return apiPost<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}/complete`,
        {
            expected_revision:
                expectedRevision,
        } satisfies MarkingDecisionTransitionRequest,
    );
}


export async function reviewMarkingDecision(
    decisionId: number,
    payload: MarkingReviewRequest,
): Promise<MarkingDecision> {
    return apiPost<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}/review`,
        payload,
    );
}


export async function finaliseMarkingDecision(
    decisionId: number,
    expectedRevision: number,
): Promise<MarkingDecision> {
    return apiPost<MarkingDecision>(
        `/assessment-marking/decisions/${decisionId}/finalise`,
        {
            expected_revision:
                expectedRevision,
        } satisfies MarkingDecisionTransitionRequest,
    );
}


// ---------------------------------------------------------------------
// Criterion-level marking evidence
// ---------------------------------------------------------------------


export async function setMarkSchemeItemAward(
    decisionId: number,
    payload: MarkSchemeItemAwardCreate,
): Promise<MarkSchemeItemAward> {
    return apiPut<MarkSchemeItemAward>(
        `/assessment-marking/decisions/${decisionId}/awards`,
        payload,
    );
}


export async function deleteMarkSchemeItemAward(
    awardId: number,
    expectedRevision: number,
): Promise<void> {
    await apiDelete<void>(
        `/assessment-marking/awards/${awardId}`,
        {
            expected_revision:
                expectedRevision,
        } satisfies MarkSchemeItemAwardDeleteRequest,
    );
}


// ---------------------------------------------------------------------
// Pristine-decision cleanup
// ---------------------------------------------------------------------


export async function deleteMarkingDecision(
    decisionId: number,
): Promise<void> {
    /*
     * The backend permits physical deletion only while the decision
     * remains pristine. Once revision history exists, retention rules
     * prohibit deletion.
     */
    await apiDelete<void>(
        `/assessment-marking/decisions/${decisionId}`,
    );
}







