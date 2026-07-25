from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReportingMode = Literal[
    "grade_card",
    "full_report",
    "both",
]


class ReportSessionBase(BaseModel):
    """
    Shared configuration for a school reporting checkpoint.

    The existing ``term`` field is retained for backward compatibility.
    New clients should use ``checkpoint_name``.

    Teachers may save incomplete drafts. The ``require_*`` settings are
    intended to be enforced when a report is submitted, approved or
    published, rather than during ordinary draft saving.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Session identification
    # ------------------------------------------------------------------

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    academic_year: str = Field(
        min_length=1,
        max_length=20,
    )

    year_group: str = Field(
        min_length=1,
        max_length=50,
    )

    # Retained temporarily for compatibility with the existing database,
    # frontend and API clients.
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

    # grade_card:
    #     Produce a compact grade card only.
    #
    # full_report:
    #     Produce a full written report only.
    #
    # both:
    #     Produce both documents from the same StudentReport data.
    reporting_mode: ReportingMode = "full_report"

    active: bool = True

    # Report generation is optional. Manual report writing remains
    # available regardless of this setting.
    enable_report_generation: bool = True

    # ------------------------------------------------------------------
    # Branding and document-header configuration
    # ------------------------------------------------------------------

    include_school_name: bool = True
    include_school_logo: bool = True
    include_teacher_name: bool = True
    include_subject_name: bool = True

    # ------------------------------------------------------------------
    # Report field display configuration
    # ------------------------------------------------------------------

    include_work_covered: bool = True
    include_student_comment: bool = True

    include_exam_mark: bool = False
    include_exam_grade: bool = False

    include_effort_grade: bool = True
    include_attainment_grade: bool = True
    include_target_grade: bool = True

    include_gcse_predicted_grade: bool = False
    include_ucas_predicted_grade: bool = False

    include_next_steps: bool = False

    include_tutor_comment: bool = False
    include_head_of_year_comment: bool = False
    include_headteacher_comment: bool = False

    include_attendance: bool = False
    include_behaviour: bool = False

    # ------------------------------------------------------------------
    # Submission/publication validation configuration
    # ------------------------------------------------------------------

    require_student_comment: bool = True

    require_effort_grade: bool = True
    require_attainment_grade: bool = True
    require_target_grade: bool = True

    require_exam_mark: bool = False
    require_exam_grade: bool = False

    require_gcse_predicted_grade: bool = False
    require_ucas_predicted_grade: bool = False

    require_next_steps: bool = False

    require_tutor_comment: bool = False
    require_head_of_year_comment: bool = False
    require_headteacher_comment: bool = False

    # ------------------------------------------------------------------
    # Workflow editing policy
    # ------------------------------------------------------------------

    allow_teacher_edit_after_submission: bool = False
    allow_smt_edit_after_approval: bool = True

    # ------------------------------------------------------------------
    # Cumulative display configuration
    # ------------------------------------------------------------------

    show_previous_grades: bool = False
    show_previous_tutor_comments: bool = False
    show_progress_journey: bool = False

    # ------------------------------------------------------------------
    # Configuration-copy support
    # ------------------------------------------------------------------

    # Records the source session when the administrator copies
    # configuration from an earlier checkpoint.
    copied_from_session_id: int | None = Field(
        default=None,
        ge=1,
    )

    @model_validator(mode="after")
    def validate_required_fields_are_included(
        self,
    ) -> "ReportSessionBase":
        """
        Prevent creation of an internally contradictory session.

        A field cannot be required at submission or publication time if
        the same session does not include that field in the report form.
        """

        required_to_included = {
            "require_student_comment": "include_student_comment",
            "require_effort_grade": "include_effort_grade",
            "require_attainment_grade": "include_attainment_grade",
            "require_target_grade": "include_target_grade",
            "require_exam_mark": "include_exam_mark",
            "require_exam_grade": "include_exam_grade",
            "require_gcse_predicted_grade": ("include_gcse_predicted_grade"),
            "require_ucas_predicted_grade": ("include_ucas_predicted_grade"),
            "require_next_steps": "include_next_steps",
            "require_tutor_comment": "include_tutor_comment",
            "require_head_of_year_comment": ("include_head_of_year_comment"),
            "require_headteacher_comment": ("include_headteacher_comment"),
        }

        conflicts = [
            required_name
            for required_name, included_name in required_to_included.items()
            if (getattr(self, required_name) and not getattr(self, included_name))
        ]

        if conflicts:
            raise ValueError(
                "Required report fields must also be included: " + ", ".join(conflicts)
            )

        return self


class ReportSessionCreate(ReportSessionBase):
    """Payload used when creating a reporting checkpoint."""


class ReportSessionUpdate(BaseModel):
    """
    Payload used to partially update a reporting checkpoint.

    Every field is optional so PATCH requests only change fields that
    were explicitly supplied.

    Cross-field consistency must be checked after this payload is merged
    with the existing database record.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Session identification
    # ------------------------------------------------------------------

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

    year_group: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
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
    enable_report_generation: bool | None = None

    # ------------------------------------------------------------------
    # Branding and document-header configuration
    # ------------------------------------------------------------------

    include_school_name: bool | None = None
    include_school_logo: bool | None = None
    include_teacher_name: bool | None = None
    include_subject_name: bool | None = None

    # ------------------------------------------------------------------
    # Report field display configuration
    # ------------------------------------------------------------------

    include_work_covered: bool | None = None
    include_student_comment: bool | None = None

    include_exam_mark: bool | None = None
    include_exam_grade: bool | None = None

    include_effort_grade: bool | None = None
    include_attainment_grade: bool | None = None
    include_target_grade: bool | None = None

    include_gcse_predicted_grade: bool | None = None
    include_ucas_predicted_grade: bool | None = None

    include_next_steps: bool | None = None

    include_tutor_comment: bool | None = None
    include_head_of_year_comment: bool | None = None
    include_headteacher_comment: bool | None = None

    include_attendance: bool | None = None
    include_behaviour: bool | None = None

    # ------------------------------------------------------------------
    # Submission/publication validation configuration
    # ------------------------------------------------------------------

    require_student_comment: bool | None = None

    require_effort_grade: bool | None = None
    require_attainment_grade: bool | None = None
    require_target_grade: bool | None = None

    require_exam_mark: bool | None = None
    require_exam_grade: bool | None = None

    require_gcse_predicted_grade: bool | None = None
    require_ucas_predicted_grade: bool | None = None

    require_next_steps: bool | None = None

    require_tutor_comment: bool | None = None
    require_head_of_year_comment: bool | None = None
    require_headteacher_comment: bool | None = None

    # ------------------------------------------------------------------
    # Workflow editing policy
    # ------------------------------------------------------------------

    allow_teacher_edit_after_submission: bool | None = None
    allow_smt_edit_after_approval: bool | None = None

    # ------------------------------------------------------------------
    # Cumulative display configuration
    # ------------------------------------------------------------------

    show_previous_grades: bool | None = None
    show_previous_tutor_comments: bool | None = None
    show_progress_journey: bool | None = None

    # ------------------------------------------------------------------
    # Configuration-copy support
    # ------------------------------------------------------------------

    # Explicit null is permitted so an administrator can remove the
    # reference to the copied source session.
    copied_from_session_id: int | None = Field(
        default=None,
        ge=1,
    )


class ReportSessionStatistics(BaseModel):
    """
    Computed report counts for one reporting checkpoint.

    These values are not stored on the report_sessions table. They are
    calculated from StudentReport records by the repository or service.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    total_reports: int = Field(
        default=0,
        ge=0,
    )

    draft_count: int = Field(
        default=0,
        ge=0,
    )

    submitted_count: int = Field(
        default=0,
        ge=0,
    )

    tutor_review_count: int = Field(
        default=0,
        ge=0,
    )

    ready_for_smt_count: int = Field(
        default=0,
        ge=0,
    )

    approved_count: int = Field(
        default=0,
        ge=0,
    )

    published_count: int = Field(
        default=0,
        ge=0,
    )


class ReportSessionRead(
    ReportSessionBase,
    ReportSessionStatistics,
):
    """Reporting checkpoint returned by the API."""

    id: int = Field(
        ge=1,
    )

    school_id: int = Field(
        ge=1,
    )

    published_at: datetime | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )
