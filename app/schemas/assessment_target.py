from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

# ---------------------------------------------------------------------------
# Shared target fields
# ---------------------------------------------------------------------------


class AssessmentTargetBase(BaseModel):
    """
    Shared assessment-target fields.
    """

    grade_label: str = Field(
        min_length=1,
        max_length=100,
    )

    grade_points: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
    )

    academic_year: str | None = Field(
        default=None,
        max_length=50,
    )

    notes: str | None = None


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class AssessmentTargetCreate(AssessmentTargetBase):
    """
    Payload used to create one student/course assessment target.
    """

    school_id: int | None = Field(
        default=None,
        ge=1,
    )

    student_id: int = Field(
        ge=1,
    )

    course_id: int = Field(
        ge=1,
    )


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class AssessmentTargetUpdate(BaseModel):
    """
    PATCH-style assessment-target update.

    Fields omitted from the request remain unchanged.

    Nullable fields may explicitly be supplied as None to clear them.
    """

    grade_label: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    grade_points: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
    )

    academic_year: str | None = Field(
        default=None,
        max_length=50,
    )

    notes: str | None = None


# ---------------------------------------------------------------------------
# Staff-facing target output
# ---------------------------------------------------------------------------


class AssessmentTargetOut(BaseModel):
    """
    Fully resolved staff-facing assessment target.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    school_id: int

    student_id: int
    student_name: str | None = None

    course_id: int
    course_title: str | None = None

    subject_id: int | None = None
    subject_name: str | None = None

    grade_label: str
    grade_points: Decimal | None = None

    academic_year: str | None = None
    notes: str | None = None

    set_by_id: int
    set_by_name: str | None = None

    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Latest formal assessment result
# ---------------------------------------------------------------------------


class AssessmentTargetLatestResultOut(BaseModel):
    """
    Latest formal assessment result used for target comparison.

    Extra fields are intentionally preserved because the established
    assessment-trends payload already carries useful assessment metadata and
    visibility information.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    assessment_id: int | None = None
    candidate_id: int | None = None
    student_id: int | None = None

    assessment_title: str | None = None
    assessment_type: str | None = None

    academic_year: str | None = None
    term: str | None = None

    scheduled_at: datetime | None = None
    assessment_date: datetime | None = None

    course_id: int | None = None
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

    visibility: dict[str, Any] | None = None

    percentage_change: Decimal | None = None


# ---------------------------------------------------------------------------
# Target-progress output
# ---------------------------------------------------------------------------


AssessmentTargetProgressStatus = Literal[
    "above_target",
    "on_target",
    "below_target",
    "not_comparable",
]


AssessmentTargetProgressAudience = Literal[
    "student",
    "parent",
]


class AssessmentTargetProgressOut(BaseModel):
    """
    Student/parent target-versus-current-performance response.
    """

    audience: AssessmentTargetProgressAudience

    target: AssessmentTargetOut

    latest_result: AssessmentTargetLatestResultOut | None = None

    status: AssessmentTargetProgressStatus

    grade_points_difference: Decimal | None = None

    target_grade_label: str
    target_grade_points: Decimal | None = None

    current_grade: str | None = None
    current_grade_points: Decimal | None = None
