from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ReportSession(Base):
    """
    Defines one reporting checkpoint for a school.

    A reporting session belongs to a school, academic year and year group.
    It controls the fields collected from teachers and the documents
    produced from the shared StudentReport data.

    Supported output modes:

        grade_card
            Produce a compact grade card only.

        full_report
            Produce a full written report only.

        both
            Produce both the grade card and full written report from the
            same StudentReport data.

    Teachers may always type the final report manually. Where report
    generation is enabled, teacher notes or prompts may be used to create
    an editable suggestion, but generated text must never be compulsory.

    Workflow stages indicate progress but must not create a dependency on
    one named member of staff. Authorised tutors, Heads of Year, the
    Headmaster, SMT, School Admin and Platform Admin may continue
    unpublished reports when an earlier contributor is unavailable.

    Existing fields such as ``term`` are retained for backward
    compatibility. New code should primarily use ``checkpoint_name``.
    """

    __tablename__ = "report_sessions"

    __table_args__ = (
        CheckConstraint(
            "reporting_mode IN ('grade_card', 'full_report', 'both')",
            name="ck_report_sessions_reporting_mode",
        ),
        CheckConstraint(
            "display_order >= 1",
            name="ck_report_sessions_display_order_positive",
        ),
        Index(
            "ix_report_sessions_school_academic_year",
            "school_id",
            "academic_year",
        ),
        Index(
            "ix_report_sessions_school_year_group",
            "school_id",
            "year_group",
        ),
        Index(
            "ix_report_sessions_school_year_group_active",
            "school_id",
            "year_group",
            "active",
        ),
    )

    # ------------------------------------------------------------------
    # Identity and ownership
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schools.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Session identification
    # ------------------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    academic_year: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
    )

    # Dedicated cohort identifier, for example:
    # Year 7, Year 10, Year 13, Sixth Form or Reception.
    #
    # This should be used for filtering and reporting rather than
    # inferring the year group from the session title.
    year_group: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Reporting checkpoint
    # ------------------------------------------------------------------

    # Legacy reporting-period field retained for compatibility with
    # existing data, API clients, frontend pages and tests.
    term: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Flexible school-defined checkpoint, for example:
    # Autumn 1, Spring 2, Progress Check 3 or Final Report.
    checkpoint_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    # Controls checkpoint ordering within the academic year.
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )

    # Supported values:
    #
    # grade_card
    #     Grade Card only.
    #
    # full_report
    #     Full written report only.
    #
    # both
    #     Grade Card and Full Report from the same saved report data.
    reporting_mode: Mapped[str] = mapped_column(
        String(30),
        default="full_report",
        server_default="full_report",
        nullable=False,
        index=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    # Generation is an optional time-saving tool. Manual report writing
    # remains available regardless of this setting.
    enable_report_generation: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # The date on which the session was published as a whole.
    # Individual StudentReport records retain their own publication audit.
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Branding and document-header configuration
    # ------------------------------------------------------------------

    include_school_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_school_logo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_teacher_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_subject_name: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Report field display configuration
    # ------------------------------------------------------------------

    include_work_covered: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Controls whether the editable teacher-written or generated report
    # narrative is included.
    include_student_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_exam_mark: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_exam_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_effort_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_attainment_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    include_target_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    include_gcse_predicted_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_ucas_predicted_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_next_steps: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_tutor_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_head_of_year_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_headteacher_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_attendance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    include_behaviour: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Submission / publication validation
    # ------------------------------------------------------------------

    # Drafts may always be saved incomplete. These settings are enforced
    # only when reports move through workflow stages.

    require_student_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_effort_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_attainment_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_target_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    require_exam_mark: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_exam_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_gcse_predicted_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_ucas_predicted_grade: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_next_steps: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_tutor_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_head_of_year_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    require_headteacher_comment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Workflow editing policy
    # ------------------------------------------------------------------

    allow_teacher_edit_after_submission: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    allow_smt_edit_after_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Cumulative report configuration
    # ------------------------------------------------------------------

    show_previous_grades: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    show_previous_tutor_comments: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    show_progress_journey: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Configuration copy support
    # ------------------------------------------------------------------

    copied_from_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "report_sessions.id",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Audit fields
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    school: Mapped["School"] = relationship(
        "School",
        lazy="selectin",
    )

    copied_from_session: Mapped["ReportSession | None"] = relationship(
        "ReportSession",
        remote_side=[id],
        foreign_keys=[copied_from_session_id],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def checkpoint_label(self) -> str:
        """
        Return the preferred human-readable reporting checkpoint name.

        ``checkpoint_name`` is preferred for new records, while ``term``
        remains available for older records created before checkpoint names
        were introduced.
        """

        if self.checkpoint_name:
            return self.checkpoint_name

        if self.term:
            return self.term

        return self.title

    @property
    def produces_grade_card(self) -> bool:
        """Return whether this session produces a grade-card document."""

        return self.reporting_mode in {
            "grade_card",
            "both",
        }

    @property
    def produces_full_report(self) -> bool:
        """Return whether this session produces a full written report."""

        return self.reporting_mode in {
            "full_report",
            "both",
        }

    def __repr__(self) -> str:
        return (
            "<ReportSession "
            f"id={self.id} "
            f"school_id={self.school_id} "
            f"title={self.title!r} "
            f"academic_year={self.academic_year!r} "
            f"year_group={self.year_group!r} "
            f"checkpoint_name={self.checkpoint_name!r} "
            f"reporting_mode={self.reporting_mode!r} "
            f"active={self.active}>"
        )
