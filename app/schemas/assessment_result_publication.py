from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.assessment_result_publication import (
    AssessmentResultPublicationStatus,
)

# ---------------------------------------------------------------------------
# Publication configuration schemas
# ---------------------------------------------------------------------------


class AssessmentResultPublicationBase(BaseModel):
    """
    Shared assessment-result publication configuration.

    Ordinary classroom assessments default to:

        requires_approval = False

    so the owning course teacher may publish results directly once marking
    is fully finalised.

    Controlled assessments may opt into:

        requires_approval = True

    and must then be approved before release.
    """

    requires_approval: bool = False

    visible_to_students: bool = True
    visible_to_parents: bool = True

    include_mark: bool = True
    include_percentage: bool = True
    include_grade: bool = True
    include_question_breakdown: bool = False

    release_message: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator(
        "release_message",
    )
    @classmethod
    def clean_release_message(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


class AssessmentResultPublicationCreate(
    AssessmentResultPublicationBase,
):
    """
    Payload for creating result-publication configuration.
    """

    pass


class AssessmentResultPublicationUpdate(BaseModel):
    """
    Partial update payload.

    Explicit null is supported for ``release_message``.
    The endpoint layer must therefore preserve ``model_fields_set``.
    """

    requires_approval: bool | None = None

    visible_to_students: bool | None = None
    visible_to_parents: bool | None = None

    include_mark: bool | None = None
    include_percentage: bool | None = None
    include_grade: bool | None = None
    include_question_breakdown: bool | None = None

    release_message: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator(
        "release_message",
    )
    @classmethod
    def clean_release_message(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


class AssessmentResultPublicationOut(BaseModel):
    """
    Public staff-facing representation of result-publication configuration.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int

    status: AssessmentResultPublicationStatus

    scheduled_for: datetime | None = None

    published_at: datetime | None = None
    published_by_id: int | None = None

    withdrawn_at: datetime | None = None
    withdrawn_by_id: int | None = None
    withdrawal_reason: str | None = None

    requires_approval: bool

    approved_at: datetime | None = None
    approved_by_id: int | None = None
    approval_note: str | None = None

    visible_to_students: bool
    visible_to_parents: bool

    include_mark: bool
    include_percentage: bool
    include_grade: bool
    include_question_breakdown: bool

    release_message: str | None = None

    created_by_id: int

    created_at: datetime
    updated_at: datetime

    is_published: bool
    is_scheduled: bool
    is_approved: bool
    can_release: bool


# ---------------------------------------------------------------------------
# Approval schemas
# ---------------------------------------------------------------------------


class AssessmentResultPublicationApprovalRequest(BaseModel):
    """
    Optional note supplied when approving a controlled release.
    """

    approval_note: str | None = None

    @field_validator(
        "approval_note",
    )
    @classmethod
    def clean_approval_note(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


# ---------------------------------------------------------------------------
# Scheduling schemas
# ---------------------------------------------------------------------------


class AssessmentResultPublicationScheduleRequest(BaseModel):
    """
    Schedule assessment results for future publication.
    """

    scheduled_for: datetime


# ---------------------------------------------------------------------------
# Withdrawal schemas
# ---------------------------------------------------------------------------


class AssessmentResultPublicationWithdrawRequest(BaseModel):
    """
    Withdraw a published or scheduled release.
    """

    withdrawal_reason: str | None = None

    @field_validator(
        "withdrawal_reason",
    )
    @classmethod
    def clean_withdrawal_reason(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


# ---------------------------------------------------------------------------
# Visibility schemas
# ---------------------------------------------------------------------------


class AssessmentPublishedResultVisibilityOut(BaseModel):
    """
    Minimal publication information used by student/parent result services.

    This schema intentionally contains no marks or grades. It only describes
    whether an active release exists and which result fields may be exposed.
    """

    assessment_id: int

    status: AssessmentResultPublicationStatus

    visible_to_students: bool
    visible_to_parents: bool

    include_mark: bool
    include_percentage: bool
    include_grade: bool
    include_question_breakdown: bool

    release_message: str | None = None

    published_at: datetime | None = None
