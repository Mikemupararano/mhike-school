from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.assessment import AssessmentStatus


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
