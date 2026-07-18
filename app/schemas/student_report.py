from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class StudentReportBase(BaseModel):
    """
    Shared student-report fields.

    ``grade`` and ``term`` are retained temporarily for compatibility
    with existing database records, tests and frontend code.

    Preferred Reporting V2 fields:

    - attainment_grade instead of grade
    - checkpoint_name instead of term
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Report identification
    # ------------------------------------------------------------------

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    academic_year: str = Field(
        min_length=1,
        max_length=20,
    )

    # Legacy field retained during migration.
    term: str | None = Field(
        default=None,
        max_length=50,
    )

    checkpoint_name: str | None = Field(
        default=None,
        max_length=100,
    )

    subject_name: str | None = Field(
        default=None,
        max_length=100,
    )

    # ------------------------------------------------------------------
    # Report content
    # ------------------------------------------------------------------

    # A report may remain blank while in draft status.
    # Repository validation determines what is required at submission.
    report_text: str = ""

    # Legacy field retained until work covered is moved to a shared
    # class/subject reporting structure.
    work_covered: str | None = None

    teacher_notes: str | None = None
    generated_report_text: str | None = None
    next_steps: str | None = None

    # ------------------------------------------------------------------
    # Assessment information
    # ------------------------------------------------------------------

    # Legacy grade field retained temporarily.
    grade: str | None = Field(
        default=None,
        max_length=50,
    )

    attainment_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    effort_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    target_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    # Required at submission when the linked ReportSession has
    # include_exam_grade=True.
    exam_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    # Exam mark remains optional.
    exam_mark: int | None = Field(
        default=None,
        ge=0,
    )

    exam_max_mark: int | None = Field(
        default=None,
        gt=0,
    )

    ucas_predicted_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    # ------------------------------------------------------------------
    # Pastoral and senior comments
    # ------------------------------------------------------------------

    tutor_comment: str | None = None
    head_of_year_comment: str | None = None
    headteacher_comment: str | None = None

    @model_validator(mode="after")
    def validate_exam_marks(self) -> StudentReportBase:
        """
        Validate complete create/read payloads.

        An exam maximum mark cannot exist without an exam mark, and the
        entered mark cannot exceed the maximum.
        """

        if self.exam_max_mark is not None and self.exam_mark is None:
            raise ValueError(
                "Exam maximum mark cannot be entered without an exam mark."
            )

        if (
            self.exam_mark is not None
            and self.exam_max_mark is not None
            and self.exam_mark > self.exam_max_mark
        ):
            raise ValueError("Exam mark cannot be greater than the exam maximum mark.")

        return self


class StudentReportCreate(StudentReportBase):
    """
    Payload used when a teacher creates a draft report.

    ``teacher_id`` is accepted for backward compatibility with the
    existing API tests and frontend payloads. The repository must continue
    using the authenticated user's ID as the authoritative teacher ID.
    """

    student_id: int = Field(
        ge=1,
    )

    teacher_id: int | None = Field(
        default=None,
        ge=1,
    )

    report_session_id: int | None = Field(
        default=None,
        ge=1,
    )


class StudentReportUpdate(BaseModel):
    """
    Payload used to update a student report.

    Every field is optional so that only explicitly supplied values are
    changed. Repository workflow validation determines whether the report
    is currently editable.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Report identification
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

    # Legacy field retained during migration.
    term: str | None = Field(
        default=None,
        max_length=50,
    )

    checkpoint_name: str | None = Field(
        default=None,
        max_length=100,
    )

    subject_name: str | None = Field(
        default=None,
        max_length=100,
    )

    # ------------------------------------------------------------------
    # Report content
    # ------------------------------------------------------------------

    report_text: str | None = None
    work_covered: str | None = None
    teacher_notes: str | None = None
    generated_report_text: str | None = None
    next_steps: str | None = None

    # ------------------------------------------------------------------
    # Assessment information
    # ------------------------------------------------------------------

    # Legacy field retained temporarily.
    grade: str | None = Field(
        default=None,
        max_length=50,
    )

    attainment_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    effort_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    target_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    exam_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    exam_mark: int | None = Field(
        default=None,
        ge=0,
    )

    exam_max_mark: int | None = Field(
        default=None,
        gt=0,
    )

    ucas_predicted_grade: str | None = Field(
        default=None,
        max_length=50,
    )

    # ------------------------------------------------------------------
    # Pastoral and senior comments
    # ------------------------------------------------------------------

    tutor_comment: str | None = None
    head_of_year_comment: str | None = None
    headteacher_comment: str | None = None

    # ------------------------------------------------------------------
    # Ownership and session
    # ------------------------------------------------------------------

    teacher_id: int | None = Field(
        default=None,
        ge=1,
    )

    report_session_id: int | None = Field(
        default=None,
        ge=1,
    )

    @model_validator(mode="after")
    def validate_exam_marks(self) -> StudentReportUpdate:
        """
        Validate exam fields supplied in a partial update.

        Because this is a PATCH-style payload, repository validation must
        also check the final merged model state after updates are applied.
        """

        supplied_fields = self.model_fields_set

        if (
            "exam_max_mark" in supplied_fields
            and self.exam_max_mark is not None
            and "exam_mark" in supplied_fields
            and self.exam_mark is None
        ):
            raise ValueError(
                "Exam maximum mark cannot be entered without an exam mark."
            )

        if (
            self.exam_mark is not None
            and self.exam_max_mark is not None
            and self.exam_mark > self.exam_max_mark
        ):
            raise ValueError("Exam mark cannot be greater than the exam maximum mark.")

        return self


class StudentReportTutorCorrection(BaseModel):
    """
    Changes a tutor may make while checking a submitted report.

    The tutor may correct the report wording and enter a report-facing
    tutor comment. Workflow comments remain separate.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    report_text: str = Field(
        min_length=1,
    )

    tutor_comment: str | None = None

    tutor_review_comments: str | None = Field(
        default=None,
        max_length=5000,
    )


class StudentReportTutorDecision(BaseModel):
    """
    Workflow comments supplied when a tutor returns a report or marks it
    ready for SMT review.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    tutor_review_comments: str | None = Field(
        default=None,
        max_length=5000,
    )


class StudentReportReviewDecision(BaseModel):
    """
    Workflow comments supplied by SMT or a School Admin when approving or
    returning a report.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    review_comments: str | None = Field(
        default=None,
        max_length=5000,
    )


class StudentReportReviewDashboard(BaseModel):
    """
    Counts of reports at active workflow stages.

    Fields are optional so older API consumers may receive only populated
    statuses, while newer clients can still receive the complete Reporting
    V2 workflow when the endpoint includes those values.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    draft: int | None = Field(
        default=None,
        ge=0,
    )

    submitted: int | None = Field(
        default=None,
        ge=0,
    )

    tutor_review: int | None = Field(
        default=None,
        ge=0,
    )

    returned_by_tutor: int | None = Field(
        default=None,
        ge=0,
    )

    ready_for_smt: int | None = Field(
        default=None,
        ge=0,
    )

    returned_by_smt: int | None = Field(
        default=None,
        ge=0,
    )

    approved: int | None = Field(
        default=None,
        ge=0,
    )

    published: int | None = Field(
        default=None,
        ge=0,
    )


class StudentReportCompletionRow(BaseModel):
    """One pupil within a report completion overview."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    student_id: int = Field(ge=1)
    student_name: str
    report_id: int | None = None
    status: str
    last_updated: datetime | None = None


class StudentReportCompletionOverview(BaseModel):
    """Teacher completion dashboard for a class/report session."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    class_id: int = Field(ge=1)
    report_session_id: int = Field(ge=1)
    teacher_id: int | None = Field(default=None, ge=1)

    total_students: int = Field(ge=0)
    completed: int = Field(ge=0)
    outstanding: int = Field(ge=0)

    not_started: int = Field(ge=0)
    draft: int = Field(ge=0)
    returned_by_tutor: int = Field(ge=0)
    returned_by_smt: int = Field(ge=0)
    submitted: int = Field(ge=0)
    tutor_review: int = Field(ge=0)
    ready_for_smt: int = Field(ge=0)
    approved: int = Field(ge=0)
    published: int = Field(ge=0)

    completion_percentage: float = Field(ge=0, le=100)

    students: list[StudentReportCompletionRow]


class StudentReportRead(StudentReportBase):
    """Complete student-report representation returned by the API."""

    id: int
    school_id: int
    student_id: int

    teacher_id: int | None
    report_session_id: int | None

    status: str

    # ------------------------------------------------------------------
    # Teacher submission
    # ------------------------------------------------------------------

    submitted_at: datetime | None
    submitted_by_id: int | None

    # ------------------------------------------------------------------
    # Tutor review
    # ------------------------------------------------------------------

    tutor_reviewed_at: datetime | None
    tutor_reviewed_by_id: int | None
    tutor_review_comments: str | None

    ready_for_smt_at: datetime | None
    ready_for_smt_by_id: int | None

    # ------------------------------------------------------------------
    # SMT review
    # ------------------------------------------------------------------

    reviewed_at: datetime | None
    reviewed_by_id: int | None
    review_comments: str | None

    # ------------------------------------------------------------------
    # Optional senior review
    # ------------------------------------------------------------------

    head_of_year_reviewed_at: datetime | None
    head_of_year_reviewed_by_id: int | None

    headteacher_reviewed_at: datetime | None
    headteacher_reviewed_by_id: int | None

    # ------------------------------------------------------------------
    # Publication
    # ------------------------------------------------------------------

    published: bool
    published_at: datetime | None
    published_by_id: int | None

    # ------------------------------------------------------------------
    # Audit information
    # ------------------------------------------------------------------

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
