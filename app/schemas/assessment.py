from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.models.assessment import AssessmentStatus

# ----------------------------------------------------------------------
# Assessment section schemas
# ----------------------------------------------------------------------


class AssessmentSectionCreate(BaseModel):
    """
    Payload used to create a section within a draft assessment.
    """

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    order: int = Field(
        default=1,
        gt=0,
    )

    is_optional: bool = False


class AssessmentSectionUpdate(BaseModel):
    """
    Payload used to edit a section within a draft assessment.

    Fields are optional because PATCH semantics are used.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    order: int | None = Field(
        default=None,
        gt=0,
    )

    is_optional: bool | None = None


class AssessmentSectionOut(BaseModel):
    """
    Lightweight assessment-section representation.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int

    title: str
    description: str | None = None

    order: int
    is_optional: bool


# ----------------------------------------------------------------------
# Assessment question schemas
# ----------------------------------------------------------------------


class AssessmentQuestionCreate(BaseModel):
    """
    Payload used to create a question within a draft assessment.

    Questions may optionally belong to a section and/or another question.
    """

    section_id: int | None = Field(
        default=None,
        gt=0,
    )

    parent_question_id: int | None = Field(
        default=None,
        gt=0,
    )

    question_number: str = Field(
        min_length=1,
        max_length=50,
    )

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    prompt: str | None = None

    maximum_mark: Decimal = Field(
        ge=Decimal("0"),
        max_digits=8,
        decimal_places=2,
    )

    order: int = Field(
        default=1,
        gt=0,
    )

    is_markable: bool = True


class AssessmentQuestionUpdate(BaseModel):
    """
    Payload used to edit a question within a draft assessment.

    Fields are optional because PATCH semantics are used.

    Nullable relationship fields deliberately support explicit None:

        {"section_id": null}

    removes the section assignment, while omitting ``section_id`` leaves
    the current assignment unchanged.

    The endpoint must therefore inspect ``model_fields_set`` rather than
    relying only on field values.
    """

    section_id: int | None = Field(
        default=None,
        gt=0,
    )

    parent_question_id: int | None = Field(
        default=None,
        gt=0,
    )

    question_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    prompt: str | None = None

    maximum_mark: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=8,
        decimal_places=2,
    )

    order: int | None = Field(
        default=None,
        gt=0,
    )

    is_markable: bool | None = None


class AssessmentQuestionOut(BaseModel):
    """
    Lightweight assessment-question representation.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    assessment_id: int

    section_id: int | None = None
    parent_question_id: int | None = None

    question_number: str

    title: str | None = None
    prompt: str | None = None

    maximum_mark: Decimal

    order: int
    is_markable: bool


# ----------------------------------------------------------------------
# Assessment definition schemas
# ----------------------------------------------------------------------


class AssessmentCreate(BaseModel):
    """
    Payload used to create a new draft assessment.
    """

    course_id: int = Field(
        gt=0,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    assessment_type: str | None = Field(
        default=None,
        max_length=100,
    )

    academic_year: str | None = Field(
        default=None,
        max_length=50,
    )

    term: str | None = Field(
        default=None,
        max_length=100,
    )

    anonymous_marking: bool = False

    scheduled_at: datetime | None = None
    closes_at: datetime | None = None

    @model_validator(
        mode="after",
    )
    def validate_date_window(
        self,
    ) -> "AssessmentCreate":
        """
        Ensure the closing time follows the scheduled time.
        """

        if (
            self.scheduled_at is not None
            and self.closes_at is not None
            and self.closes_at <= self.scheduled_at
        ):
            raise ValueError(
                "Assessment closing time must be later than its scheduled time.",
            )

        return self


class AssessmentUpdate(BaseModel):
    """
    Payload used to edit an existing draft assessment.

    Fields are optional because PATCH semantics are used.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    assessment_type: str | None = Field(
        default=None,
        max_length=100,
    )

    academic_year: str | None = Field(
        default=None,
        max_length=50,
    )

    term: str | None = Field(
        default=None,
        max_length=100,
    )

    anonymous_marking: bool | None = None

    scheduled_at: datetime | None = None
    closes_at: datetime | None = None


class AssessmentStatusUpdate(BaseModel):
    """
    Payload for an explicit assessment lifecycle transition.
    """

    status: AssessmentStatus


class AssessmentOut(BaseModel):
    """
    Full assessment response model.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    school_id: int
    course_id: int
    created_by_id: int

    title: str
    description: str | None = None

    assessment_type: str | None = None
    academic_year: str | None = None
    term: str | None = None

    status: AssessmentStatus
    anonymous_marking: bool

    scheduled_at: datetime | None = None
    closes_at: datetime | None = None

    created_at: datetime
    updated_at: datetime

    sections: list[AssessmentSectionOut] = Field(
        default_factory=list,
    )

    questions: list[AssessmentQuestionOut] = Field(
        default_factory=list,
    )
