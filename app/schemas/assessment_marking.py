from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.assessment_marking_annotation import (
    MarkingAnnotationSurfaceType,
    MarkingAnnotationType,
)
from app.models.marking_palette import (
    MarkingPaletteToolType,
)

from app.models.assessment_response import (
    AssessmentResponseStatus,
    MarkingDecisionStatus,
)

# ---------------------------------------------------------------------------
# Structured assessment-response payloads
# ---------------------------------------------------------------------------


class DiagramAnnotationPoint(BaseModel):
    """
    Represent one learner annotation placed on a question visual.

    Coordinates are normalised to the rendered asset:

        x = 0.0 -> left edge
        x = 1.0 -> right edge
        y = 0.0 -> top edge
        y = 1.0 -> bottom edge

    Normalised coordinates keep an answer stable across different viewport
    sizes and allow the same response to be rendered consistently to learners
    and markers.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(
        min_length=1,
        max_length=100,
    )

    symbol: str = Field(
        min_length=1,
        max_length=100,
    )

    x: float = Field(
        ge=0.0,
        le=1.0,
    )

    y: float = Field(
        ge=0.0,
        le=1.0,
    )


class DiagramAnnotationResponseData(BaseModel):
    """
    Versioned structured response for a diagram-annotation question.

    ``asset_id`` identifies the canonical AssessmentQuestionAsset on which the
    learner placed the annotations.

    ``annotations`` may be empty while a response is in progress. Submission
    completeness remains a service/lifecycle concern because some valid
    questions may legitimately require zero or a variable number of marks.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    type: Literal["diagram_annotation"] = "diagram_annotation"

    version: Literal[1] = 1

    asset_id: int = Field(
        gt=0,
    )

    annotations: list[DiagramAnnotationPoint] = Field(
        default_factory=list,
        max_length=500,
    )


def _normalise_response_data(value: Any) -> str | None:
    """
    Validate and serialise structured response data while retaining backwards
    compatibility with existing string-based response payloads.

    Existing non-JSON strings continue to pass through unchanged.

    JSON objects whose ``type`` is ``diagram_annotation`` are validated
    strictly against ``DiagramAnnotationResponseData`` and serialised to a
    canonical JSON string for storage in AssessmentResponse.response_data.

    Dictionaries supplied directly by newer clients are also accepted and
    normalised before reaching the service/ORM layer.
    """

    if value is None:
        return None

    if isinstance(value, DiagramAnnotationResponseData):
        payload = value
        return json.dumps(
            payload.model_dump(mode="json"),
            separators=(",", ":"),
            ensure_ascii=False,
        )

    if isinstance(value, dict):
        response_type = value.get("type")

        if response_type == "diagram_annotation":
            payload = DiagramAnnotationResponseData.model_validate(value)
            return json.dumps(
                payload.model_dump(mode="json"),
                separators=(",", ":"),
                ensure_ascii=False,
            )

        # Preserve compatibility for existing generic structured dictionaries.
        return json.dumps(
            value,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    if not isinstance(value, str):
        raise ValueError("response_data must be a string, object, or null")

    stripped = value.strip()

    if not stripped:
        return value

    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError:
        # Existing response_data historically accepts arbitrary text.
        return value

    if isinstance(decoded, dict) and decoded.get("type") == "diagram_annotation":
        payload = DiagramAnnotationResponseData.model_validate(decoded)
        return json.dumps(
            payload.model_dump(mode="json"),
            separators=(",", ":"),
            ensure_ascii=False,
        )

    # Existing JSON stored in response_data remains valid and is preserved.
    return value


# ---------------------------------------------------------------------------
# Assessment response payloads
# ---------------------------------------------------------------------------


class AssessmentResponseCreate(BaseModel):
    """
    Payload for creating one response for a script/question pair.

    ``response_data`` remains a string at the service/ORM boundary for
    backwards compatibility with the existing Text database column.

    New clients may nevertheless submit a structured dictionary. Supported
    typed response formats, such as ``diagram_annotation``, are validated and
    serialised automatically.
    """

    question_id: int = Field(
        gt=0,
    )

    response_text: str | None = None
    response_data: str | None = None

    source_reference: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator(
        "response_data",
        mode="before",
    )
    @classmethod
    def validate_response_data(
        cls,
        value: Any,
    ) -> str | None:
        return _normalise_response_data(value)


class AssessmentResponseUpdate(BaseModel):
    """
    Payload for updating editable response content.

    Structured response data uses the same validation and serialisation rules
    as response creation.
    """

    response_text: str | None = None
    response_data: str | None = None

    source_reference: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator(
        "response_data",
        mode="before",
    )
    @classmethod
    def validate_response_data(
        cls,
        value: Any,
    ) -> str | None:
        return _normalise_response_data(value)


class AssessmentResponseStatusUpdate(BaseModel):
    """
    Payload for an explicit assessment-response lifecycle transition.
    """

    status: AssessmentResponseStatus


# ---------------------------------------------------------------------------
# Marking decision payloads
# ---------------------------------------------------------------------------


class MarkingDecisionCreate(BaseModel):
    """
    Payload for creating a pristine marking decision for one submitted
    response.

    Authoritative marking content is added only through revision-aware
    mutation endpoints.
    """

    model_config = {
        "extra": "forbid",
    }


class InstantMarkRequest(BaseModel):
    """
    Payload for examiner-style one-click or keyboard marking.

    ``expected_revision`` is the revision displayed by the marking client.
    It is used for optimistic concurrency so a stale browser tab cannot
    overwrite a newer authoritative marking decision.
    """

    mark_awarded: Decimal = Field(
        ge=0,
    )

    expected_revision: int = Field(
        ge=0,
    )


class MarkingDecisionUpdate(BaseModel):
    """
    Payload for updating the authoritative question-level result.

    ``expected_revision`` is required for optimistic concurrency so a
    stale marking client cannot overwrite a newer decision.
    """

    mark_awarded: Decimal | None = Field(
        default=None,
        ge=0,
    )

    marker_comment: str | None = None

    expected_revision: int = Field(
        ge=0,
    )


class MarkingDecisionStatusUpdate(BaseModel):
    """
    Payload for an explicit marking-decision lifecycle transition.

    ``moderation_comment`` is used when moving a completed decision into
    REVIEWED status. ``expected_revision`` prevents a stale marking client
    from changing a newer authoritative decision.
    """

    status: MarkingDecisionStatus

    moderation_comment: str | None = None

    expected_revision: int = Field(
        ge=0,
    )


class MarkingDecisionTransitionRequest(BaseModel):
    """
    Payload for lifecycle action endpoints such as start, complete and
    finalise.

    The revision is required for optimistic concurrency.
    """

    expected_revision: int = Field(
        ge=0,
    )


class MarkingReviewRequest(BaseModel):
    """
    Payload for reviewing or moderating a completed marking decision.
    """

    moderation_comment: str | None = None

    expected_revision: int = Field(
        ge=0,
    )


# ---------------------------------------------------------------------------
# Mark-scheme item award payloads
# ---------------------------------------------------------------------------


class MarkSchemeItemAwardCreate(BaseModel):
    """
    Payload for creating or updating one criterion-level award.

    ``expected_revision`` protects the authoritative marking decision
    from stale criterion-marking clients.
    """

    mark_scheme_item_id: int = Field(
        gt=0,
    )

    marks_awarded: Decimal = Field(
        ge=0,
    )

    marker_note: str | None = None

    expected_revision: int = Field(
        ge=0,
    )


# ---------------------------------------------------------------------------
# Nested output models
# ---------------------------------------------------------------------------


class MarkSchemeItemSummaryOut(BaseModel):
    """
    Lightweight mark-scheme item representation for marking responses.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    mark_scheme_id: int

    code: str | None = None

    item_type: str

    description: str

    marks: Decimal

    order: int
    is_optional: bool

    alternative_group: str | None = None
    examiner_notes: str | None = None


# ---------------------------------------------------------------------------
# Examiner marking palette output
# ---------------------------------------------------------------------------


class MarkingPaletteToolOut(BaseModel):
    """
    One active examiner tool exposed to the marking workspace.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    palette_id: int

    tool_type: MarkingPaletteToolType

    value: str
    label: str
    description: str | None = None
    keyboard_shortcut: str | None = None

    sort_order: int
    is_active: bool

    created_at: datetime
    updated_at: datetime


class MarkingPaletteOut(BaseModel):
    """
    School-scoped marking palette exposed to authorised markers.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    school_id: int
    subject_id: int | None = None

    name: str
    description: str | None = None

    is_default: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    tools: list[MarkingPaletteToolOut]


# ---------------------------------------------------------------------------
# Examiner marking annotation payloads
# ---------------------------------------------------------------------------


class MarkingAnnotationCreate(BaseModel):
    """
    Payload for placing one examiner annotation on a submitted response.

    The palette tool determines the annotation type, value and label snapshot.
    Surface identity is fixed when the annotation is created.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    palette_tool_id: int = Field(
        gt=0,
    )

    expected_decision_revision: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Expected authoritative marking-decision revision. "
            "Required for score-bearing tick/cross annotations; "
            "optional for non-scoring examiner annotations."
        ),
    )

    surface_type: MarkingAnnotationSurfaceType = (
        MarkingAnnotationSurfaceType.RESPONSE
    )

    surface_reference: str | None = Field(
        default=None,
        max_length=255,
    )

    page_number: int | None = Field(
        default=None,
        gt=0,
    )

    x: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    y: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    end_x: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    end_y: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    width: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    height: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    text: str | None = None


class MarkingAnnotationUpdate(BaseModel):
    """
    Payload for changing mutable annotation presentation.

    ``revision`` is required for optimistic concurrency.

    Surface identity is intentionally absent. Moving an annotation to a
    different response surface, question asset or script page requires
    deleting it and creating a new annotation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    revision: int = Field(
        gt=0,
    )

    x: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    y: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    end_x: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    end_y: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    width: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    height: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    text: str | None = None


class MarkingAnnotationOut(BaseModel):
    """
    Examiner annotation response model.

    Palette value and label are snapshots so later palette customisation does
    not rewrite historical marking evidence.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    response_id: int
    marker_id: int | None = None
    palette_tool_id: int | None = None

    annotation_type: MarkingAnnotationType

    value: str | None = None
    label_snapshot: str | None = None
    text: str | None = None

    surface_type: MarkingAnnotationSurfaceType
    surface_reference: str | None = None
    page_number: int | None = None

    x: Decimal
    y: Decimal

    end_x: Decimal | None = None
    end_y: Decimal | None = None

    width: Decimal | None = None
    height: Decimal | None = None

    revision: int

    created_at: datetime
    updated_at: datetime

    deleted_at: datetime | None = None
    deleted_by_id: int | None = None


class MarkSchemeItemAwardDeleteRequest(BaseModel):
    """
    Payload for deleting one criterion-level award.

    ``expected_revision`` protects the authoritative marking decision
    from stale criterion-marking clients.
    """

    expected_revision: int = Field(
        ge=0,
    )


class MarkSchemeItemAwardOut(BaseModel):
    """
    Criterion-level award response model.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    marking_decision_id: int
    mark_scheme_item_id: int

    marks_awarded: Decimal

    marker_note: str | None = None

    awarded_by_id: int | None = None

    awarded_at: datetime
    updated_at: datetime

    mark_scheme_item: MarkSchemeItemSummaryOut | None = None


class MarkingDecisionRevisionOut(BaseModel):
    """
    Immutable historical snapshot of one marking decision revision.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    marking_decision_id: int
    response_id: int

    revision: int

    changed_by_id: int | None = None
    change_type: str
    source: str

    marker_id: int | None = None

    status: MarkingDecisionStatus

    mark_awarded: Decimal | None = None

    marker_comment: str | None = None
    moderation_comment: str | None = None

    marked_at: datetime | None = None
    reviewed_at: datetime | None = None
    finalised_at: datetime | None = None

    created_at: datetime


class MarkingDecisionOut(BaseModel):
    """
    Question-level marking decision response model.

    ``mark_awarded`` remains the authoritative question-level result.
    Criterion-level awards provide supporting marking evidence.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    response_id: int
    marker_id: int | None = None

    status: MarkingDecisionStatus

    mark_awarded: Decimal | None = None

    revision: int

    marker_comment: str | None = None
    moderation_comment: str | None = None

    created_at: datetime
    updated_at: datetime

    marked_at: datetime | None = None
    reviewed_at: datetime | None = None
    finalised_at: datetime | None = None

    item_awards: list[MarkSchemeItemAwardOut] = Field(
        default_factory=list,
    )


class AssessmentQuestionSnapshotOptionOut(BaseModel):
    """
    Learner-visible option frozen into an immutable question snapshot.

    Correct-answer flags and feedback are deliberately absent from this
    marking representation.
    """

    model_config = ConfigDict(
        extra="ignore",
    )

    id: int
    text: str
    order: int


class AssessmentQuestionSnapshotAssetOut(BaseModel):
    """
    Safe marker-facing metadata for an immutable question asset.

    Internal storage paths, checksums, and file-system provenance remain
    server-side.
    """

    model_config = ConfigDict(
        extra="ignore",
    )

    id: int
    asset_type: str

    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None

    alt_text: str | None = None
    caption: str | None = None

    order: int


class AssessmentQuestionSnapshotOut(BaseModel):
    """
    Immutable learner-facing question state used by one script/version.

    Once a response is linked to a question snapshot, marking clients should
    use this representation rather than mutable canonical question content.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    script_id: int
    question_id: int
    parent_question_id_snapshot: int | None = None

    question_number: str
    title: str | None = None
    prompt: str | None = None
    question_type: str

    interaction_config_snapshot: dict[str, Any] | None = None

    maximum_mark: Decimal
    order: int
    is_markable: bool
    source_page_number: int | None = None

    section_snapshot: dict[str, Any] | None = None

    options_snapshot: list[AssessmentQuestionSnapshotOptionOut] = Field(
        default_factory=list,
    )

    assets_snapshot: list[AssessmentQuestionSnapshotAssetOut] = Field(
        default_factory=list,
    )

    created_at: datetime


class AssessmentResponseOut(BaseModel):
    """
    Assessment response representation.

    The nested marking decision is included when one exists so a marking
    client can retrieve the current question-level result and supporting
    criterion awards without making a separate request.

    ``question_snapshot`` exposes the immutable learner-facing question state
    that governed the submitted response. Marking clients should prefer this
    snapshot whenever ``question_snapshot_id`` is present.

    ``response_data`` remains the stored JSON/text representation so existing
    API consumers remain backwards compatible.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    script_id: int
    question_id: int

    question_snapshot_id: int | None = None
    question_snapshot: AssessmentQuestionSnapshotOut | None = None

    status: AssessmentResponseStatus

    response_text: str | None = None
    response_data: str | None = None
    source_reference: str | None = None

    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None

    marking_decision: MarkingDecisionOut | None = None
