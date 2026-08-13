from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
)

TrendAudience = Literal[
    "student",
    "parent",
]


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


class AssessmentTrendFiltersOut(BaseModel):
    """
    Filters applied to a longitudinal assessment trend.
    """

    school_id: int | None = None
    course_id: int | None = None
    subject_id: int | None = None

    academic_year: str | None = None
    term: str | None = None


# ---------------------------------------------------------------------------
# Publication visibility
# ---------------------------------------------------------------------------


class AssessmentTrendVisibilityOut(BaseModel):
    """
    Result-content visibility inherited from assessment publication.
    """

    include_mark: bool
    include_percentage: bool
    include_grade: bool
    include_question_breakdown: bool


# ---------------------------------------------------------------------------
# Trend point
# ---------------------------------------------------------------------------


class AssessmentTrendPointOut(BaseModel):
    """
    One published assessment result in chronological trend order.

    The point represents the already-authorised published result for one
    assessment candidate. Hidden result fields remain ``None`` and therefore
    cannot influence trend calculations indirectly.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    assessment_id: int
    candidate_id: int
    student_id: int

    assessment_title: str
    assessment_type: str | None = None

    academic_year: str | None = None
    term: str | None = None

    scheduled_at: datetime | None = None
    assessment_date: datetime

    course_id: int
    course_title: str | None = None

    subject_id: int | None = None
    subject_name: str | None = None
    subject_code: str | None = None

    exam_board: str | None = None
    qualification: str | None = None
    specification_code: str | None = None

    script_id: int | None = None
    script_version: int | None = None

    mark_awarded: Decimal | None = None
    percentage: Decimal | None = None

    grade: str | None = None
    grade_points: Decimal | None = None
    is_pass: bool | None = None

    published_at: datetime | None = None

    visibility: AssessmentTrendVisibilityOut | None = None

    percentage_change: Decimal | None = None


# ---------------------------------------------------------------------------
# Base trend output
# ---------------------------------------------------------------------------


class AssessmentTrendOut(BaseModel):
    """
    Longitudinal published assessment performance for one student.

    Only audience-visible published values contribute to the derived summary
    statistics.
    """

    student_id: int
    audience: TrendAudience

    filters: AssessmentTrendFiltersOut

    assessment_count: int

    # ------------------------------------------------------------------
    # Percentage summary
    # ------------------------------------------------------------------

    percentage_result_count: int

    average_percentage: Decimal | None = None
    first_percentage: Decimal | None = None
    latest_percentage: Decimal | None = None
    overall_percentage_change: Decimal | None = None

    highest_percentage: Decimal | None = None
    lowest_percentage: Decimal | None = None

    # ------------------------------------------------------------------
    # Grade-points summary
    # ------------------------------------------------------------------

    grade_points_result_count: int

    average_grade_points: Decimal | None = None
    first_grade_points: Decimal | None = None
    latest_grade_points: Decimal | None = None
    overall_grade_points_change: Decimal | None = None

    # ------------------------------------------------------------------
    # Chronological results
    # ------------------------------------------------------------------

    points: list[AssessmentTrendPointOut]


# ---------------------------------------------------------------------------
# Audience-specific outputs
# ---------------------------------------------------------------------------


class StudentAssessmentTrendOut(
    AssessmentTrendOut,
):
    """
    Published longitudinal assessment trend for the logged-in student.
    """

    audience: Literal["student"]


class ParentStudentAssessmentTrendOut(
    AssessmentTrendOut,
):
    """
    Published longitudinal assessment trend for an authorised linked child.
    """

    audience: Literal["parent"]
