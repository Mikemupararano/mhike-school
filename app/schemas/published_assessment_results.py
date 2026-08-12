from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class PublishedAssessmentResultVisibilityOut(BaseModel):
    """
    Describe which parts of a published assessment result are visible.

    These flags mirror the assessment-result publication configuration and
    allow the frontend to render the result consistently without inferring
    why a field is absent.
    """

    include_mark: bool
    include_percentage: bool
    include_grade: bool
    include_question_breakdown: bool


class PublishedAssessmentQuestionResultOut(BaseModel):
    """
    Public question-level result representation.

    The assessment-results layer may expose richer question structures over
    time, so this schema deliberately permits additional result fields while
    retaining the common identifiers and mark values where available.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    question_id: int | None = None
    question_number: str | None = None

    maximum_mark: Decimal | None = None
    mark_awarded: Decimal | None = None

    percentage: Decimal | None = None

    status: str | None = None


class PublishedAssessmentResultOut(BaseModel):
    """
    Published assessment result visible to a student or linked parent.

    Values hidden by publication configuration remain ``None`` rather than
    being silently substituted with staff-only values.

    Grades remain derived from the active assessment grading scheme and are
    never persisted here.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    assessment_id: int
    candidate_id: int
    student_id: int

    candidate_number: str | None = None

    script_id: int | None = None
    script_version: int | None = None

    mark_awarded: Decimal | None = None
    percentage: Decimal | None = None

    grade: str | None = None
    grade_points: Decimal | None = None
    is_pass: bool | None = None

    question_breakdown: (
        list[PublishedAssessmentQuestionResultOut | dict[str, Any]] | None
    ) = None

    release_message: str | None = Field(
        default=None,
        max_length=1000,
    )

    published_at: datetime | None = None

    visibility: PublishedAssessmentResultVisibilityOut


class StudentPublishedAssessmentResultOut(
    PublishedAssessmentResultOut,
):
    """
    Published result returned to the student who owns the candidate record.
    """

    pass


class ParentPublishedAssessmentResultOut(
    PublishedAssessmentResultOut,
):
    """
    Published result returned to an authorised parent for a linked child.
    """

    pass
