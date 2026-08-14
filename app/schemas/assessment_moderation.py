from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment_moderation import (
    AssessmentModerationItemOutcome,
    AssessmentModerationOutcome,
    AssessmentModerationReviewStatus,
    AssessmentModerationSamplingMethod,
)

# ----------------------------------------------------------------------
# Shared configuration
# ----------------------------------------------------------------------


class AssessmentModerationSchema(BaseModel):
    """
    Base schema configuration for assessment moderation resources.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


# ----------------------------------------------------------------------
# Review input schemas
# ----------------------------------------------------------------------


class AssessmentModerationReviewCreate(
    AssessmentModerationSchema,
):
    """
    Request body for creating a moderation review.

    ``script_id`` is expected to come from the route path rather than the
    request body.
    """

    moderator_id: int = Field(
        gt=0,
    )

    sampling_method: AssessmentModerationSamplingMethod = (
        AssessmentModerationSamplingMethod.MANUAL
    )

    reason: str | None = Field(
        default=None,
        max_length=1000,
    )

    notes: str | None = None

    sample_description: str | None = None


class AssessmentModerationReviewComplete(
    AssessmentModerationSchema,
):
    """
    Request body for completing an active moderation review.
    """

    outcome: AssessmentModerationOutcome

    notes: str | None = None


class AssessmentModerationReviewCancel(
    AssessmentModerationSchema,
):
    """
    Request body for cancelling a pending or active moderation review.
    """

    cancellation_reason: str = Field(
        min_length=1,
        max_length=1000,
    )


# ----------------------------------------------------------------------
# Moderation item input schemas
# ----------------------------------------------------------------------


class AssessmentModerationItemCreate(
    AssessmentModerationSchema,
):
    """
    Request body for recording one reviewed response.

    ``mark_after`` may be omitted when the current mark is being confirmed.

    For ADJUSTED outcomes, the service requires ``mark_after`` to differ from
    the current marking decision.
    """

    response_id: int = Field(
        gt=0,
    )

    marking_decision_id: int = Field(
        gt=0,
    )

    outcome: AssessmentModerationItemOutcome

    mark_after: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=8,
        decimal_places=2,
    )

    moderator_comment: str | None = None

    evidence_notes: str | None = None


# ----------------------------------------------------------------------
# Moderation item read schemas
# ----------------------------------------------------------------------


class AssessmentModerationItemRead(
    AssessmentModerationSchema,
):
    """
    Immutable response-level moderation evidence.
    """

    id: int

    review_id: int

    response_id: int

    marking_decision_id: int

    outcome: AssessmentModerationItemOutcome

    mark_before_snapshot: Decimal | None = None

    mark_after_snapshot: Decimal | None = None

    maximum_mark_snapshot: Decimal | None = None

    mark_changed: bool

    decision_status_before_snapshot: str | None = None

    decision_status_after_snapshot: str | None = None

    moderator_comment: str | None = None

    evidence_notes: str | None = None

    reviewed_by_id: int

    reviewed_at: datetime


# ----------------------------------------------------------------------
# Moderation review read schemas
# ----------------------------------------------------------------------


class AssessmentModerationReviewRead(
    AssessmentModerationSchema,
):
    """
    Full moderation review representation.

    ``items`` contains the immutable response-level evidence belonging to the
    review when loaded by the service.
    """

    id: int

    school_id: int

    assessment_id: int

    candidate_id: int

    script_id: int

    review_number: int

    status: AssessmentModerationReviewStatus

    outcome: AssessmentModerationOutcome | None = None

    sampling_method: AssessmentModerationSamplingMethod

    moderator_id: int

    initiated_by_id: int

    reason: str | None = None

    notes: str | None = None

    sample_description: str | None = None

    created_at: datetime

    started_at: datetime | None = None

    completed_at: datetime | None = None

    cancelled_at: datetime | None = None

    cancelled_by_id: int | None = None

    cancellation_reason: str | None = None

    items: list[AssessmentModerationItemRead] = Field(
        default_factory=list,
    )


class AssessmentModerationReviewSummary(
    AssessmentModerationSchema,
):
    """
    Compact moderation review representation for collection endpoints.

    Item evidence is intentionally omitted to avoid unnecessarily large
    assessment-wide moderation responses.
    """

    id: int

    school_id: int

    assessment_id: int

    candidate_id: int

    script_id: int

    review_number: int

    status: AssessmentModerationReviewStatus

    outcome: AssessmentModerationOutcome | None = None

    sampling_method: AssessmentModerationSamplingMethod

    moderator_id: int

    initiated_by_id: int

    reason: str | None = None

    created_at: datetime

    started_at: datetime | None = None

    completed_at: datetime | None = None

    cancelled_at: datetime | None = None


# ----------------------------------------------------------------------
# Collection schemas
# ----------------------------------------------------------------------


class AssessmentModerationReviewList(
    AssessmentModerationSchema,
):
    """
    Container for moderation review collections.
    """

    items: list[AssessmentModerationReviewSummary]

    total: int = Field(
        ge=0,
    )
