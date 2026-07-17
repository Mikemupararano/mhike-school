from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReportingMode = Literal[
    "grade_card",
    "full_report",
]


class ReportSessionBase(BaseModel):
    """
    Shared configuration for a school reporting checkpoint.

    The existing ``term`` field is retained for backward compatibility.
    New clients should use ``checkpoint_name``.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    academic_year: str = Field(
        min_length=1,
        max_length=20,
    )

    # Retained temporarily for compatibility with the existing
    # database, frontend and API clients.
    term: str | None = Field(
        default=None,
        max_length=50,
    )

    # Flexible checkpoint name, for example:
    # Autumn 1, Spring Progress Check or End-of-Year Report.
    checkpoint_name: str | None = Field(
        default=None,
        max_length=100,
    )

    # Determines the checkpoint's position within the academic year.
    display_order: int = Field(
        default=1,
        ge=1,
    )

    reporting_mode: ReportingMode = "full_report"

    active: bool = True

    # ------------------------------------------------------------------
    # Report field configuration
    # ------------------------------------------------------------------

    include_work_covered: bool = True
    include_student_comment: bool = True

    include_exam_mark: bool = False
    include_exam_grade: bool = False

    include_attainment_grade: bool = False
    include_effort_grade: bool = False
    include_target_grade: bool = False
    include_ucas_predicted_grade: bool = False

    include_next_steps: bool = False

    include_tutor_comment: bool = False
    include_head_of_year_comment: bool = False
    include_headteacher_comment: bool = False

    # ------------------------------------------------------------------
    # Cumulative display configuration
    # ------------------------------------------------------------------

    show_previous_grades: bool = False
    show_previous_tutor_comments: bool = False
    show_progress_journey: bool = False

    # Records the source session when the administrator copies
    # configuration from an earlier checkpoint.
    copied_from_session_id: int | None = Field(
        default=None,
        ge=1,
    )


class ReportSessionCreate(ReportSessionBase):
    """Payload used when creating a reporting checkpoint."""

    pass


class ReportSessionUpdate(BaseModel):
    """
    Payload used to partially update a reporting checkpoint.

    Every field is optional so PATCH requests only change fields that
    were explicitly supplied.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    academic_year: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    # Retained temporarily for backward compatibility.
    term: str | None = Field(
        default=None,
        max_length=50,
    )

    checkpoint_name: str | None = Field(
        default=None,
        max_length=100,
    )

    display_order: int | None = Field(
        default=None,
        ge=1,
    )

    reporting_mode: ReportingMode | None = None

    active: bool | None = None

    # ------------------------------------------------------------------
    # Report field configuration
    # ------------------------------------------------------------------

    include_work_covered: bool | None = None
    include_student_comment: bool | None = None

    include_exam_mark: bool | None = None
    include_exam_grade: bool | None = None

    include_attainment_grade: bool | None = None
    include_effort_grade: bool | None = None
    include_target_grade: bool | None = None
    include_ucas_predicted_grade: bool | None = None

    include_next_steps: bool | None = None

    include_tutor_comment: bool | None = None
    include_head_of_year_comment: bool | None = None
    include_headteacher_comment: bool | None = None

    # ------------------------------------------------------------------
    # Cumulative display configuration
    # ------------------------------------------------------------------

    show_previous_grades: bool | None = None
    show_previous_tutor_comments: bool | None = None
    show_progress_journey: bool | None = None

    copied_from_session_id: int | None = Field(
        default=None,
        ge=1,
    )


class ReportSessionRead(ReportSessionBase):
    """Reporting checkpoint returned by the API."""

    id: int
    school_id: int

    published_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
