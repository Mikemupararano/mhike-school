from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment_response import (
    AssessmentResponseStatus,
    MarkingDecisionStatus,
)

# ---------------------------------------------------------------------------
# Assessment response payloads
# ---------------------------------------------------------------------------


class AssessmentResponseCreate(BaseModel):
    """
    Payload for creating one response for a script/question pair.
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


class AssessmentResponseUpdate(BaseModel):
    """
    Payload for updating editable response content.
    """

    response_text: str | None = None
    response_data: str | None = None

    source_reference: str | None = Field(
        default=None,
        max_length=1000,
    )


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
    Payload for starting marking on one submitted response.
    """

    marker_comment: str | None = None


class MarkingDecisionUpdate(BaseModel):
    """
    Payload for updating the authoritative question-level result.
    """

    mark_awarded: Decimal | None = Field(
        default=None,
        ge=0,
    )

    marker_comment: str | None = None


class MarkingDecisionStatusUpdate(BaseModel):
    """
    Payload for an explicit marking-decision lifecycle transition.

    ``moderation_comment`` is used when moving a completed decision into
    REVIEWED status.
    """

    status: MarkingDecisionStatus

    moderation_comment: str | None = None


class MarkingReviewRequest(BaseModel):
    """
    Payload for reviewing or moderating a completed marking decision.
    """

    moderation_comment: str | None = None


# ---------------------------------------------------------------------------
# Mark-scheme item award payloads
# ---------------------------------------------------------------------------


class MarkSchemeItemAwardCreate(BaseModel):
    """
    Payload for creating or updating one criterion-level award.
    """

    mark_scheme_item_id: int = Field(
        gt=0,
    )

    marks_awarded: Decimal = Field(
        ge=0,
    )

    marker_note: str | None = None


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


class AssessmentResponseOut(BaseModel):
    """
    Assessment response representation.

    The nested marking decision is included when one exists so a marking
    client can retrieve the current question-level result and supporting
    criterion awards without making a separate request.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    script_id: int
    question_id: int

    status: AssessmentResponseStatus

    response_text: str | None = None
    response_data: str | None = None
    source_reference: str | None = None

    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None

    marking_decision: MarkingDecisionOut | None = None
